from marshmallow import Schema, fields, validate


# ============================================================
# SCHÉMA DE VALIDATION — pour l'inscription (/signup)
# Ne concerne QUE la validation des données reçues du client ;
# ce schéma ne touche jamais la base de données.
# ============================================================
class UserSchema(Schema):
    # fields.Email vérifie que la valeur est un email au bon format
    # (pas juste une chaîne de caractères quelconque)
    email = fields.Email(required=True)

    # Le mot de passe doit être présent, et faire au moins 6 caractères
    password = fields.String(required=True, validate=validate.Length(min=6))

    nom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    prenom = fields.String(required=True, validate=validate.Length(min=1, max=100))

    # Champ optionnel : required=False, et allow_none=True permet d'envoyer null
    telephone = fields.String(required=False, allow_none=True)
