import uuid
import enum
from datetime import datetime, timezone

from settings import db


def generate_uuid():
    return str(uuid.uuid4())


class RoleUtilisateur(enum.Enum):
    parent = 'parent'
    admin_equipe = 'admin_equipe'
    admin_plateforme = 'admin_plateforme'


class RoleMembreEquipe(enum.Enum):
    parent = 'parent'
    coach = 'coach'
    admin = 'admin'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.Enum(RoleUtilisateur), default=RoleUtilisateur.parent, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.id} {self.email} {self.role}'


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(255), nullable=False)
    sport = db.Column(db.String(50), nullable=False)
    league_id = db.Column(db.String(36), nullable=True)
    saison = db.Column(db.String(20), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'{self.id} {self.nom} {self.sport}'


class TeamMember(db.Model):
    __tablename__ = 'team_members'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False)
    role = db.Column(db.Enum(RoleMembreEquipe), default=RoleMembreEquipe.parent, nullable=False)

    def __repr__(self):
        return f'{self.id} {self.user_id} {self.team_id} {self.role}'


# ============================================================
# ENFANT (joueur) — appartient à un parent (users.id)
# Un parent peut avoir plusieurs enfants.
# ============================================================
class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    parent_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    prenom = db.Column(db.String(100), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.id} {self.prenom} {self.nom}'


# ============================================================
# INSCRIPTION d'un enfant à une équipe (relation plusieurs-à-plusieurs)
# Un enfant peut être inscrit à plusieurs équipes,
# mais une seule fois à la même équipe (contrainte unique).
# ============================================================
class PlayerTeam(db.Model):
    __tablename__ = 'player_teams'
    __table_args__ = (
        db.UniqueConstraint('player_id', 'team_id', name='uq_player_team'),
    )
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    player_id = db.Column(db.String(36), db.ForeignKey('players.id'), nullable=False, index=True)
    team_id = db.Column(db.String(36), db.ForeignKey('teams.id'), nullable=False, index=True)
    date_inscription = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'{self.id} {self.player_id} {self.team_id}'