from marshmallow import Schema, fields, validate


# ============================================================
# SCHÉMA DE VALIDATION — pour la création d'une équipe (/api/teams)
# ============================================================
class TeamSchema(Schema):
    nom = fields.String(required=True, validate=validate.Length(min=1, max=255))
    sport = fields.String(required=True, validate=validate.Length(min=1, max=50))
    # une équipe peut être créée sans préciser la saison
    saison = fields.String(required=False, allow_none=True)
