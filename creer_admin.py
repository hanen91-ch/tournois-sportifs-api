"""
Création (ou promotion) d'un compte ADMIN d'équipes.

L'inscription publique (/signup) crée toujours un compte parent.
Les admins sont créés ici, côté serveur, par l'équipe de développement.

Utilisation (terminal PyCharm, .venv actif) :
    python creer_admin.py <courriel> <mot_de_passe> <nom> <prenom>

Si le courriel existe déjà, le compte est simplement promu admin
(son mot de passe n'est pas modifié).
"""
import sys

from werkzeug.security import generate_password_hash

from settings import app, db
from modele.mod_classes import User, RoleUtilisateur


def main():
    if len(sys.argv) != 5:
        print("Usage : python creer_admin.py <courriel> <mot_de_passe> <nom> <prenom>")
        sys.exit(1)

    email, mot_de_passe, nom, prenom = sys.argv[1:5]

    with app.app_context():
        db.create_all()

        user = User.query.filter_by(email=email).first()
        if user:
            user.role = RoleUtilisateur.admin_equipe
            db.session.commit()
            print(f"Compte existant promu admin : {email}")
            return

        if len(mot_de_passe) < 6:
            print("Le mot de passe doit contenir au moins 6 caractères.")
            sys.exit(1)

        user = User(email=email,
                    password_hash=generate_password_hash(mot_de_passe),
                    nom=nom,
                    prenom=prenom,
                    role=RoleUtilisateur.admin_equipe)
        db.session.add(user)
        db.session.commit()
        print(f"Admin créé : {email}")


if __name__ == '__main__':
    main()
