from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models.parcelle import Parcelle, Equipement
from app.models.user import User
from app.forms.parcelle import ParcelleForm, EquipementForm
from app.utils.decorators import role_required, owner_or_admin
from sqlalchemy import or_
import pandas as pd
from io import BytesIO
from flask import Response
from datetime import datetime

parcelles_bp = Blueprint('parcelles', __name__, url_prefix='/parcelles')

# ================================================
# ROUTES POUR LES PARCELLES
# ================================================

@parcelles_bp.route('/')
@login_required
def index():
    """Liste des parcelles avec filtres et pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    type_sol = request.args.get('type_sol', '')
    
    # Base de la requête selon le rôle
    if current_user.is_admin() or current_user.is_manager():
        query = Parcelle.query
    else:
        query = Parcelle.query.filter_by(user_id=current_user.id)
    
    # Filtre recherche
    if search:
        query = query.filter(
            or_(
                Parcelle.nom.ilike(f'%{search}%'),
                Parcelle.localisation.ilike(f'%{search}%'),
                Parcelle.culture_principale.ilike(f'%{search}%')
            )
        )
    
    # Filtre type de sol
    if type_sol:
        query = query.filter_by(type_sol=type_sol)
    
    # Pagination (10 par page)
    pagination = query.order_by(Parcelle.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    parcelles = pagination.items
    
    # Statistiques pour le tableau de bord
    total_parcelles = query.count()
    total_superficie = db.session.query(db.func.sum(Parcelle.superficie_ha)).filter(
        Parcelle.id.in_([p.id for p in query.all()])
    ).scalar() or 0
    
    return render_template(
        'parcelles/index.html',
        parcelles=parcelles,
        pagination=pagination,
        search=search,
        type_sol=type_sol,
        total_parcelles=total_parcelles,
        total_superficie=round(total_superficie, 2),
        type_sol_choices=['argileux', 'sableux', 'limoneux', 'humifère', 'calcaire', 'mixte']
    )

@parcelles_bp.route('/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'user')
def create():
    """Créer une nouvelle parcelle"""
    form = ParcelleForm()
    
    if form.validate_on_submit():
        parcelle = Parcelle(
            nom=form.nom.data,
            superficie_ha=form.superficie_ha.data,
            localisation=form.localisation.data,
            type_sol=form.type_sol.data,
            culture_principale=form.culture_principale.data,
            user_id=current_user.id
        )
        
        db.session.add(parcelle)
        db.session.commit()
        
        flash(f'Parcelle "{parcelle.nom}" créée avec succès !', 'success')
        return redirect(url_for('parcelles.index'))
    
    return render_template('parcelles/create.html', form=form)

@parcelles_bp.route('/<int:id>')
@login_required
def show(id):
    """Afficher les détails d'une parcelle"""
    parcelle = Parcelle.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.can_edit(parcelle.user_id) and not current_user.is_admin():
        flash('Vous n\'avez pas accès à cette parcelle', 'danger')
        return redirect(url_for('parcelles.index'))
    
    # Récupérer les équipements associés
    equipements = Equipement.query.filter_by(parcelle_id=id).all()
    
    # Statistiques de la parcelle (à compléter avec les récoltes plus tard)
    stats = {
        'nb_equipements': len(equipements),
        'superficie': parcelle.superficie_ha,
        'rendement_estime': round(parcelle.superficie_ha * 2.5, 2)  # Estimation temporaire
    }
    
    return render_template('parcelles/show.html', parcelle=parcelle, equipements=equipements, stats=stats)

@parcelles_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Modifier une parcelle"""
    parcelle = Parcelle.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.can_edit(parcelle.user_id):
        flash('Vous n\'êtes pas autorisé à modifier cette parcelle', 'danger')
        return redirect(url_for('parcelles.index'))
    
    form = ParcelleForm(obj=parcelle)
    
    if form.validate_on_submit():
        parcelle.nom = form.nom.data
        parcelle.superficie_ha = form.superficie_ha.data
        parcelle.localisation = form.localisation.data
        parcelle.type_sol = form.type_sol.data
        parcelle.culture_principale = form.culture_principale.data
        parcelle.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Parcelle "{parcelle.nom}" mise à jour avec succès', 'success')
        return redirect(url_for('parcelles.show', id=parcelle.id))
    
    return render_template('parcelles/edit.html', form=form, parcelle=parcelle)

@parcelles_bp.route('/<int:id>/supprimer', methods=['POST'])
@login_required
def delete(id):
    """Supprimer une parcelle"""
    parcelle = Parcelle.query.get_or_404(id)
    
    # Vérifier les permissions
    if not current_user.can_edit(parcelle.user_id):
        flash('Vous n\'êtes pas autorisé à supprimer cette parcelle', 'danger')
        return redirect(url_for('parcelles.index'))
    
    # Vérifier s'il y a des équipements associés
    equipements_count = Equipement.query.filter_by(parcelle_id=id).count()
    if equipements_count > 0:
        flash(f'Impossible de supprimer : cette parcelle contient {equipements_count} équipement(s).', 'danger')
        return redirect(url_for('parcelles.show', id=id))
    
    nom = parcelle.nom
    db.session.delete(parcelle)
    db.session.commit()
    
    flash(f'Parcelle "{nom}" supprimée avec succès', 'success')
    return redirect(url_for('parcelles.index'))

@parcelles_bp.route('/export/excel')
@login_required
@role_required('admin', 'manager')
def export_excel():
    """Exporter les parcelles vers Excel"""
    if current_user.is_admin() or current_user.is_manager():
        parcelles = Parcelle.query.all()
    else:
        parcelles = Parcelle.query.filter_by(user_id=current_user.id).all()
    
    # Convertir en DataFrame pandas
    data = []
    for p in parcelles:
        data.append({
            'ID': p.id,
            'Nom': p.nom,
            'Superficie (ha)': p.superficie_ha,
            'Localisation': p.localisation or '',
            'Type de sol': p.type_sol or '',
            'Culture principale': p.culture_principale or '',
            'Propriétaire ID': p.user_id,
            'Date création': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''
        })
    
    df = pd.DataFrame(data)
    
    # Créer le fichier Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Parcelles', index=False)
    
    output.seek(0)
    
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment;filename=parcelles.xlsx'}
    )

# ================================================
# ROUTES POUR LES ÉQUIPEMENTS
# ================================================

@parcelles_bp.route('/equipements')
@login_required
def equipements_index():
    """Liste des équipements"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    type_equip = request.args.get('type', '')
    
    # Base de la requête
    if current_user.is_admin() or current_user.is_manager():
        query = Equipement.query
    else:
        # Les utilisateurs voient les équipements de leurs parcelles
        user_parcelles = Parcelle.query.filter_by(user_id=current_user.id).all()
        parcelle_ids = [p.id for p in user_parcelles]
        query = Equipement.query.filter(Equipement.parcelle_id.in_(parcelle_ids + [None]))
    
    # Filtres
    if search:
        query = query.filter(
            or_(
                Equipement.nom.ilike(f'%{search}%'),
                Equipement.marque.ilike(f'%{search}%'),
                Equipement.modele.ilike(f'%{search}%')
            )
        )
    
    if type_equip:
        query = query.filter_by(type=type_equip)
    
    pagination = query.order_by(Equipement.id.desc()).paginate(page=page, per_page=10, error_out=False)
    equipements = pagination.items
    
    return render_template(
        'equipements/index.html',
        equipements=equipements,
        pagination=pagination,
        search=search,
        type_equip=type_equip
    )

@parcelles_bp.route('/equipements/creer', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager', 'user')
def equipement_create():
    """Créer un nouvel équipement"""
    form = EquipementForm()
    
    # Remplir les choix des parcelles
    if current_user.is_admin() or current_user.is_manager():
        parcelles = Parcelle.query.all()
    else:
        parcelles = Parcelle.query.filter_by(user_id=current_user.id).all()
    
    form.parcelle_id.choices = [('', 'Aucune parcelle')] + [(p.id, f"{p.nom} ({p.superficie_ha} ha)") for p in parcelles]
    
    if form.validate_on_submit():
        equipement = Equipement(
            nom=form.nom.data,
            type=form.type.data,
            marque=form.marque.data,
            modele=form.modele.data,
            numero_serie=form.numero_serie.data,
            date_achat=form.date_achat.data,
            valeur_achat=form.valeur_achat.data,
            parcelle_id=form.parcelle_id.data if form.parcelle_id.data else None,
            notes=form.notes.data
        )
        
        db.session.add(equipement)
        db.session.commit()
        
        flash(f'Équipement "{equipement.nom}" ajouté avec succès !', 'success')
        return redirect(url_for('parcelles.equipements_index'))
    
    return render_template('equipements/create.html', form=form)

@parcelles_bp.route('/equipements/<int:id>/modifier', methods=['GET', 'POST'])
@login_required
def equipement_edit(id):
    """Modifier un équipement"""
    equipement = Equipement.query.get_or_404(id)
    
    # Vérifier les permissions
    if equipement.parcelle_id:
        parcelle = Parcelle.query.get(equipement.parcelle_id)
        if parcelle and not current_user.can_edit(parcelle.user_id):
            flash('Vous n\'êtes pas autorisé à modifier cet équipement', 'danger')
            return redirect(url_for('parcelles.equipements_index'))
    
    form = EquipementForm(obj=equipement)
    
    # Remplir les choix des parcelles
    if current_user.is_admin() or current_user.is_manager():
        parcelles = Parcelle.query.all()
    else:
        parcelles = Parcelle.query.filter_by(user_id=current_user.id).all()
    
    form.parcelle_id.choices = [('', 'Aucune parcelle')] + [(p.id, f"{p.nom} ({p.superficie_ha} ha)") for p in parcelles]
    
    if form.validate_on_submit():
        equipement.nom = form.nom.data
        equipement.type = form.type.data
        equipement.marque = form.marque.data
        equipement.modele = form.modele.data
        equipement.numero_serie = form.numero_serie.data
        equipement.date_achat = form.date_achat.data
        equipement.valeur_achat = form.valeur_achat.data
        equipement.parcelle_id = form.parcelle_id.data if form.parcelle_id.data else None
        
        db.session.commit()
        flash(f'Équipement "{equipement.nom}" mis à jour', 'success')
        return redirect(url_for('parcelles.equipements_index'))
    
    return render_template('equipements/edit.html', form=form, equipement=equipement)

@parcelles_bp.route('/equipements/<int:id>/supprimer', methods=['POST'])
@login_required
def equipement_delete(id):
    """Supprimer un équipement"""
    equipement = Equipement.query.get_or_404(id)
    
    # Vérifier les permissions
    if equipement.parcelle_id:
        parcelle = Parcelle.query.get(equipement.parcelle_id)
        if parcelle and not current_user.can_edit(parcelle.user_id):
            flash('Vous n\'êtes pas autorisé à supprimer cet équipement', 'danger')
            return redirect(url_for('parcelles.equipements_index'))
    
    nom = equipement.nom
    db.session.delete(equipement)
    db.session.commit()
    
    flash(f'Équipement "{nom}" supprimé', 'success')
    return redirect(url_for('parcelles.equipements_index'))