from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Ce compte est désactivé. Contactez l\'administrateur.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Mettre à jour la date de dernière connexion
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=remember)
        flash(f'Bienvenue {user.username} !', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.dashboard'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Inscription d'un nouvel utilisateur (accessible à tous)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validations
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé', 'danger')
            return redirect(url_for('auth.register'))
        
        # Créer le nouvel utilisateur (rôle 'viewer' par défaut)
        new_user = User(username=username, email=email, role='viewer')
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Inscription réussie ! Vous pouvez maintenant vous connecter', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """Page de profil utilisateur"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Changer son mot de passe"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Mot de passe actuel incorrect', 'danger')
            return redirect(url_for('auth.change_password'))
        
        if new_password != confirm_password:
            flash('Les nouveaux mots de passe ne correspondent pas', 'danger')
            return redirect(url_for('auth.change_password'))
        
        if len(new_password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Mot de passe modifié avec succès', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')