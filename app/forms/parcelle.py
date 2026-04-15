from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, SubmitField, TextAreaField, DateField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Length, Optional

class ParcelleForm(FlaskForm):
    """Formulaire pour créer/modifier une parcelle"""
    nom = StringField('Nom de la parcelle', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=100, message='Le nom doit faire entre 2 et 100 caractères')
    ])
    superficie_ha = FloatField('Superficie (hectares)', validators=[
        DataRequired(message='La superficie est obligatoire'),
        NumberRange(min=0.01, max=10000, message='La superficie doit être entre 0.01 et 10000 ha')
    ])
    localisation = StringField('Localisation', validators=[
        Optional(),
        Length(max=200)
    ])
    type_sol = SelectField('Type de sol', choices=[
        ('', 'Sélectionner un type de sol'),
        ('argileux', 'Argileux'),
        ('sableux', 'Sableux'),
        ('limoneux', 'Limoneux'),
        ('humifère', 'Humifère'),
        ('calcaire', 'Calcaire'),
        ('mixte', 'Mixte')
    ], validators=[Optional()])
    culture_principale = StringField('Culture principale', validators=[
        Optional(),
        Length(max=100)
    ])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Créer')

class EquipementForm(FlaskForm):
    """Formulaire pour créer/modifier un équipement"""
    nom = StringField('Nom de l\'équipement', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=100)
    ])
    type = SelectField('Type d\'équipement', choices=[
        ('', 'Sélectionner un type'),
        ('tracteur', 'Tracteur'),
        ('moissonneuse', 'Moissonneuse-batteuse'),
        ('pulverisateur', 'Pulvérisateur'),
        ('broyeur', 'Broyeur'),
        ('charrues', 'Charrues'),
        ('herse', 'Herse'),
        ('remorque', 'Remorque'),
        ('autre', 'Autre')
    ], validators=[DataRequired(message='Le type est obligatoire')])
    marque = StringField('Marque', validators=[Optional(), Length(max=50)])
    modele = StringField('Modèle', validators=[Optional(), Length(max=50)])
    numero_serie = StringField('Numéro de série', validators=[Optional(), Length(max=100)])
    date_achat = DateField('Date d\'achat', validators=[Optional()])
    valeur_achat = FloatField('Valeur d\'achat (€)', validators=[
        Optional(),
        NumberRange(min=0, message='La valeur doit être positive')
    ])
    parcelle_id = SelectField('Parcelle associée', choices=[], validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Créer')
    
    def __init__(self, *args, **kwargs):
        super(EquipementForm, self).__init__(*args, **kwargs)
        # Les choix pour parcelle_id seront chargés dynamiquement dans la route