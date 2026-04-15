from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.recolte import Recolte, ControleQualite, StockRecolte
from app.models.parcelle import Parcelle
from app.models.production import Campagne, Operation
from app.models.stock import Depot
from app.forms.recolte import RecolteForm, ControleQualiteForm
from app.utils.decorators import role_required, owner_or_admin
from datetime import datetime
from sqlalchemy import or_, func

recolte_bp = Blueprint('recolte', __name__, url_prefix='/recoltes')

# ================================================
# DASHBOARD RÉCOLTES
# ================================================

@recolte_bp.route('/')
@login_required
def index():
    """Dashboard des récoltes"""
    # Statistiques
    total_recoltes = Recolte.query.count()
    total_tonnes = db.session.query(func.sum(Recolte.quantite_nette_tonnes)).scalar() or 0
    total_ventes = db.session.query(func.sum(Recolte.quantite_nette_tonnes - Recolte.quantite_disponible)).scalar() or 0
    
    # Alertes
    stocks_bas = Recolte.query.filter(
        Recolte.quantite_disponible < 1,
        Recolte.est_entierement_vendue == False
    ).count()
    
    # Dernières récoltes
    dernieres_recoltes = Recolte.query.order_by(Recolte.date_recolte.desc()).limit(10).all()
    
    # Répartition par qualité
    qualite_stats = db.session.query(
        Recolte.qualite, 
        func.sum(Recolte.quantite_nette_tonnes)
    ).group_by(Recolte.qualite).all()
    
    return render_template(
        'recolte/index.html',
        total_recoltes=total_recoltes,
        total_tonnes=round(total_tonnes, 2),
        total_ventes=round(total_ventes, 2),
        stocks_bas=stocks_bas,
        dernieres_recoltes=dernieres_recoltes,
        qualite_stats=qualite_stats
    )

# ================================================
# GESTION DES RÉCOLTES
# ================================================

@recolte_bp.route('/liste')
@login_required
def liste():
    """Liste des récoltes avec filtres"""
    search = request.args.get('search', '')
    qualite = request.args.get('qualite', '')
    culture = request.args.get('culture', '')
    
    query = Recolte.query
    
    if search:
        query = query.filter(
            or_(
                Recolte.numero_lot.ilike(f'%{search}%'),
                Recolte.culture.ilike(f'%{search}%'),
                Recolte.variete.ilike(f'%{search}%')
            )
        )
    
    if qualite:
        query = query.filter_by(qualite=qualite)
    
    if culture:
        query = query.filter_by(culture=culture)
    
    recoltes = query.order_by(Recolte.date_recolte.desc()).all()
    
    # Récupérer les valeurs uniques pour les filtres
    cultures_unique = db.session.query(Recolte.culture).distinct().all()
    
    return render_template(
        'recolte/liste.html',
        recoltes=recoltes,
        search=search,
        qualite=qualite,
        culture=culture,
        cultures_unique=[c[0] for c in cultures_unique if c[0]]
    )

@recolte_bp.route('/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'user')
def create():
    """Enregistrer une nouvelle récolte"""
    form = RecolteForm()
    
    # Remplir les choix
    form.parcelle_id.choices = [(p.id, f"{p.nom} ({p.superficie_ha} ha)") for p in Parcelle.query.all()]
    form.campagne_id.choices = [(0, 'Non associée')] + [(c.id, f"{c.code} - {c.nom}") for c in Campagne.query.all()]
    form.operation_id.choices = [(0, 'Non associée')] + [(o.id, f"{o.code} - {o.type}") for o in Operation.query.filter_by(type='recolte').all()]
    form.depot_id.choices = [(d.id, f"{d.nom}") for d in Depot.query.filter_by(est_actif=True).all()]
    
    if form.validate_on_submit():
        quantite_nette = form.quantite_brute_tonnes.data - (form.pertes_tonnes.data or 0)
        
        recolte = Recolte(
            numero_lot=form.numero_lot.data,
            parcelle_id=form.parcelle_id.data,
            campagne_id=form.campagne_id.data if form.campagne_id.data != 0 else None,
            operation_id=form.operation_id.data if form.operation_id.data != 0 else None,
            culture=form.culture.data,
            variete=form.variete.data,
            quantite_brute_tonnes=form.quantite_brute_tonnes.data,
            quantite_nette_tonnes=quantite_nette,
            pertes_tonnes=form.pertes_tonnes.data or 0,
            qualite=form.qualite.data,
            calibre=form.calibre.data,
            humidite_pourcent=form.humidite_pourcent.data,
            date_recolte=form.date_recolte.data,
            depot_id=form.depot_id.data,
            notes_qualite=form.notes_qualite.data,
            user_id=current_user.id
        )
        
        db.session.add(recolte)
        
        # Créer le mouvement de stock initial
        stock_mvt = StockRecolte(
            recolte_id=recolte.id,
            type_mouvement='entree_stock',
            quantite_tonnes=quantite_nette,
            quantite_avant=0,
            quantite_apres=quantite_nette,
            motif=f"Récolte {recolte.numero_lot}",
            user_id=current_user.id
        )
        db.session.add(stock_mvt)
        
        db.session.commit()
        
        flash(f'Récolte "{recolte.numero_lot}" enregistrée avec succès! {quantite_nette} tonnes disponibles', 'success')
        return redirect(url_for('recolte.liste'))
    
    return render_template('recolte/form.html', form=form, title="Nouvelle récolte")

@recolte_bp.route('/<int:id>')
@login_required
def detail(id):
    """Détail d'une récolte"""
    recolte = Recolte.query.get_or_404(id)
    
    # Contrôles qualité
    controles = ControleQualite.query.filter_by(recolte_id=id).order_by(ControleQualite.date_controle.desc()).all()
    
    # Mouvements de stock
    mouvements = StockRecolte.query.filter_by(recolte_id=id).order_by(StockRecolte.date.desc()).all()
    
    # Ventes associées
    ventes = recolte.ventes
    
    # Disponibilité
    disponible = recolte.quantite_disponible
    vendu = recolte.quantite_nette_tonnes - disponible
    
    return render_template(
        'recolte/detail.html',
        recolte=recolte,
        controles=controles,
        mouvements=mouvements,
        ventes=ventes,
        disponible=disponible,
        vendu=vendu
    )

@recolte_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Modifier une récolte"""
    recolte = Recolte.query.get_or_404(id)
    
    # Vérifier si des ventes sont déjà associées
    if recolte.ventes and len(recolte.ventes) > 0:
        flash('Impossible de modifier une récolte qui a déjà des ventes associées', 'warning')
        return redirect(url_for('recolte.detail', id=id))
    
    form = RecolteForm(obj=recolte)
    
    form.parcelle_id.choices = [(p.id, f"{p.nom} ({p.superficie_ha} ha)") for p in Parcelle.query.all()]
    form.campagne_id.choices = [(0, 'Non associée')] + [(c.id, f"{c.code} - {c.nom}") for c in Campagne.query.all()]
    form.operation_id.choices = [(0, 'Non associée')] + [(o.id, f"{o.code} - {o.type}") for o in Operation.query.filter_by(type='recolte').all()]
    form.depot_id.choices = [(d.id, f"{d.nom}") for d in Depot.query.filter_by(est_actif=True).all()]
    
    if form.validate_on_submit():
        quantite_nette = form.quantite_brute_tonnes.data - (form.pertes_tonnes.data or 0)
        
        recolte.numero_lot = form.numero_lot.data
        recolte.parcelle_id = form.parcelle_id.data
        recolte.campagne_id = form.campagne_id.data if form.campagne_id.data != 0 else None
        recolte.operation_id = form.operation_id.data if form.operation_id.data != 0 else None
        recolte.culture = form.culture.data
        recolte.variete = form.variete.data
        recolte.quantite_brute_tonnes = form.quantite_brute_tonnes.data
        recolte.quantite_nette_tonnes = quantite_nette
        recolte.pertes_tonnes = form.pertes_tonnes.data or 0
        recolte.qualite = form.qualite.data
        recolte.calibre = form.calibre.data
        recolte.humidite_pourcent = form.humidite_pourcent.data
        recolte.date_recolte = form.date_recolte.data
        recolte.depot_id = form.depot_id.data
        recolte.notes_qualite = form.notes_qualite.data
        
        db.session.commit()
        
        flash(f'Récolte "{recolte.numero_lot}" mise à jour', 'success')
        return redirect(url_for('recolte.detail', id=id))
    
    return render_template('recolte/form.html', form=form, title="Modifier récolte", recolte=recolte)

@recolte_bp.route('/<int:id>/controle-qualite', methods=['GET', 'POST'])
@login_required
def add_controle_qualite(id):
    """Ajouter un contrôle qualité"""
    recolte = Recolte.query.get_or_404(id)
    form = ControleQualiteForm()
    
    if form.validate_on_submit():
        controle = ControleQualite(
            recolte_id=id,
            controleur=form.controleur.data or current_user.username,
            purete_pourcent=form.purete_pourcent.data,
            impuretes_pourcent=form.impuretes_pourcent.data,
            taux_proteines=form.taux_proteines.data,
            taux_sucre=form.taux_sucre.data,
            presence_moisissure=form.presence_moisissure.data,
            presence_insectes=form.presence_insectes.data,
            resultat=form.resultat.data,
            commentaires=form.commentaires.data
        )
        db.session.add(controle)
        db.session.commit()
        
        flash('Contrôle qualité ajouté', 'success')
        return redirect(url_for('recolte.detail', id=id))
    
    return render_template('recolte/controle_qualite.html', form=form, recolte=recolte)

@recolte_bp.route('/api/disponible/<int:id>')
@login_required
def api_disponible(id):
    """API pour obtenir la quantité disponible (utilisée par les ventes)"""
    recolte = Recolte.query.get_or_404(id)
    return jsonify({
        'disponible': recolte.quantite_disponible,
        'unite': 'tonnes',
        'culture': recolte.culture,
        'qualite': recolte.qualite
    })