from app import db
from datetime import datetime

class Parcelle(db.Model):
    __tablename__ = 'parcelles'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    superficie_ha = db.Column(db.Float, nullable=False)
    localisation = db.Column(db.String(200))
    type_sol = db.Column(db.String(50))  # argileux, sableux, limoneux
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    equipements = db.relationship('Equipement', backref='parcelle', lazy=True)
    operations = db.relationship('Operation', backref='parcelle', lazy=True)
    recoltes = db.relationship('Recolte', lazy=True)

class Equipement(db.Model):
    __tablename__ = 'equipements'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # tracteur, moissonneuse, pulvérisateur
    date_achat = db.Column(db.Date)
    valeur_achat = db.Column(db.Float)
    parcelle_id = db.Column(db.Integer, db.ForeignKey('parcelles.id'), nullable=True)