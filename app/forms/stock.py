from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, DateField, IntegerField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from app.models.stock import Intrant, LotIntrant

class IntrantForm(FlaskForm):
    """Formulaire pour créer/modifier un intrant"""
    nom = StringField('Nom de l\'intrant', validators=[
        DataRequired(message='Le nom est obligatoire'),
        Length(min=2, max=100)
    ])
    code = StringField('Code', validators=[
        DataRequired(message='Le code est obligatoire'),
        Length(min=2, max=50)
    ])
    type = SelectField('Type', choices=[
        ('', 'Sélectionner'),
        ('semence', 'Semence'),
        ('engrais', 'Engrais'),
        ('pesticide', 'Pesticide'),
        ('herbicide', 'Herbicide'),
        ('carburant', 'Carburant'),
        ('autre', 'Autre')
    ], validators=[DataRequired()])
    categorie = StringField('Catégorie', validators=[Optional(), Length(max=50)])
    unite = SelectField('Unité', choices=[
        ('kg', 'Kilogramme (kg)'),
        ('g', 'Gramme (g)'),
        ('L', 'Litre (L)'),
        ('sac', 'Sac'),
        ('unite', 'Unité')
    ], default='kg')
    prix_unitaire = FloatField('Prix unitaire (€)', validators=[
        Optional(),
        NumberRange(min=0)
    ])
    fournisseur_principal = StringField('Fournisseur principal', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    est_actif = BooleanField('Actif', default=True)

class LotIntrantForm(FlaskForm):
    """Formulaire pour créer un lot d'intrant"""
    numero_lot = StringField('Numéro de lot', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    intrant_id = SelectField('Intrant', choices=[], coerce=int, validators=[DataRequired()])
    quantite_initiale = FloatField('Quantité initiale', validators=[
        DataRequired(),
        NumberRange(min=0.01)
    ])
    prix_achat = FloatField("Prix d'achat (€)", validators=[Optional(), NumberRange(min=0)])
    date_fabrication = DateField('Date de fabrication', validators=[Optional()])
    date_peremption = DateField('Date de péremption', validators=[Optional()])
    depot_id = SelectField('Dépôt', choices=[], coerce=int, validators=[DataRequired()])
    fournisseur = StringField('Fournisseur', validators=[Optional()])
    facture_numero = StringField('N° de facture', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    def validate_numero_lot(self, field):
        if LotIntrant.query.filter_by(numero_lot=field.data).first():
            raise ValidationError('Ce numéro de lot existe déjà')

class MouvementStockForm(FlaskForm):
    """Formulaire pour enregistrer un mouvement de stock"""
    type = SelectField('Type de mouvement', choices=[
        ('sortie', 'Sortie (consommation)'),
        ('perte', 'Perte'),
        ('ajustement', 'Ajustement'),
        ('transfert', 'Transfert entre dépôts')
    ], validators=[DataRequired()])
    lot_id = SelectField('Lot', choices=[], coerce=int, validators=[DataRequired()])
    quantite = FloatField('Quantité', validators=[
        DataRequired(),
        NumberRange(min=0.01)
    ])
    motif = StringField('Motif', validators=[
        DataRequired(),
        Length(min=3, max=200)
    ])
    reference = StringField('Référence (commande/opération)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])

class DepotForm(FlaskForm):
    """Formulaire pour créer/modifier un dépôt"""
    nom = StringField('Nom du dépôt', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    code = StringField('Code', validators=[
        DataRequired(),
        Length(min=2, max=20)
    ])
    type = SelectField('Type', choices=[
        ('principal', 'Entrepôt principal'),
        ('terrain', 'Dépôt terrain'),
        ('magasin', 'Magasin'),
        ('externe', 'Externe (tiers)')
    ])
    localisation = StringField('Localisation', validators=[Optional()])
    responsable = StringField('Responsable', validators=[Optional()])
    est_actif = BooleanField('Actif', default=True)