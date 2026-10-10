from marshmallow import Schema, fields, validate


# ============================================================
# SCHÉMA DE VALIDATION — pour l'ajout d'un enfant (/api/enfants)
# ============================================================
class EnfantSchema(Schema):
    prenom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    nom = fields.String(required=True, validate=validate.Length(min=1, max=100))
    # Format attendu : "AAAA-MM-JJ" (ex. "2015-04-23") — optionnel
    date_naissance = fields.Date(required=False, allow_none=True)
