from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from app import db
from app.models.vente import Client, Vente, Paiement
from app.models.recolte import Recolte, StockRecolte
from app.forms.vente import ClientForm, VenteForm, PaiementForm
from app.utils.decorators import role_required
from datetime import datetime, timedelta
from sqlalchemy import or_, func
import pdfkit  # Pour génération PDF (optionnel)
from io import BytesIO

vente_bp = Blueprint('vente', __name__, url_prefix='/ventes')

# ================================================
# DASHBOARD VENTES
# ================================================

@vente_bp.route('/')
@login_required
def index():
    """Dashboard des ventes"""
    # Statistiques
    total_ventes = Vente.query.count()
    chiffre_affaires = db.session.query(func.sum(Vente.montant_ttc)).filter(Vente.statut == 'paye').scalar() or 0
    factures_impayees = db.session.query(func.sum(Vente.montant_ttc - Vente.montant_paye)).filter(
        Vente.est_paye == False,
        Vente.statut != 'annule'
    ).scalar() or 0
    
    # Ventes en cours
    ventes_en_cours = Vente.query.filter(Vente.statut.in_(['confirme', 'livre', 'facture'])).count()
    
    # Dernières ventes
    dernieres_ventes = Vente.query.order_by(Vente.date_devis.desc()).limit(10).all()
    
    # Ventes par mois (pour graphique)
    ventes_par_mois = db.session.query(
        func.strftime('%Y-%m', Vente.date_commande).label('mois'),
        func.sum(Vente.montant_ttc)
    ).filter(Vente.statut == 'paye').group_by('mois').order_by('mois').limit(6).all()
    
    return render_template(
        'vente/index.html',
        total_ventes=total_ventes,
        chiffre_affaires=round(chiffre_affaires, 2),
        factures_impayees=round(factures_impayees, 2),
        ventes_en_cours=ventes_en_cours,
        dernieres_ventes=dernieres_ventes,
        ventes_par_mois=ventes_par_mois
    )

# ================================================
# GESTION DES CLIENTS
# ================================================

@vente_bp.route('/clients')
@login_required
def clients_list():
    """Liste des clients"""
    search = request.args.get('search', '')
    
    query = Client.query
    
    if search:
        query = query.filter(
            or_(
                Client.nom.ilike(f'%{search}%'),
                Client.code.ilike(f'%{search}%'),
                Client.email.ilike(f'%{search}%')
            )
        )
    
    clients = query.order_by(Client.nom).all()
    
    return render_template('vente/clients.html', clients=clients, search=search)

@vente_bp.route('/clients/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def client_create():
    """Créer un client"""
    form = ClientForm()
    
    if form.validate_on_submit():
        client = Client(
            code=form.code.data,
            nom=form.nom.data,
            type=form.type.data,
            email=form.email.data,
            telephone=form.telephone.data,
            adresse=form.adresse.data,
            ville=form.ville.data,
            pays=form.pays.data,
            numero_tva=form.numero_tva.data,
            contact_nom=form.contact_nom.data,
            contact_telephone=form.contact_telephone.data,
            est_actif=form.est_actif.data,
            user_id=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        
        flash(f'Client "{client.nom}" créé', 'success')
        return redirect(url_for('vente.clients_list'))
    
    return render_template('vente/client_form.html', form=form, title="Nouveau client")

@vente_bp.route('/clients/<int:id>')
@login_required
def client_detail(id):
    """Détail d'un client"""
    client = Client.query.get_or_404(id)
    ventes = Vente.query.filter_by(client_id=id).order_by(Vente.date_devis.desc()).limit(20).all()
    
    stats = {
        'total_ventes': len(ventes),
        'total_achats': client.total_achats,
        'derniere_vente': ventes[0].date_devis if ventes else None
    }
    
    return render_template('vente/client_detail.html', client=client, ventes=ventes, stats=stats)

# ================================================
# WORKFLOW DE VENTE
# ================================================

@vente_bp.route('/devis/creer', methods=['GET', 'POST'])
@login_required
def devis_create():
    """Créer un devis (brouillon)"""
    form = VenteForm()
    
    # Remplir les choix
    form.client_id.choices = [(c.id, f"{c.code} - {c.nom}") for c in Client.query.filter_by(est_actif=True).all()]
    
    # Récupérer les récoltes disponibles
    recoltes_disponibles = Recolte.query.filter(
        Recolte.quantite_disponible > 0,
        Recolte.est_entierement_vendue == False
    ).all()
    
    form.recolte_id.choices = [(r.id, f"{r.numero_lot} - {r.culture} ({r.quantite_disponible} t dispo)") for r in recoltes_disponibles]
    
    if form.validate_on_submit():
        recolte = Recolte.query.get(form.recolte_id.data)
        
        # Vérifier le stock
        if form.quantite_tonnes.data > recolte.quantite_disponible:
            flash(f'Stock insuffisant. Disponible: {recolte.quantite_disponible} tonnes', 'danger')
            return redirect(url_for('vente.devis_create'))
        
        # Calculer les montants
        montant_ht = form.quantite_tonnes.data * form.prix_unitaire.data
        montant_tva = montant_ht * (form.taux_tva.data / 100)
        montant_ttc = montant_ht + montant_tva
        
        # Générer un numéro de devis
        devis_num = f"DEV-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        
        vente = Vente(
            numero_devis=devis_num,
            client_id=form.client_id.data,
            recolte_id=form.recolte_id.data,
            quantite_tonnes=form.quantite_tonnes.data,
            prix_unitaire=form.prix_unitaire.data,
            montant_ht=montant_ht,
            taux_tva=form.taux_tva.data,
            montant_tva=montant_tva,
            montant_ttc=montant_ttc,
            date_livraison_prevue=form.date_livraison_prevue.data,
            conditions_paiement=form.conditions_paiement.data,
            adresse_livraison=form.adresse_livraison.data,
            notes=form.notes.data,
            statut='brouillon',
            user_id=current_user.id
        )
        
        db.session.add(vente)
        db.session.commit()
        
        flash(f'Devis {devis_num} créé avec succès', 'success')
        return redirect(url_for('vente.devis_detail', id=vente.id))
    
    return render_template('vente/devis_form.html', form=form, title="Nouveau devis")

@vente_bp.route('/devis/<int:id>')
@login_required
def devis_detail(id):
    """Détail d'un devis"""
    vente = Vente.query.get_or_404(id)
    
    return render_template('vente/devis_detail.html', vente=vente)

@vente_bp.route('/devis/<int:id>/confirmer', methods=['POST'])
@login_required
def devis_confirm(id):
    """Confirmer un devis (devient commande)"""
    vente = Vente.query.get_or_404(id)
    
    if vente.statut != 'brouillon':
        flash('Ce devis ne peut pas être confirmé', 'warning')
        return redirect(url_for('vente.devis_detail', id=id))
    
    # Vérifier à nouveau le stock
    recolte = Recolte.query.get(vente.recolte_id)
    if vente.quantite_tonnes > recolte.quantite_disponible:
        flash(f'Stock insuffisant. Disponible: {recolte.quantite_disponible} tonnes', 'danger')
        return redirect(url_for('vente.devis_detail', id=id))
    
    # Générer numéro de commande
    vente.numero_commande = f"CMD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    vente.date_commande = datetime.utcnow()
    vente.statut = 'confirme'
    
    db.session.commit()
    
    flash(f'Devis confirmé. Commande {vente.numero_commande} créée', 'success')
    return redirect(url_for('vente.commande_detail', id=vente.id))

@vente_bp.route('/commandes')
@login_required
def commandes_list():
    """Liste des commandes"""
    statut = request.args.get('statut', '')
    
    query = Vente.query.filter(Vente.numero_commande.isnot(None))
    
    if statut:
        query = query.filter_by(statut=statut)
    
    commandes = query.order_by(Vente.date_commande.desc()).all()
    
    return render_template('vente/commandes.html', commandes=commandes, statut=statut)

@vente_bp.route('/commande/<int:id>')
@login_required
def commande_detail(id):
    """Détail d'une commande"""
    vente = Vente.query.get_or_404(id)
    paiements = Paiement.query.filter_by(vente_id=id).all()
    
    return render_template('vente/commande_detail.html', vente=vente, paiements=paiements)

@vente_bp.route('/commande/<int:id>/livrer', methods=['POST'])
@login_required
def commande_livrer(id):
    """Marquer une commande comme livrée"""
    vente = Vente.query.get_or_404(id)
    
    if vente.statut != 'confirme':
        flash('Seules les commandes confirmées peuvent être livrées', 'warning')
        return redirect(url_for('vente.commande_detail', id=id))
    
    # Générer numéro de livraison
    vente.numero_livraison = f"BL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    vente.date_livraison_reelle = datetime.now().date()
    vente.statut = 'livre'
    
    db.session.commit()
    
    flash(f'Commande livrée. Bon de livraison: {vente.numero_livraison}', 'success')
    return redirect(url_for('vente.commande_detail', id=id))

@vente_bp.route('/commande/<int:id>/facturer', methods=['POST'])
@login_required
def commande_facturer(id):
    """Générer la facture"""
    vente = Vente.query.get_or_404(id)
    
    if vente.statut not in ['livre', 'facture']:
        flash('La commande doit être livrée avant facturation', 'warning')
        return redirect(url_for('vente.commande_detail', id=id))
    
    # Générer numéro de facture
    vente.numero_facture = f"FACT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    vente.date_facture = datetime.utcnow()
    vente.statut = 'facture'
    
    db.session.commit()
    
    flash(f'Facture {vente.numero_facture} générée', 'success')
    return redirect(url_for('vente.facture_detail', id=vente.id))

@vente_bp.route('/facture/<int:id>')
@login_required
def facture_detail(id):
    """Détail d'une facture"""
    vente = Vente.query.get_or_404(id)
    paiements = Paiement.query.filter_by(vente_id=id).all()
    
    return render_template('vente/facture_detail.html', vente=vente, paiements=paiements)

@vente_bp.route('/facture/<int:id>/pdf')
@login_required
def facture_pdf(id):
    """Générer la facture en PDF"""
    vente = Vente.query.get_or_404(id)
    
    # Rendre le template HTML
    html = render_template('vente/facture_pdf.html', vente=vente)
    
    # Générer PDF (nécessite wkhtmltopdf installé)
    # pdf = pdfkit.from_string(html, False)
    
    # response = make_response(pdf)
    # response.headers['Content-Type'] = 'application/pdf'
    # response.headers['Content-Disposition'] = f'inline; filename=facture_{vente.numero_facture}.pdf'
    
    # Version temporaire: renvoyer HTML
    return html

# ================================================
# PAIEMENTS
# ================================================

@vente_bp.route('/paiement/<int:vente_id>/ajouter', methods=['GET', 'POST'])
@login_required
def add_paiement(vente_id):
    """Ajouter un paiement"""
    vente = Vente.query.get_or_404(vente_id)
    form = PaiementForm()
    
    if form.validate_on_submit():
        # Vérifier que le paiement ne dépasse pas le montant dû
        if form.montant.data > vente.reste_a_payer:
            flash(f'Montant trop élevé. Reste à payer: {vente.reste_a_payer}€', 'danger')
            return redirect(url_for('vente.add_paiement', vente_id=vente_id))
        
        paiement = Paiement(
            vente_id=vente_id,
            montant=form.montant.data,
            mode=form.mode.data,
            reference=form.reference.data,
            date_paiement=form.date_paiement.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        
        db.session.add(paiement)
        
        # Mettre à jour le montant payé de la vente
        vente.montant_paye += form.montant.data
        
        if vente.reste_a_payer <= 0:
            vente.est_paye = True
            vente.statut = 'paye'
            vente.date_paiement = form.date_paiement.data
            
            # Mettre à jour le stock de la récolte (sortie définitive)
            recolte = Recolte.query.get(vente.recolte_id)
            if recolte.quantite_disponible <= 0:
                recolte.est_entierement_vendue = True
            
            # Enregistrer le mouvement de stock
            stock_mvt = StockRecolte(
                recolte_id=recolte.id,
                type_mouvement='sortie_vente',
                quantite_tonnes=vente.quantite_tonnes,
                quantite_avant=recolte.quantite_disponible + vente.quantite_tonnes,
                quantite_apres=recolte.quantite_disponible,
                reference=vente.numero_facture,
                motif=f"Vente {vente.numero_facture}",
                user_id=current_user.id
            )
            db.session.add(stock_mvt)
        
        db.session.commit()
        
        flash(f'Paiement de {form.montant.data}€ enregistré', 'success')
        return redirect(url_for('vente.commande_detail', id=vente_id))
    
    return render_template('vente/paiement_form.html', form=form, vente=vente)