from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='viewer')  # admin, manager, user, viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relations
    parcelles = db.relationship('Parcelle', backref='proprietaire', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
    
    def set_password(self, password):
        """Hache le mot de passe avant stockage"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifie le mot de passe"""
        return check_password_hash(self.password_hash, password)
    
    # Méthodes de vérification des rôles
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def is_user(self):
        return self.role in ['admin', 'manager', 'user']
    
    def can_edit(self, resource_owner_id=None):
        """
        Vérifie si l'utilisateur peut modifier une ressource
        - Admin : toujours True
        - Manager : toujours True (sauf pour les users)
        - User : True seulement si c'est son propre bien
        - Viewer : toujours False
        """
        if self.is_admin():
            return True
        if self.is_manager():
            return True
        if self.role == 'user' and resource_owner_id == self.id:
            return True
        return False
    
    def can_view(self, resource_owner_id=None):
        """
        Vérifie si l'utilisateur peut voir une ressource
        - Viewer, User, Manager, Admin : toujours True
        """
        return self.role in ['admin', 'manager', 'user', 'viewer']