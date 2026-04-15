from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, DateField, IntegerField, BooleanField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from app.models.vente import Client, Vente

class ClientForm(FlaskForm):
    """Formulaire pour créer/modifier un client"""
    code = StringField('Code client', validators=[
        DataRequired(),
        Length(min=2, max=50)
    ])
    nom = StringField('Nom / Raison sociale', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    type = SelectField('Type de client', choices=[
        ('particulier', 'Particulier'),
        ('entreprise', 'Entreprise'),
        ('cooperative', 'Coopérative'),
        ('exportateur', 'Exportateur')
    ])
    email = StringField('Email', validators=[Optional()])
    telephone = StringField('Téléphone', validators=[Optional()])
    adresse = StringField('Adresse', validators=[Optional()])
    ville = StringField('Ville', validators=[Optional()])
    pays = StringField('Pays', default='RDC')
    numero_tva = StringField('N° TVA', validators=[Optional()])
    contact_nom = StringField('Nom du contact', validators=[Optional()])
    contact_telephone = StringField('Téléphone du contact', validators=[Optional()])
    est_actif = BooleanField('Actif', default=True)

class VenteForm(FlaskForm):
    """Formulaire pour créer une vente"""
    client_id = SelectField('Client', choices=[], coerce=int, validators=[DataRequired()])
    recolte_id = SelectField('Lot de récolte', choices=[], coerce=int, validators=[DataRequired()])
    quantite_tonnes = FloatField('Quantité (tonnes)', validators=[
        DataRequired(),
        NumberRange(min=0.01)
    ])
    prix_unitaire = FloatField('Prix unitaire (€/tonne)', validators=[
        DataRequired(),
        NumberRange(min=0)
    ])
    taux_tva = SelectField('TVA (%)', choices=[
        (0, '0%'),
        (16, '16%'),
        (18, '18%')
    ], coerce=float, default=0)
    date_livraison_prevue = DateField('Date de livraison prévue', validators=[Optional()])
    conditions_paiement = SelectField('Conditions de paiement', choices=[
        ('a_reception', 'À réception'),
        ('15_jours', '15 jours'),
        ('30_jours', '30 jours'),
        ('45_jours', '45 jours')
    ])
    adresse_livraison = StringField('Adresse de livraison', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    # Champ caché pour stocker la quantité max disponible
    max_disponible = HiddenField()
    
    def validate_quantite_tonnes(self, field):
        if field.data > float(self.max_disponible.data) if self.max_disponible.data else 0:
            raise ValidationError(f'Quantité insuffisante. Maximum disponible: {self.max_disponible.data} tonnes')

class PaiementForm(FlaskForm):
    """Formulaire pour enregistrer un paiement"""
    montant = FloatField('Montant (€)', validators=[
        DataRequired(),
        NumberRange(min=0.01)
    ])
    mode = SelectField('Mode de paiement', choices=[
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
        ('cheque', 'Chèque'),
        ('mobile_money', 'Mobile Money')
    ])
    reference = StringField('Référence', validators=[Optional()])
    date_paiement = DateField('Date de paiement', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])