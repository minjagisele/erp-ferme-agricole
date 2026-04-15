from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Décorateur pour vérifier que l'utilisateur a un des rôles requis
    Utilisation: @role_required('admin', 'manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Veuillez vous connecter', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('Accès non autorisé. Vous n\'avez pas les droits nécessaires.', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def owner_or_admin(resource_getter):
    """
    Décorateur pour vérifier que l'utilisateur est le propriétaire ou admin
    Utilisation: @owner_or_admin(lambda id: Parcelle.query.get(id))
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Veuillez vous connecter', 'warning')
                return redirect(url_for('auth.login'))
            
            # Extraire l'ID des kwargs (suppose que l'id est dans les paramètres)
            resource_id = kwargs.get('id') or kwargs.get('resource_id')
            if resource_id:
                resource = resource_getter(resource_id)
                if resource and hasattr(resource, 'user_id'):
                    if current_user.is_admin() or resource.user_id == current_user.id:
                        return f(*args, **kwargs)
            
            flash('Vous n\'êtes pas autorisé à modifier cette ressource', 'danger')
            return redirect(url_for('main.dashboard'))
        return decorated_function
    return decorator