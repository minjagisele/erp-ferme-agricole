# ERP Ferme Agricole

Un système complet de gestion d'entreprise (ERP) pour les fermes agricoles, développé avec Flask et SQLAlchemy.

## Description du Projet

Ce système ERP permet aux agriculteurs de gérer efficacement tous les aspects de leur exploitation agricole :

### Fonctionnalités Principales

#### 🏠 **Tableau de Bord**
- KPIs en temps réel (parcelles, superficies, stocks, ventes)
- Graphiques interactifs (ventes par mois, opérations, récoltes)
- Alertes et notifications (ruptures de stock, opérations en retard)
- Activités récentes et prévisions

#### 👥 **Gestion des Utilisateurs**
- Système d'authentification complet
- Rôles utilisateur (admin, manager, viewer)
- Gestion des profils et mots de passe
- Inscription publique avec validation

#### 🌾 **Gestion des Parcelles**
- Catalogue des parcelles avec superficies et types de sol
- Équipements associés
- Suivi des opérations culturales

#### 📦 **Gestion des Stocks**
- Intrants et produits phytosanitaires
- Lots avec traçabilité (dates de péremption)
- Dépôts et mouvements de stock
- Alertes de rupture et péremption

#### 🚜 **Gestion de la Production**
- Campagnes agricoles
- Opérations culturales (labour, semis, traitement, récolte)
- Suivi des coûts et ressources utilisées
- Employés et équipements affectés

#### 🌽 **Gestion des Récoltes**
- Suivi des récoltes par parcelle
- Qualité et calibre
- Stockage et traçabilité
- Intégration avec les ventes

#### 💰 **Gestion Commerciale**
- Clients et devis
- Commandes et factures
- Suivi des paiements
- Chiffre d'affaires et créances

## Architecture Technique

### Backend
- **Framework**: Flask 2.x
- **Base de données**: SQLAlchemy avec SQLite
- **Authentification**: Flask-Login
- **Migrations**: Flask-Migrate (optionnel)

### Frontend
- **Templates**: Jinja2
- **CSS Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **Graphiques**: Chart.js (intégration préparée)

### Structure du Projet
```
erp-agricole-complet/
├── app/
│   ├── __init__.py          # Configuration Flask
│   ├── models/              # Modèles de données
│   ├── routes/              # Routes et contrôleurs
│   ├── templates/           # Templates HTML
│   ├── static/              # Assets statiques
│   └── utils/               # Utilitaires
├── config.py                # Configuration
├── run.py                   # Point d'entrée
└── requirements.txt         # Dépendances Python
```

## Installation et Configuration

### Prérequis
- Python 3.8+
- pip
- Virtualenv (recommandé)

### Installation
```bash
# Cloner le repository
git clone <repository-url>
cd erp-agricole-complet

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base de données
python run.py  # Les tables sont créées automatiquement
```

### Configuration
Modifier `config.py` pour :
- Changer la clé secrète
- Configurer la base de données
- Paramètres d'environnement

## Utilisation

### Démarrage
```bash
python run.py
```
L'application sera accessible sur `http://127.0.0.1:5000/`

### Comptes par Défaut
- **Admin**: Créer un compte via l'inscription, puis modifier le rôle en base
- **Utilisateur standard**: S'inscrire via le formulaire d'inscription

## État du Projet

### ✅ Fonctionnalités Implémentées
- Système d'authentification complet
- Dashboard avec KPIs et graphiques
- Gestion complète des parcelles et équipements
- Système de stock avec alertes
- Gestion des campagnes et opérations
- Suivi des récoltes et ventes
- Interface responsive avec Bootstrap

### 🔧 Corrections Récentes
- Résolution des conflits SQLAlchemy (backrefs)
- Correction des requêtes SQL complexes
- Ajout des champs manquants (created_at)
- Routes manquantes (gestion utilisateurs)
- Templates et context variables

### 🚧 Améliorations Possibles
- Migration vers PostgreSQL pour la production
- API REST pour intégrations externes
- Notifications par email
- Export de rapports PDF/Excel
- Application mobile
- Synchronisation cloud

## Technologies Utilisées

- **Python 3.8+**
- **Flask 2.x** - Framework web
- **SQLAlchemy** - ORM
- **Flask-Login** - Authentification
- **Bootstrap 5** - UI Framework
- **Chart.js** - Graphiques
- **SQLite** - Base de données (développement)

## Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.

## Support

Pour le support, ouvrir une issue sur GitHub ou contacter l'équipe de développement.

---

**Note**: Ce système est conçu pour les petites à moyennes exploitations agricoles. Pour les grandes structures, une adaptation peut être nécessaire.</content>
