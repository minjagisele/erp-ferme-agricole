from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.parcelle import Parcelle, Equipement
from app.models.stock import Intrant, LotIntrant, MouvementStock, Depot
from app.models.production import Campagne, Operation
from app.models.recolte import Recolte
from app.models.vente import Vente, Client
from app.utils.decorators import role_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, extract

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Page d'accueil"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal avec tous les KPIs"""
    
    # ================================================
    # 1. INDICATEURS GÉNÉRAUX (KPI CARDS)
    # ================================================
    
    # Parcelles
    if current_user.is_admin() or current_user.is_manager():
        total_parcelles = Parcelle.query.count()
        total_superficie = db.session.query(func.sum(Parcelle.superficie_ha)).scalar() or 0
        parcelles_par_type = db.session.query(
            Parcelle.type_sol, func.count(Parcelle.id)
        ).group_by(Parcelle.type_sol).all()
    else:
        total_parcelles = Parcelle.query.filter_by(user_id=current_user.id).count()
        total_superficie = db.session.query(func.sum(Parcelle.superficie_ha)).filter(
            Parcelle.user_id == current_user.id
        ).scalar() or 0
        parcelles_par_type = db.session.query(
            Parcelle.type_sol, func.count(Parcelle.id)
        ).filter(Parcelle.user_id == current_user.id).group_by(Parcelle.type_sol).all()
    
    # Stocks (intrants)
    intrants_rupture = LotIntrant.query.filter(
        LotIntrant.quantite_actuelle < 10,
        LotIntrant.est_actif == True
    ).count()
    
    lots_perimes = LotIntrant.query.filter(
        LotIntrant.date_peremption < datetime.now().date(),
        LotIntrant.est_actif == True
    ).count()
    
    valeur_stock = db.session.query(
        func.sum(LotIntrant.quantite_actuelle * Intrant.prix_unitaire)
    ).join(Intrant).filter(LotIntrant.est_actif == True).scalar() or 0
    
    # Production
    campagnes_actives = Campagne.query.filter_by(statut='actif').count()
    operations_en_cours = Operation.query.filter_by(statut='en_cours').count()
    operations_retard = Operation.query.filter(
        Operation.statut == 'planifie',
        Operation.date_prevue < datetime.now().date()
    ).count()
    
    # Récoltes
    total_recoltes_tonnes = db.session.query(func.sum(Recolte.quantite_nette_tonnes)).scalar() or 0
    
    # Calcul du stock disponible (quantité nette - quantité vendue)
    sold_per_recolte = db.session.query(
        Recolte.id,
        func.sum(Vente.quantite_tonnes).label('total_sold')
    ).outerjoin(Vente, and_(
        Vente.recolte_id == Recolte.id,
        Vente.statut != 'annule'
    )).group_by(Recolte.id).subquery()
    
    stock_recoltes_disponible = db.session.query(
        func.sum(Recolte.quantite_nette_tonnes - func.coalesce(sold_per_recolte.c.total_sold, 0))
    ).select_from(Recolte).outerjoin(sold_per_recolte, sold_per_recolte.c.id == Recolte.id).scalar() or 0
    
    recoltes_par_qualite = db.session.query(
        Recolte.qualite, func.sum(Recolte.quantite_nette_tonnes)
    ).group_by(Recolte.qualite).all()
    
    # Ventes
    if current_user.is_admin() or current_user.is_manager():
        chiffre_affaires_mois = db.session.query(func.sum(Vente.montant_ttc)).filter(
            Vente.statut == 'paye',
            extract('month', Vente.date_paiement) == datetime.now().month
        ).scalar() or 0
        
        chiffre_affaires_annee = db.session.query(func.sum(Vente.montant_ttc)).filter(
            Vente.statut == 'paye',
            extract('year', Vente.date_paiement) == datetime.now().year
        ).scalar() or 0
        
        creances_impayees = db.session.query(
            func.sum(Vente.montant_ttc - Vente.montant_paye)
        ).filter(
            Vente.est_paye == False,
            Vente.statut != 'annule'
        ).scalar() or 0
    else:
        # Pour un utilisateur standard, voir uniquement ses ventes (via ses récoltes)
        user_parcelles = Parcelle.query.filter_by(user_id=current_user.id).all()
        parcelle_ids = [p.id for p in user_parcelles]
        user_recoltes = Recolte.query.filter(Recolte.parcelle_id.in_(parcelle_ids)).all()
        recolte_ids = [r.id for r in user_recoltes]
        
        chiffre_affaires_mois = db.session.query(func.sum(Vente.montant_ttc)).filter(
            Vente.statut == 'paye',
            Vente.recolte_id.in_(recolte_ids),
            extract('month', Vente.date_paiement) == datetime.now().month
        ).scalar() or 0
        
        chiffre_affaires_annee = db.session.query(func.sum(Vente.montant_ttc)).filter(
            Vente.statut == 'paye',
            Vente.recolte_id.in_(recolte_ids),
            extract('year', Vente.date_paiement) == datetime.now().year
        ).scalar() or 0
        
        creances_impayees = db.session.query(
            func.sum(Vente.montant_ttc - Vente.montant_paye)
        ).filter(
            Vente.recolte_id.in_(recolte_ids),
            Vente.est_paye == False,
            Vente.statut != 'annule'
        ).scalar() or 0
    
    # ================================================
    # 2. GRAPHIQUES (données pour Chart.js)
    # ================================================
    
    # Graphique des ventes sur 6 derniers mois
    ventes_par_mois = []
    for i in range(5, -1, -1):
        mois = datetime.now().replace(day=1) - timedelta(days=30*i)
        montant = db.session.query(func.sum(Vente.montant_ttc)).filter(
            Vente.statut == 'paye',
            extract('year', Vente.date_paiement) == mois.year,
            extract('month', Vente.date_paiement) == mois.month
        ).scalar() or 0
        ventes_par_mois.append({
            'mois': mois.strftime('%B %Y'),
            'montant': round(montant, 2)
        })
    
    # Graphique des opérations par type
    operations_par_type = db.session.query(
        Operation.type, func.count(Operation.id)
    ).group_by(Operation.type).all()
    
    # Graphique de l'utilisation des stocks (top 5 intrants)
    top_intrants = db.session.query(
        Intrant.nom,
        func.sum(LotIntrant.quantite_initiale - LotIntrant.quantite_actuelle).label('consomme')
    ).join(LotIntrant).group_by(Intrant.id).order_by(func.sum(LotIntrant.quantite_initiale - LotIntrant.quantite_actuelle).desc()).limit(5).all()
    
    # Graphique des récoltes par culture
    recoltes_par_culture = db.session.query(
        Recolte.culture, func.sum(Recolte.quantite_nette_tonnes)
    ).group_by(Recolte.culture).all()
    
    # ================================================
    # 3. ALERTES
    # ================================================
    
    alertes = []
    
    # Alerte stock intrants bas
    lots_alerte = LotIntrant.query.filter(
        LotIntrant.quantite_actuelle < 10,
        LotIntrant.est_actif == True
    ).limit(5).all()
    for lot in lots_alerte:
        alertes.append({
            'type': 'warning',
            'icon': 'fa-boxes',
            'message': f'Stock bas: {lot.intrant.nom} (lot {lot.numero_lot}) - reste {lot.quantite_actuelle} {lot.intrant.unite}',
            'lien': url_for('stock.lot_detail', id=lot.id)
        })
    
    # Alerte péremption
    lots_peremption = LotIntrant.query.filter(
        LotIntrant.date_peremption.isnot(None),
        LotIntrant.date_peremption <= datetime.now().date() + timedelta(days=30),
        LotIntrant.date_peremption > datetime.now().date(),
        LotIntrant.quantite_actuelle > 0
    ).limit(5).all()
    for lot in lots_peremption:
        jours = (lot.date_peremption - datetime.now().date()).days
        alertes.append({
            'type': 'danger',
            'icon': 'fa-calendar-times',
            'message': f'Péremption dans {jours} jours: {lot.intrant.nom} (lot {lot.numero_lot}) - expire le {lot.date_peremption}',
            'lien': url_for('stock.lot_detail', id=lot.id)
        })
    
    # Alerte opérations en retard
    ops_retard = Operation.query.filter(
        Operation.statut == 'planifie',
        Operation.date_prevue < datetime.now().date()
    ).limit(5).all()
    for op in ops_retard:
        retard = (datetime.now().date() - op.date_prevue).days
        alertes.append({
            'type': 'warning',
            'icon': 'fa-tasks',
            'message': f'Opération en retard de {retard} jours: {op.code} - prévue le {op.date_prevue}',
            'lien': url_for('production.operation_detail', id=op.id)
        })
    
    # Alerte factures impayées
    factures_impayees = Vente.query.filter(
        Vente.est_paye == False,
        Vente.statut == 'facture',
        Vente.date_facture <= datetime.now() - timedelta(days=15)
    ).limit(5).all()
    for facture in factures_impayees:
        retard = (datetime.now() - facture.date_facture).days
        alertes.append({
            'type': 'danger',
            'icon': 'fa-file-invoice-dollar',
            'message': f'Facture impayée depuis {retard} jours: {facture.numero_facture} - {facture.client.nom} - {facture.reste_a_payer}€',
            'lien': url_for('vente.facture_detail', id=facture.id)
        })
    
    # ================================================
    # 4. ACTIVITÉS RÉCENTES
    # ================================================
    
    activites_recentes = []
    
    # Dernières opérations
    dernieres_ops = Operation.query.order_by(Operation.created_at.desc()).limit(5).all()
    for op in dernieres_ops:
        activites_recentes.append({
            'date': op.created_at,
            'type': 'operation',
            'message': f'Opération {op.code} - {op.type}',
            'statut': op.statut,
            'lien': url_for('production.operation_detail', id=op.id)
        })
    
    # Dernières ventes
    dernieres_ventes = Vente.query.filter(Vente.numero_facture.isnot(None)).order_by(Vente.date_facture.desc()).limit(5).all()
    for vente in dernieres_ventes:
        activites_recentes.append({
            'date': vente.date_facture or vente.date_commande or vente.date_devis,
            'type': 'vente',
            'message': f'Facture {vente.numero_facture} - {vente.client.nom} - {vente.montant_ttc}€',
            'statut': vente.statut,
            'lien': url_for('vente.facture_detail', id=vente.id)
        })
    
    # Dernières récoltes
    dernieres_recoltes = Recolte.query.order_by(Recolte.date_recolte.desc()).limit(5).all()
    for recolte in dernieres_recoltes:
        activites_recentes.append({
            'date': recolte.date_recolte,
            'type': 'recolte',
            'message': f'Récolte {recolte.numero_lot} - {recolte.culture} - {recolte.quantite_nette_tonnes}t',
            'statut': 'realise',
            'lien': url_for('recolte.detail', id=recolte.id)
        })
    
    # Trier par date
    activites_recentes.sort(key=lambda x: x['date'], reverse=True)
    activites_recentes = activites_recentes[:10]
    
    # ================================================
    # 5. PRÉVISIONS (pour les jours à venir)
    # ================================================
    
    previsions = []
    
    # Opérations à venir dans les 7 jours
    ops_a_venir = Operation.query.filter(
        Operation.statut == 'planifie',
        Operation.date_prevue >= datetime.now().date(),
        Operation.date_prevue <= datetime.now().date() + timedelta(days=7)
    ).order_by(Operation.date_prevue).limit(5).all()
    
    for op in ops_a_venir:
        previsions.append({
            'date': op.date_prevue,
            'type': 'operation',
            'message': f'Opération planifiée: {op.code} - {op.type}',
            'lien': url_for('production.operation_detail', id=op.id)
        })
    
    # Livraisons à venir
    livraisons_a_venir = Vente.query.filter(
        Vente.statut == 'confirme',
        Vente.date_livraison_prevue >= datetime.now().date(),
        Vente.date_livraison_prevue <= datetime.now().date() + timedelta(days=7)
    ).order_by(Vente.date_livraison_prevue).limit(5).all()
    
    for liv in livraisons_a_venir:
        previsions.append({
            'date': liv.date_livraison_prevue,
            'type': 'livraison',
            'message': f'Livraison prévue pour {liv.client.nom} - {liv.quantite_tonnes}t',
            'lien': url_for('vente.commande_detail', id=liv.id)
        })
    
    previsions.sort(key=lambda x: x['date'])
    
    # ================================================
    # RENDU DU TEMPLATE
    # ================================================
    
    context = {
        # KPIs
        'total_parcelles': total_parcelles,
        'total_superficie': round(total_superficie, 2),
        'parcelles_par_type': parcelles_par_type,
        'intrants_rupture': intrants_rupture,
        'lots_perimes': lots_perimes,
        'valeur_stock': round(valeur_stock, 2),
        'campagnes_actives': campagnes_actives,
        'operations_en_cours': operations_en_cours,
        'operations_retard': operations_retard,
        'total_recoltes_tonnes': round(total_recoltes_tonnes, 2),
        'stock_recoltes_disponible': round(stock_recoltes_disponible, 2),
        'recoltes_par_qualite': recoltes_par_qualite,
        'chiffre_affaires_mois': round(chiffre_affaires_mois, 2),
        'chiffre_affaires_annee': round(chiffre_affaires_annee, 2),
        'creances_impayees': round(creances_impayees, 2),
        
        # Graphiques
        'ventes_par_mois': ventes_par_mois,
        'operations_par_type': operations_par_type,
        'top_intrants': top_intrants,
        'recoltes_par_culture': recoltes_par_culture,
        
        # Alertes et activités
        'alertes': alertes,
        'activites_recentes': activites_recentes,
        'previsions': previsions,
        
        # Info utilisateur
        'user_role': current_user.role,
        'datetime': datetime
    }
    
    return render_template('dashboard/index.html', **context)

# ================================================
# GESTION ADMINISTRATEUR
# ================================================

@main_bp.route('/admin/users')
@login_required
@role_required('admin')
def manage_users():
    """Gestion des utilisateurs (admin seulement)"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# ================================================
# API POUR GRAPHIQUES EN TEMPS RÉEL (AJAX)
# ================================================

@main_bp.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API pour rafraîchir les statistiques sans recharger la page"""
    # Version simplifiée - retourne les données JSON
    stats = {
        'parcelles': Parcelle.query.count(),
        'operations_en_cours': Operation.query.filter_by(statut='en_cours').count(),
        'alertes': len(LotIntrant.query.filter(LotIntrant.quantite_actuelle < 10).all())
    }
    return jsonify(stats)