from app import db
from datetime import datetime
from enum import Enum

class StatutVente(Enum):
    BROUILLON = 'brouillon'
    CONFIRME = 'confirme'
    LIVRE = 'livre'
    FACTURE = 'facture'
    PAYE = 'paye'
    ANNULE = 'annule'

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # particulier, entreprise, cooperative, exportateur
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(50), default='RDC')
    
    # Informations fiscales
    numero_tva = db.Column(db.String(50))
    numero_compte = db.Column(db.String(50))
    
    # Contact
    contact_nom = db.Column(db.String(100))
    contact_telephone = db.Column(db.String(20))
    
    est_actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    ventes = db.relationship('Vente', backref='client', lazy=True)
    
    def __repr__(self):
        return f'<Client {self.code} - {self.nom}>'
    
    @property
    def total_achats(self):
        return sum(v.montant_total for v in self.ventes if v.statut == 'paye')

class Vente(db.Model):
    __tablename__ = 'ventes'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_devis = db.Column(db.String(50), unique=True)
    numero_commande = db.Column(db.String(50), unique=True)
    numero_facture = db.Column(db.String(50), unique=True)
    numero_livraison = db.Column(db.String(50), unique=True)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    recolte_id = db.Column(db.Integer, db.ForeignKey('recoltes.id'), nullable=False)
    
    # Quantités et prix
    quantite_tonnes = db.Column(db.Float, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)  # €/tonne
    montant_ht = db.Column(db.Float, nullable=False)
    taux_tva = db.Column(db.Float, default=0)  # 0, 16, 18%
    montant_tva = db.Column(db.Float, default=0)
    montant_ttc = db.Column(db.Float, nullable=False)
    
    # Dates du workflow
    date_devis = db.Column(db.DateTime, default=datetime.utcnow)
    date_commande = db.Column(db.DateTime)
    date_livraison_prevue = db.Column(db.Date)
    date_livraison_reelle = db.Column(db.Date)
    date_facture = db.Column(db.DateTime)
    date_paiement = db.Column(db.Date)
    
    # Statut
    statut = db.Column(db.String(20), default='brouillon')
    
    # Paiement
    conditions_paiement = db.Column(db.String(100))  # "30 jours", "à réception"
    est_paye = db.Column(db.Boolean, default=False)
    montant_paye = db.Column(db.Float, default=0)
    
    # Livraison
    adresse_livraison = db.Column(db.String(200))
    transporteur = db.Column(db.String(100))
    numero_suivi = db.Column(db.String(100))
    
    # Documents
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<Vente {self.numero_facture or self.numero_devis} - {self.montant_ttc}€>'
    
    @property
    def reste_a_payer(self):
        return round(self.montant_ttc - self.montant_paye, 2)
    
    @property
    def est_totalement_paye(self):
        return self.reste_a_payer <= 0
    
    @property
    def progression(self):
        """Progression du workflow"""
        etapes = ['brouillon', 'confirme', 'livre', 'facture', 'paye']
        if self.statut in etapes:
            return (etapes.index(self.statut) / (len(etapes) - 1)) * 100
        return 0

class Paiement(db.Model):
    """Suivi des paiements reçus"""
    __tablename__ = 'paiements'
    
    id = db.Column(db.Integer, primary_key=True)
    vente_id = db.Column(db.Integer, db.ForeignKey('ventes.id'), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    mode = db.Column(db.String(50))  # especes, virement, cheque, mobile_money
    reference = db.Column(db.String(100))
    date_paiement = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    vente = db.relationship('Vente', backref='paiements')