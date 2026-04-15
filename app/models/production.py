from app import db
from datetime import datetime
from enum import Enum
from sqlalchemy import event
from app.models.stock import LotIntrant

class StatutOperation(Enum):
    PLANIFIE = 'planifie'
    EN_COURS = 'en_cours'
    REALISE = 'realise'
    ANNULE = 'annule'
    REPORTE = 'reporte'

class Campagne(db.Model):
    __tablename__ = 'campagnes'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    objectif_principal = db.Column(db.Text)
    budget_prevu = db.Column(db.Float, default=0)
    budget_reel = db.Column(db.Float, default=0)
    statut = db.Column(db.String(20), default='planifie')  # planifie, actif, termine, annule
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    operations = db.relationship('Operation', backref='campagne', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Campagne {self.code} - {self.nom}>'
    
    @property
    def progression(self):
        """Calculer la progression de la campagne"""
        total = len(self.operations)
        if total == 0:
            return 0
        realisees = len([op for op in self.operations if op.statut == 'realise'])
        return round((realisees / total) * 100, 2)
    
    @property
    def ecart_budget(self):
        return self.budget_reel - self.budget_prevu

class Operation(db.Model):
    __tablename__ = 'operations'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    type = db.Column(db.String(50), nullable=False)  # labour, semis, irrigation, traitement, fertilisation, recolte, autre
    description = db.Column(db.Text)
    date_prevue = db.Column(db.Date, nullable=False)
    date_debut_reel = db.Column(db.DateTime)
    date_fin_reel = db.Column(db.DateTime)
    statut = db.Column(db.String(20), default='planifie')
    priorite = db.Column(db.Integer, default=1)  # 1=haute, 2=moyenne, 3=basse
    cout_estime = db.Column(db.Float, default=0)
    cout_reel = db.Column(db.Float, default=0)
    
    # Relations
    parcelle_id = db.Column(db.Integer, db.ForeignKey('parcelles.id'), nullable=False)
    campagne_id = db.Column(db.Integer, db.ForeignKey('campagnes.id'), nullable=False)
    responsable_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ressources
    intrants_utilises = db.relationship('OperationIntrant', backref='operation', lazy=True, cascade='all, delete-orphan')
    employes = db.relationship('OperationEmploye', backref='operation', lazy=True, cascade='all, delete-orphan')
    equipements_utilises = db.relationship('OperationEquipement', backref='operation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Operation {self.code} - {self.type} - {self.statut}>'
    
    @property
    def est_en_retard(self):
        if self.statut not in ['realise', 'annule'] and self.date_prevue < datetime.now().date():
            return True
        return False
    
    @property
    def duree_reelle(self):
        if self.date_debut_reel and self.date_fin_reel:
            delta = self.date_fin_reel - self.date_debut_reel
            return delta.total_seconds() / 3600  # en heures
        return None

class OperationIntrant(db.Model):
    __tablename__ = 'operations_intrants'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots_intrants.id'), nullable=False)
    intrant_id = db.Column(db.Integer, db.ForeignKey('intrants.id'), nullable=False)
    quantite_prevue = db.Column(db.Float)
    quantite_reelle = db.Column(db.Float, nullable=False)
    cout = db.Column(db.Float, default=0)
    
    # Relations
    lot = db.relationship('LotIntrant', backref='operations_consommees')
    intrant = db.relationship('Intrant', backref='operations_consommees')

class OperationEmploye(db.Model):
    __tablename__ = 'operations_employes'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)
    nom_employe = db.Column(db.String(100), nullable=False)
    fonction = db.Column(db.String(50))
    heures_travaillees = db.Column(db.Float, default=0)
    taux_horaire = db.Column(db.Float, default=0)
    cout_total = db.Column(db.Float, default=0)

class OperationEquipement(db.Model):
    __tablename__ = 'operations_equipements'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=False)
    equipement_id = db.Column(db.Integer, db.ForeignKey('equipements.id'), nullable=False)
    heures_utilisation = db.Column(db.Float, default=0)
    cout_horaire = db.Column(db.Float, default=0)
    
    equipement = db.relationship('Equipement', backref='operations_utilisations')

# Signal pour consommer les intrants automatiquement
@event.listens_for(OperationIntrant, 'after_insert')
def consume_intrant(mapper, connection, target):
    """Quand on ajoute un intrant à une opération, le consommer du stock"""
    from sqlalchemy import update
    
    # Mettre à jour la quantité du lot
    stmt = update(LotIntrant).where(LotIntrant.id == target.lot_id).values(
        quantite_actuelle = LotIntrant.quantite_actuelle - target.quantite_reelle
    )
    connection.execute(stmt)
    
    # Créer un mouvement de stock automatique
    from app.models.stock import MouvementStock
    # Note: en vrai, il faudrait insérer dans la table mouvements