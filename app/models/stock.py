from app import db
from datetime import datetime
from sqlalchemy import event

class Intrant(db.Model):
    __tablename__ = 'intrants'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(50))  # semence, engrais, pesticide, herbicide, carburant, autre
    categorie = db.Column(db.String(50))  # sous-catégorie
    unite = db.Column(db.String(20), default='kg')  # kg, L, sac, unité
    prix_unitaire = db.Column(db.Float, default=0)
    fournisseur_principal = db.Column(db.String(100))
    description = db.Column(db.Text)
    est_actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lots = db.relationship('LotIntrant', backref='intrant', lazy=True, cascade='all, delete-orphan')
    mouvements = db.relationship('MouvementStock', backref='intrant', lazy=True)
    
    def __repr__(self):
        return f'<Intrant {self.code} - {self.nom}>'
    
    @property
    def stock_total(self):
        """Calculer le stock total tous lots confondus"""
        total = db.session.query(db.func.sum(LotIntrant.quantite_actuelle)).filter(
            LotIntrant.intrant_id == self.id,
            LotIntrant.est_actif == True
        ).scalar() or 0
        return round(total, 2)
    
    @property
    def lots_actifs(self):
        return LotIntrant.query.filter_by(intrant_id=self.id, est_actif=True).count()

class LotIntrant(db.Model):
    __tablename__ = 'lots_intrants'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_lot = db.Column(db.String(100), unique=True, nullable=False)
    intrant_id = db.Column(db.Integer, db.ForeignKey('intrants.id'), nullable=False)
    quantite_initiale = db.Column(db.Float, nullable=False)
    quantite_actuelle = db.Column(db.Float, nullable=False)
    prix_achat = db.Column(db.Float)
    date_fabrication = db.Column(db.Date)
    date_peremption = db.Column(db.Date)
    date_reception = db.Column(db.DateTime, default=datetime.utcnow)
    depot_id = db.Column(db.Integer, db.ForeignKey('depots.id'))
    fournisseur = db.Column(db.String(100))
    facture_numero = db.Column(db.String(100))
    est_actif = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    
    # Relations
    mouvements = db.relationship('MouvementStock', backref='lot', lazy=True)
    
    def __repr__(self):
        return f'<Lot {self.numero_lot} - {self.quantite_actuelle}/{self.quantite_initiale}>'
    
    @property
    def est_pereime(self):
        if self.date_peremption:
            return self.date_peremption < datetime.now().date()
        return False
    
    @property
    def jours_avant_peremption(self):
        if self.date_peremption:
            delta = (self.date_peremption - datetime.now().date()).days
            return max(0, delta)
        return None
    
    @property
    def taux_consommation(self):
        if self.quantite_initiale > 0:
            return round((1 - self.quantite_actuelle / self.quantite_initiale) * 100, 2)
        return 0

class Depot(db.Model):
    __tablename__ = 'depots'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    type = db.Column(db.String(50))  # principal, terrain, magasin, externe
    localisation = db.Column(db.String(200))
    responsable = db.Column(db.String(100))
    est_actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    lots = db.relationship('LotIntrant', backref='depot', lazy=True)
    
    def __repr__(self):
        return f'<Depot {self.code} - {self.nom}>'

class MouvementStock(db.Model):
    __tablename__ = 'mouvements_stock'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_mouvement = db.Column(db.String(100), unique=True, nullable=False)
    intrant_id = db.Column(db.Integer, db.ForeignKey('intrants.id'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('lots_intrants.id'), nullable=False)
    type = db.Column(db.String(20))  # entree, sortie, perte, ajustement, transfert
    quantite = db.Column(db.Float, nullable=False)
    quantite_avant = db.Column(db.Float)
    quantite_apres = db.Column(db.Float)
    motif = db.Column(db.String(200))
    reference = db.Column(db.String(100))  # numéro de commande, d'opération, etc.
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Mouvement {self.numero_mouvement} - {self.type} {self.quantite}>'

# Signal pour mettre à jour les quantités automatiquement
@event.listens_for(MouvementStock, 'after_insert')
def update_lot_quantity(mapper, connection, target):
    """Met à jour la quantité du lot après chaque mouvement"""
    from sqlalchemy import update
    if target.type == 'entree':
        stmt = update(LotIntrant).where(LotIntrant.id == target.lot_id).values(
            quantite_actuelle = LotIntrant.quantite_actuelle + target.quantite
        )
    else:  # sortie, perte, ajustement negatif
        stmt = update(LotIntrant).where(LotIntrant.id == target.lot_id).values(
            quantite_actuelle = LotIntrant.quantite_actuelle - target.quantite
        )
    connection.execute(stmt)