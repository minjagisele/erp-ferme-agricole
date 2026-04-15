from app import db
from datetime import datetime

class Fournisseur(db.Model):
    __tablename__ = 'fournisseurs'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    
    commandes = db.relationship('CommandeAchat', backref='fournisseur', lazy=True)

class CommandeAchat(db.Model):
    __tablename__ = 'commandes_achat'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_commande = db.Column(db.String(50), unique=True)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'))
    intrant_id = db.Column(db.Integer, db.ForeignKey('intrants.id'))
    quantite = db.Column(db.Float)
    prix_total = db.Column(db.Float)
    date_commande = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.String(20), default='brouillon')  # brouillon, envoye, recu, annule