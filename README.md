# 🏆 Plateforme Tournois Sportifs — API REST (Flask)

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![JWT](https://img.shields.io/badge/Auth-JWT-orange)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

API REST qui aide les parents d'enfants en sport compétitif (hockey, soccer, natation) à coordonner la logistique des tournois : équipes, joueurs, et à terme horaires, covoiturage et hôtels.
Le service est consommé par un **client Android (Java)** et un **client Web**.

> Projet de session combiné **420-A15 (services web, Python)** et **420-A17 (Android)** — Collège de Bois-de-Boulogne, AEC Analyste-programmeur, 2026.
> Réalisé en équipe de 3. **Ma contribution : le service backend (authentification JWT, gestion des équipes et des joueurs, Swagger, Docker).**

---

## ✨ Fonctionnalités

- Inscription et connexion avec **jeton JWT** (mots de passe hachés avec Werkzeug)
- Rôles sur la plateforme (parent, admin d'équipe, admin de plateforme) et dans l'équipe (parent, coach, admin)
- **CRUD des équipes** : créer, consulter, modifier, supprimer
- Gestion des **joueurs (enfants)** et de leur rattachement aux équipes
- Validation des données entrantes avec **marshmallow**
- Documentation interactive de l'API avec **Swagger** (`/apidocs`)
- Client Python de démonstration (`client_tournois.py`)

## 🛠️ Technologies

| Couche | Outils |
|---|---|
| Langage | Python 3 |
| Framework web | Flask 3, flasgger (Swagger) |
| Persistance | SQLAlchemy 2 (ORM), SQLite, identifiants UUID |
| Sécurité | PyJWT, werkzeug.security, variables d'environnement (.env) |
| Validation | marshmallow |
| Déploiement | Docker |
| Tests | Postman |

## 📁 Structure

```
tournois-sportifs-api/
├── app.py              # Routes de l'API (auth, équipes, joueurs)
├── settings.py         # Création de l'app Flask, BD et config Swagger
├── config.py           # Lecture des variables d'environnement
├── modele/
│   └── mod_classes.py  # Modèles SQLAlchemy : User, Team, TeamMember, Player, PlayerTeam
├── schemas/            # Schémas de validation marshmallow
├── creer_admin.py      # Script de création d'un compte administrateur
├── client_tournois.py  # Client de démonstration (requests)
├── Dockerfile
├── requirements.txt
└── .env.example        # Modèle du fichier .env (à copier)
```

## 🔌 Points d'accès principaux

| Méthode | Route | Description | Jeton requis |
|---|---|---|---|
| POST | `/signup` | Créer un compte | Non |
| POST | `/login` | Se connecter, retourne un JWT | Non |
| POST | `/api/teams` | Créer une équipe | Oui |
| GET | `/api/teams` | Lister mes équipes | Oui |
| PUT | `/api/teams/<team_id>` | Modifier une équipe | Oui |
| DELETE | `/api/teams/<team_id>` | Supprimer une équipe | Oui |
| GET | `/api/teams/<team_id>/joueurs` | Joueurs d'une équipe | Oui |
| POST | `/api/enfants` | Ajouter un enfant (joueur) | Oui |
| GET | `/api/enfants` | Lister mes enfants | Oui |
| POST | `/api/enfants/<enfant_id>/equipes/<team_id>` | Inscrire un enfant dans une équipe | Oui |

En-tête à envoyer pour les routes protégées : `Authorization: Bearer <votre_token>`

## 🚀 Installation et exécution

### Option 1 — en local

```bash
git clone https://github.com/hanen91-ch/tournois-sportifs-api.git
cd tournois-sportifs-api
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env      # (cp sous macOS/Linux) puis définir SECRET_KEY
python app.py
```

L'API démarre sur http://127.0.0.1:5000 et la documentation Swagger sur http://127.0.0.1:5000/apidocs

### Option 2 — avec Docker

```bash
docker build -t tournois-api .
docker run -p 5000:5000 --env-file .env tournois-api
```

## 👩‍💻 Auteure

**Hanen Chtourou** — Analyste-programmeure
[LinkedIn](https://linkedin.com/in/hanen-chtourou-45097a104) · [GitHub](https://github.com/hanen91-ch)
