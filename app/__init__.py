from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page'
    
    Migrate(app, db)
    
    # Import des modèles
    from app.models.user import User
    from app.models.parcelle import Parcelle, Equipement
    
    with app.app_context():
        db.create_all()
    
    # Import des routes
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.parcelles import parcelles_bp
    from app.routes.stocks import stock_bp
    from app.routes.production import production_bp
    from app.routes.recolte import recolte_bp
    from app.routes.ventes import vente_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(parcelles_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(recolte_bp)
    app.register_blueprint(vente_bp)
    
    return app