from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, DateField, IntegerField, DateTimeField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from datetime import datetime

class CampagneForm(FlaskForm):
    """Formulaire pour créer/modifier une campagne"""
    nom = StringField('Nom de la campagne', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    code = StringField('Code', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    date_debut = DateField('Date de début', validators=[DataRequired()])
    date_fin = DateField('Date de fin', validators=[DataRequired()])
    objectif_principal = TextAreaField('Objectif principal', validators=[Optional()])
    budget_prevu = FloatField('Budget prévu (€)', validators=[Optional(), NumberRange(min=0)])
    statut = SelectField('Statut', choices=[
        ('planifie', 'Planifié'),
        ('actif', 'Actif'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé')
    ], default='planifie')
    
    def validate_date_fin(self, field):
        if field.data < self.date_debut.data:
            raise ValidationError('La date de fin doit être après la date de début')

class OperationForm(FlaskForm):
    """Formulaire pour créer/modifier une opération"""
    code = StringField('Code opération', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    type = SelectField('Type d\'opération', choices=[
        ('labour', 'Labour'),
        ('semis', 'Semis'),
        ('irrigation', 'Irrigation'),
        ('traitement', 'Traitement phytosanitaire'),
        ('fertilisation', 'Fertilisation'),
        ('recolte', 'Récolte'),
        ('autre', 'Autre')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    date_prevue = DateField('Date prévue', validators=[DataRequired()])
    priorite = SelectField('Priorité', choices=[
        (1, 'Haute'),
        (2, 'Moyenne'),
        (3, 'Basse')
    ], coerce=int, default=2)
    cout_estime = FloatField('Coût estimé (€)', validators=[Optional(), NumberRange(min=0)])
    parcelle_id = SelectField('Parcelle', choices=[], coerce=int, validators=[DataRequired()])
    campagne_id = SelectField('Campagne', choices=[], coerce=int, validators=[DataRequired()])
    responsable_id = SelectField('Responsable', choices=[], coerce=int, validators=[Optional()])

class OperationIntrantForm(FlaskForm):
    """Formulaire pour ajouter un intrant à une opération"""
    lot_id = SelectField('Lot', choices=[], coerce=int, validators=[DataRequired()])
    quantite_reelle = FloatField('Quantité utilisée', validators=[
        DataRequired(),
        NumberRange(min=0.01)
    ])
    cout = FloatField('Coût (€)', validators=[Optional(), NumberRange(min=0)])

class OperationEmployeForm(FlaskForm):
    """Formulaire pour ajouter un employé à une opération"""
    nom_employe = StringField('Nom employé', validators=[DataRequired()])
    fonction = StringField('Fonction', validators=[Optional()])
    heures_travaillees = FloatField('Heures', validators=[DataRequired(), NumberRange(min=0.1)])
    taux_horaire = FloatField('Taux horaire (€)', validators=[DataRequired(), NumberRange(min=0)])