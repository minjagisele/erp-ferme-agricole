from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.production import Campagne, Operation, OperationIntrant, OperationEmploye, OperationEquipement
from app.models.parcelle import Parcelle, Equipement
from app.models.stock import LotIntrant, MouvementStock
from app.models.user import User
from app.forms.production import CampagneForm, OperationForm, OperationIntrantForm, OperationEmployeForm
from app.utils.decorators import role_required
from datetime import datetime
from sqlalchemy import or_

production_bp = Blueprint('production', __name__, url_prefix='/production')

# ================================================
# CAMPAGNES
# ================================================

@production_bp.route('/')
@login_required
def index():
    """Dashboard production"""
    campagnes_actives = Campagne.query.filter_by(statut='actif').count()
    operations_planifiees = Operation.query.filter_by(statut='planifie').count()
    operations_realisees = Operation.query.filter_by(statut='realise').count()
    operations_en_retard = Operation.query.filter(
        Operation.statut == 'planifie',
        Operation.date_prevue < datetime.now().date()
    ).count()
    
    dernieres_operations = Operation.query.order_by(Operation.date_prevue.desc()).limit(10).all()
    
    return render_template(
        'production/index.html',
        campagnes_actives=campagnes_actives,
        operations_planifiees=operations_planifiees,
        operations_realisees=operations_realisees,
        operations_en_retard=operations_en_retard,
        dernieres_operations=dernieres_operations
    )

@production_bp.route('/campagnes')
@login_required
def campagnes_list():
    """Liste des campagnes"""
    campagnes = Campagne.query.order_by(Campagne.date_debut.desc()).all()
    return render_template('production/campagnes.html', campagnes=campagnes)

@production_bp.route('/campagnes/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def campagne_create():
    """Créer une campagne"""
    form = CampagneForm()
    
    if form.validate_on_submit():
        campagne = Campagne(
            nom=form.nom.data,
            code=form.code.data,
            date_debut=form.date_debut.data,
            date_fin=form.date_fin.data,
            objectif_principal=form.objectif_principal.data,
            budget_prevu=form.budget_prevu.data or 0,
            statut=form.statut.data,
            user_id=current_user.id
        )
        db.session.add(campagne)
        db.session.commit()
        
        flash(f'Campagne "{campagne.nom}" créée', 'success')
        return redirect(url_for('production.campagnes_list'))
    
    return render_template('production/campagne_form.html', form=form, title="Nouvelle campagne")

@production_bp.route('/campagnes/<int:id>')
@login_required
def campagne_detail(id):
    """Détail d'une campagne avec ses opérations"""
    campagne = Campagne.query.get_or_404(id)
    operations = Operation.query.filter_by(campagne_id=id).order_by(Operation.date_prevue).all()
    
    # Statistiques
    stats = {
        'total_operations': len(operations),
        'realisees': len([op for op in operations if op.statut == 'realise']),
        'en_cours': len([op for op in operations if op.statut == 'en_cours']),
        'planifiees': len([op for op in operations if op.statut == 'planifie']),
        'cout_total': sum(op.cout_reel for op in operations),
        'progression': campagne.progression
    }
    
    return render_template('production/campagne_detail.html', campagne=campagne, operations=operations, stats=stats)

# ================================================
# OPÉRATIONS
# ================================================

@production_bp.route('/operations')
@login_required
def operations_list():
    """Liste des opérations avec filtres"""
    search = request.args.get('search', '')
    statut = request.args.get('statut', '')
    type_op = request.args.get('type', '')
    
    query = Operation.query
    
    if search:
        query = query.filter(
            or_(
                Operation.code.ilike(f'%{search}%'),
                Operation.description.ilike(f'%{search}%')
            )
        )
    
    if statut:
        query = query.filter_by(statut=statut)
    
    if type_op:
        query = query.filter_by(type=type_op)
    
    operations = query.order_by(Operation.date_prevue).all()
    
    return render_template('production/operations.html', operations=operations, search=search)

@production_bp.route('/operations/creer', methods=['GET', 'POST'])
@login_required
def operation_create():
    """Créer une opération"""
    form = OperationForm()
    
    # Remplir les choix
    form.parcelle_id.choices = [(p.id, f"{p.nom} ({p.superficie_ha} ha)") for p in Parcelle.query.all()]
    form.campagne_id.choices = [(c.id, f"{c.code} - {c.nom}") for c in Campagne.query.all()]
    form.responsable_id.choices = [(0, 'Non assigné')] + [(u.id, u.username) for u in User.query.filter(User.role.in_(['admin', 'manager', 'user']))]
    
    if form.validate_on_submit():
        operation = Operation(
            code=form.code.data,
            type=form.type.data,
            description=form.description.data,
            date_prevue=form.date_prevue.data,
            priorite=form.priorite.data,
            cout_estime=form.cout_estime.data or 0,
            parcelle_id=form.parcelle_id.data,
            campagne_id=form.campagne_id.data,
            responsable_id=form.responsable_id.data if form.responsable_id.data != 0 else None,
            statut='planifie'
        )
        db.session.add(operation)
        db.session.commit()
        
        flash(f'Opération "{operation.code}" créée', 'success')
        return redirect(url_for('production.operations_list'))
    
    return render_template('production/operation_form.html', form=form, title="Nouvelle opération")

@production_bp.route('/operations/<int:id>')
@login_required
def operation_detail(id):
    """Détail d'une opération"""
    operation = Operation.query.get_or_404(id)
    intrants = OperationIntrant.query.filter_by(operation_id=id).all()
    employes = OperationEmploye.query.filter_by(operation_id=id).all()
    equipements = OperationEquipement.query.filter_by(operation_id=id).all()
    
    return render_template(
        'production/operation_detail.html',
        operation=operation,
        intrants=intrants,
        employes=employes,
        equipements=equipements
    )

@production_bp.route('/operations/<int:id>/demarrer', methods=['POST'])
@login_required
def operation_start(id):
    """Démarrer une opération"""
    operation = Operation.query.get_or_404(id)
    
    if operation.statut != 'planifie':
        flash('Cette opération ne peut pas être démarrée', 'warning')
        return redirect(url_for('production.operation_detail', id=id))
    
    operation.statut = 'en_cours'
    operation.date_debut_reel = datetime.utcnow()
    db.session.commit()
    
    flash(f'Opération "{operation.code}" démarrée', 'success')
    return redirect(url_for('production.operation_detail', id=id))

@production_bp.route('/operations/<int:id>/terminer', methods=['GET', 'POST'])
@login_required
def operation_complete(id):
    """Terminer une opération et enregistrer les consommations"""
    operation = Operation.query.get_or_404(id)
    
    if request.method == 'POST':
        operation.statut = 'realise'
        operation.date_fin_reel = datetime.utcnow()
        operation.cout_reel = float(request.form.get('cout_reel', 0))
        db.session.commit()
        
        flash(f'Opération "{operation.code}" terminée', 'success')
        return redirect(url_for('production.operation_detail', id=id))
    
    # Formulaire pour ajouter les intrants consommés
    intrant_form = OperationIntrantForm()
    intrant_form.lot_id.choices = [(l.id, f"{l.numero_lot} - {l.intrant.nom} ({l.quantite_actuelle} {l.intrant.unite})") 
                                   for l in LotIntrant.query.filter(LotIntrant.quantite_actuelle > 0).all()]
    
    employe_form = OperationEmployeForm()
    
    return render_template(
        'production/operation_complete.html',
        operation=operation,
        intrant_form=intrant_form,
        employe_form=employe_form
    )

@production_bp.route('/operations/<int:id>/ajouter-intrant', methods=['POST'])
@login_required
def operation_add_intrant(id):
    """Ajouter un intrant consommé pendant l'opération"""
    operation = Operation.query.get_or_404(id)
    form = OperationIntrantForm()
    
    form.lot_id.choices = [(l.id, "") for l in LotIntrant.query.all()]  # Simplifié
    
    if form.validate_on_submit():
        lot = LotIntrant.query.get(form.lot_id.data)
        
        # Vérifier le stock
        if form.quantite_reelle.data > lot.quantite_actuelle:
            flash('Quantité insuffisante en stock', 'danger')
            return redirect(url_for('production.operation_complete', id=id))
        
        op_intrant = OperationIntrant(
            operation_id=id,
            lot_id=form.lot_id.data,
            intrant_id=lot.intrant_id,
            quantite_reelle=form.quantite_reelle.data,
            cout=form.cout.data or 0
        )
        db.session.add(op_intrant)
        db.session.commit()
        
        flash(f'Intrant ajouté: {lot.intrant.nom} - {form.quantite_reelle.data} {lot.intrant.unite}', 'success')
    
    return redirect(url_for('production.operation_complete', id=id))

@production_bp.route('/operations/<int:id>/ajouter-employe', methods=['POST'])
@login_required
def operation_add_employe(id):
    """Ajouter un employé à l'opération"""
    form = OperationEmployeForm()
    
    if form.validate_on_submit():
        employe = OperationEmploye(
            operation_id=id,
            nom_employe=form.nom_employe.data,
            fonction=form.fonction.data,
            heures_travaillees=form.heures_travaillees.data,
            taux_horaire=form.taux_horaire.data,
            cout_total=form.heures_travaillees.data * form.taux_horaire.data
        )
        db.session.add(employe)
        db.session.commit()
        
        flash(f'Employé {form.nom_employe.data} ajouté', 'success')
    
    return redirect(url_for('production.operation_complete', id=id))