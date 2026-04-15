from app import db
from datetime import datetime
from sqlalchemy import event

class Recolte(db.Model):
    __tablename__ = 'recoltes'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_lot = db.Column(db.String(100), unique=True, nullable=False)
    parcelle_id = db.Column(db.Integer, db.ForeignKey('parcelles.id'), nullable=False)
    campagne_id = db.Column(db.Integer, db.ForeignKey('campagnes.id'))
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'))  # Opération de récolte associée
    
    culture = db.Column(db.String(100), nullable=False)
    variete = db.Column(db.String(100))
    
    # Quantités
    quantite_brute_tonnes = db.Column(db.Float, nullable=False)  # Poids total récolté
    quantite_nette_tonnes = db.Column(db.Float, nullable=False)  # Après nettoyage/tri
    pertes_tonnes = db.Column(db.Float, default=0)
    
    # Qualité
    qualite = db.Column(db.String(50))  # Extra, Première, Seconde, Déchet
    calibre = db.Column(db.String(50))  # Gros, Moyen, Petit
    humidite_pourcent = db.Column(db.Float)  # Taux d'humidité
    notes_qualite = db.Column(db.Text)
    
    # Dates
    date_recolte = db.Column(db.Date, nullable=False)
    date_stockage = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Stockage
    depot_id = db.Column(db.Integer, db.ForeignKey('depots.id'))  # Où est stockée la récolte
    est_entierement_vendue = db.Column(db.Boolean, default=False)
    
    # Traçabilité
    certificat_analyse = db.Column(db.String(200))  # Lien vers PDF
    photos = db.Column(db.Text)  # URLs des photos (JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relations
    parcelle = db.relationship('Parcelle')
    campagne = db.relationship('Campagne', backref='recoltes')
    operation = db.relationship('Operation', backref='recolte_associee')
    depot = db.relationship('Depot', backref='recoltes')
    ventes = db.relationship('Vente', backref='recolte', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Recolte {self.numero_lot} - {self.culture} - {self.quantite_nette_tonnes}t>'
    
    @property
    def quantite_disponible(self):
        """Quantité non encore vendue"""
        vendu = sum(v.quantite_tonnes for v in self.ventes if v.statut != 'annule')
        return round(self.quantite_nette_tonnes - vendu, 2)
    
    @property
    def est_disponible(self):
        return self.quantite_disponible > 0
    
    @property
    def taux_pertes(self):
        if self.quantite_brute_tonnes > 0:
            return round((self.pertes_tonnes / self.quantite_brute_tonnes) * 100, 2)
        return 0

class ControleQualite(db.Model):
    """Contrôles qualité effectués sur une récolte"""
    __tablename__ = 'controles_qualite'
    
    id = db.Column(db.Integer, primary_key=True)
    recolte_id = db.Column(db.Integer, db.ForeignKey('recoltes.id'), nullable=False)
    date_controle = db.Column(db.DateTime, default=datetime.utcnow)
    controleur = db.Column(db.String(100))
    
    # Paramètres analysés
    purete_pourcent = db.Column(db.Float)  # % de produit pur
    impuretes_pourcent = db.Column(db.Float)  # % d'impuretés
    taux_proteines = db.Column(db.Float)  # Pour certaines cultures
    taux_sucre = db.Column(db.Float)  # Pour fruits
    presence_moisissure = db.Column(db.Boolean, default=False)
    presence_insectes = db.Column(db.Boolean, default=False)
    
    resultat = db.Column(db.String(20))  # Conforme, Non conforme, À surveiller
    commentaires = db.Column(db.Text)
    
    recolte = db.relationship('Recolte', backref='controles_qualite')

class StockRecolte(db.Model):
    """Suivi des mouvements de stock des récoltes (similaire aux intrants)"""
    __tablename__ = 'stock_recoltes'
    
    id = db.Column(db.Integer, primary_key=True)
    recolte_id = db.Column(db.Integer, db.ForeignKey('recoltes.id'), nullable=False)
    type_mouvement = db.Column(db.String(20))  # entree_stock, sortie_vente, perte, transfert
    quantite_tonnes = db.Column(db.Float, nullable=False)
    quantite_avant = db.Column(db.Float)
    quantite_apres = db.Column(db.Float)
    reference = db.Column(db.String(100))  # Numéro de vente, etc.
    motif = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    recolte = db.relationship('Recolte', backref='mouvements_stock')

# Signal pour mettre à jour le stock après une vente
@event.listens_for(Recolte.ventes, 'append')
def update_stock_after_sale(target, value, initiator):
    """Quand une vente est ajoutée, vérifier qu'on ne dépasse pas le stock"""
    if value.statut == 'confirme' and value.quantite_tonnes > target.quantite_disponible + value.quantite_tonnes:
        raise ValueError(f"Stock insuffisant. Disponible: {target.quantite_disponiente}")