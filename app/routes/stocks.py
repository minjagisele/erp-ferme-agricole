from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.stock import Intrant, LotIntrant, MouvementStock, Depot
from app.models.user import User
from app.forms.stock import IntrantForm, LotIntrantForm, MouvementStockForm, DepotForm
from app.utils.decorators import role_required
from datetime import datetime
from sqlalchemy import or_, and_

stock_bp = Blueprint('stock', __name__, url_prefix='/stock')

# ================================================
# DASHBOARD STOCK
# ================================================

@stock_bp.route('/')
@login_required
def index():
    """Dashboard du module stock"""
    # Stock total
    intrants = Intrant.query.filter_by(est_actif=True).all()
    lots_actifs = LotIntrant.query.filter_by(est_actif=True).count()
    
    # Alertes
    lots_perimes = LotIntrant.query.filter(
        LotIntrant.date_peremption < datetime.now().date(),
        LotIntrant.est_actif == True
    ).count()
    
    lots_alerte_stock = LotIntrant.query.filter(
        LotIntrant.quantite_actuelle < 10,  # Seuil arbitraire, à rendre configurable
        LotIntrant.est_actif == True
    ).count()
    
    # Derniers mouvements
    derniers_mouvements = MouvementStock.query.order_by(MouvementStock.date.desc()).limit(10).all()
    
    return render_template(
        'stock/index.html',
        total_intrants=len(intrants),
        total_lots=lots_actifs,
        lots_perimes=lots_perimes,
        lots_alerte_stock=lots_alerte_stock,
        derniers_mouvements=derniers_mouvements
    )

# ================================================
# GESTION DES INTRANTS
# ================================================

@stock_bp.route('/intrants')
@login_required
def intrants_list():
    """Liste des intrants"""
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    query = Intrant.query
    
    if search:
        query = query.filter(
            or_(
                Intrant.nom.ilike(f'%{search}%'),
                Intrant.code.ilike(f'%{search}%')
            )
        )
    
    if type_filter:
        query = query.filter_by(type=type_filter)
    
    intrants = query.order_by(Intrant.nom).all()
    
    return render_template('stock/intrants.html', intrants=intrants, search=search, type_filter=type_filter)

@stock_bp.route('/intrants/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def intrant_create():
    """Créer un nouvel intrant"""
    form = IntrantForm()
    
    if form.validate_on_submit():
        intrant = Intrant(
            nom=form.nom.data,
            code=form.code.data,
            type=form.type.data,
            categorie=form.categorie.data,
            unite=form.unite.data,
            prix_unitaire=form.prix_unitaire.data or 0,
            fournisseur_principal=form.fournisseur_principal.data,
            description=form.description.data,
            est_actif=form.est_actif.data
        )
        db.session.add(intrant)
        db.session.commit()
        
        flash(f'Intrant "{intrant.nom}" créé avec succès', 'success')
        return redirect(url_for('stock.intrants_list'))
    
    return render_template('stock/intrant_form.html', form=form, title="Nouvel intrant")

@stock_bp.route('/intrants/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def intrant_edit(id):
    """Modifier un intrant"""
    intrant = Intrant.query.get_or_404(id)
    form = IntrantForm(obj=intrant)
    
    if form.validate_on_submit():
        intrant.nom = form.nom.data
        intrant.code = form.code.data
        intrant.type = form.type.data
        intrant.categorie = form.categorie.data
        intrant.unite = form.unite.data
        intrant.prix_unitaire = form.prix_unitaire.data or 0
        intrant.fournisseur_principal = form.fournisseur_principal.data
        intrant.description = form.description.data
        intrant.est_actif = form.est_actif.data
        
        db.session.commit()
        flash(f'Intrant "{intrant.nom}" mis à jour', 'success')
        return redirect(url_for('stock.intrants_list'))
    
    return render_template('stock/intrant_form.html', form=form, title="Modifier intrant", intrant=intrant)

# ================================================
# GESTION DES LOTS
# ================================================

@stock_bp.route('/lots')
@login_required
def lots_list():
    """Liste des lots"""
    search = request.args.get('search', '')
    alerte = request.args.get('alerte', '')
    
    query = LotIntrant.query.filter_by(est_actif=True)
    
    if search:
        query = query.filter(
            or_(
                LotIntrant.numero_lot.ilike(f'%{search}%'),
                LotIntrant.fournisseur.ilike(f'%{search}%')
            )
        )
    
    if alerte == 'peremption':
        query = query.filter(LotIntrant.date_peremption < datetime.now().date())
    elif alerte == 'stock':
        query = query.filter(LotIntrant.quantite_actuelle < 10)
    
    lots = query.order_by(LotIntrant.date_peremption).all()
    
    return render_template('stock/lots.html', lots=lots, search=search, alerte=alerte)

@stock_bp.route('/lots/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def lot_create():
    """Créer un nouveau lot (entrée en stock)"""
    form = LotIntrantForm()
    
    # Remplir les choix
    form.intrant_id.choices = [(i.id, f"{i.code} - {i.nom}") for i in Intrant.query.filter_by(est_actif=True).all()]
    form.depot_id.choices = [(d.id, f"{d.code} - {d.nom}") for d in Depot.query.filter_by(est_actif=True).all()]
    
    if form.validate_on_submit():
        lot = LotIntrant(
            numero_lot=form.numero_lot.data,
            intrant_id=form.intrant_id.data,
            quantite_initiale=form.quantite_initiale.data,
            quantite_actuelle=form.quantite_initiale.data,  # Initialement égale
            prix_achat=form.prix_achat.data or 0,
            date_fabrication=form.date_fabrication.data,
            date_peremption=form.date_peremption.data,
            depot_id=form.depot_id.data,
            fournisseur=form.fournisseur.data,
            facture_numero=form.facture_numero.data,
            notes=form.notes.data
        )
        db.session.add(lot)
        
        # Créer le mouvement d'entrée associé
        from app.models.stock import MouvementStock
        mouvement = MouvementStock(
            numero_mouvement=f"ENT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            intrant_id=form.intrant_id.data,
            lot_id=lot.id,
            type='entree',
            quantite=form.quantite_initiale.data,
            quantite_avant=0,
            quantite_apres=form.quantite_initiale.data,
            motif=f"Réception lot {form.numero_lot.data}",
            user_id=current_user.id
        )
        db.session.add(mouvement)
        db.session.commit()
        
        flash(f'Lot "{lot.numero_lot}" ajouté avec succès', 'success')
        return redirect(url_for('stock.lots_list'))
    
    return render_template('stock/lot_form.html', form=form, title="Nouveau lot")

@stock_bp.route('/lots/<int:id>')
@login_required
def lot_detail(id):
    """Détail d'un lot avec historique des mouvements"""
    lot = LotIntrant.query.get_or_404(id)
    mouvements = MouvementStock.query.filter_by(lot_id=id).order_by(MouvementStock.date.desc()).all()
    
    return render_template('stock/lot_detail.html', lot=lot, mouvements=mouvements)

# ================================================
# MOUVEMENTS DE STOCK
# ================================================

@stock_bp.route('/mouvements/ajouter', methods=['GET', 'POST'])
@login_required
def mouvement_add():
    """Ajouter un mouvement de stock (sortie, perte, etc.)"""
    form = MouvementStockForm()
    
    # Remplir les choix des lots avec stock > 0
    lots_disponibles = LotIntrant.query.filter(
        LotIntrant.quantite_actuelle > 0,
        LotIntrant.est_actif == True
    ).all()
    
    form.lot_id.choices = [(l.id, f"{l.numero_lot} - {l.intrant.nom} ({l.quantite_actuelle} {l.intrant.unite})") for l in lots_disponibles]
    
    if form.validate_on_submit():
        lot = LotIntrant.query.get(form.lot_id.data)
        
        if form.quantite.data > lot.quantite_actuelle:
            flash(f'Quantité insuffisante. Stock disponible: {lot.quantite_actuelle} {lot.intrant.unite}', 'danger')
            return redirect(url_for('stock.mouvement_add'))
        
        # Générer un numéro de mouvement unique
        import random
        numero = f"{form.type.data.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
        
        mouvement = MouvementStock(
            numero_mouvement=numero,
            intrant_id=lot.intrant_id,
            lot_id=lot.id,
            type=form.type.data,
            quantite=form.quantite.data,
            quantite_avant=lot.quantite_actuelle,
            quantite_apres=lot.quantite_actuelle - form.quantite.data,
            motif=form.motif.data,
            reference=form.reference.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        
        db.session.add(mouvement)
        db.session.commit()
        
        flash(f'Mouvement enregistré: {form.type.data} de {form.quantite.data} {lot.intrant.unite}', 'success')
        return redirect(url_for('stock.lot_detail', id=lot.id))
    
    return render_template('stock/mouvement_form.html', form=form)

@stock_bp.route('/mouvements')
@login_required
def mouvements_list():
    """Historique des mouvements"""
    page = request.args.get('page', 1, type=int)
    pagination = MouvementStock.query.order_by(MouvementStock.date.desc()).paginate(page=page, per_page=20)
    mouvements = pagination.items
    
    return render_template('stock/mouvements.html', mouvements=mouvements, pagination=pagination)

# ================================================
# GESTION DES DÉPÔTS
# ================================================

@stock_bp.route('/depots')
@login_required
@role_required('admin', 'manager')
def depots_list():
    """Liste des dépôts"""
    depots = Depot.query.all()
    return render_template('stock/depots.html', depots=depots)

@stock_bp.route('/depots/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def depot_create():
    """Créer un dépôt"""
    form = DepotForm()
    
    if form.validate_on_submit():
        depot = Depot(
            nom=form.nom.data,
            code=form.code.data,
            type=form.type.data,
            localisation=form.localisation.data,
            responsable=form.responsable.data,
            est_actif=form.est_actif.data
        )
        db.session.add(depot)
        db.session.commit()
        
        flash(f'Dépôt "{depot.nom}" créé', 'success')
        return redirect(url_for('stock.depots_list'))
    
    return render_template('stock/depot_form.html', form=form, title="Nouveau dépôt")