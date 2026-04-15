from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, DateField, BooleanField, FileField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from app.models.recolte import Recolte

class RecolteForm(FlaskForm):
    """Formulaire pour enregistrer une récolte"""
    numero_lot = StringField('Numéro de lot', validators=[
        DataRequired(message='Le numéro de lot est obligatoire'),
        Length(min=3, max=100)
    ])
    parcelle_id = SelectField('Parcelle', choices=[], coerce=int, validators=[DataRequired()])
    campagne_id = SelectField('Campagne', choices=[], coerce=int, validators=[Optional()])
    operation_id = SelectField('Opération de récolte', choices=[], coerce=int, validators=[Optional()])
    
    culture = StringField('Culture', validators=[DataRequired(), Length(max=100)])
    variete = StringField('Variété', validators=[Optional(), Length(max=100)])
    
    quantite_brute_tonnes = FloatField('Quantité brute (tonnes)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='La quantité doit être positive')
    ])
    pertes_tonnes = FloatField('Pertes (tonnes)', validators=[
        Optional(),
        NumberRange(min=0)
    ])
    
    qualite = SelectField('Qualité', choices=[
        ('', 'Sélectionner'),
        ('Extra', 'Extra'),
        ('Première', 'Première'),
        ('Seconde', 'Seconde'),
        ('Déchet', 'Déchet')
    ])
    calibre = SelectField('Calibre', choices=[
        ('', 'Sélectionner'),
        ('Gros', 'Gros'),
        ('Moyen', 'Moyen'),
        ('Petit', 'Petit')
    ])
    humidite_pourcent = FloatField('Taux d\'humidité (%)', validators=[
        Optional(),
        NumberRange(0, 100)
    ])
    
    date_recolte = DateField('Date de récolte', validators=[DataRequired()])
    depot_id = SelectField('Dépôt de stockage', choices=[], coerce=int, validators=[DataRequired()])
    
    notes_qualite = TextAreaField('Notes sur la qualité', validators=[Optional()])
    
    def validate_numero_lot(self, field):
        if Recolte.query.filter_by(numero_lot=field.data).first():
            raise ValidationError('Ce numéro de lot existe déjà')
    
    def validate_pertes_tonnes(self, field):
        if field.data and field.data > self.quantite_brute_tonnes.data:
            raise ValidationError('Les pertes ne peuvent pas dépasser la quantité brute')

class ControleQualiteForm(FlaskForm):
    """Formulaire pour ajouter un contrôle qualité"""
    controleur = StringField('Contrôleur', validators=[Optional()])
    purete_pourcent = FloatField('Pureté (%)', validators=[Optional(), NumberRange(0, 100)])
    impuretes_pourcent = FloatField('Impuretés (%)', validators=[Optional(), NumberRange(0, 100)])
    taux_proteines = FloatField('Taux de protéines (%)', validators=[Optional(), NumberRange(0, 100)])
    taux_sucre = FloatField('Taux de sucre (%)', validators=[Optional(), NumberRange(0, 100)])
    presence_moisissure = BooleanField('Présence de moisissure')
    presence_insectes = BooleanField('Présence d\'insectes')
    resultat = SelectField('Résultat', choices=[
        ('Conforme', 'Conforme'),
        ('Non conforme', 'Non conforme'),
        ('À surveiller', 'À surveiller')
    ])
    commentaires = TextAreaField('Commentaires')