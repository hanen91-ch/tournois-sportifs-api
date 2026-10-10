import functools
import jwt
from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from flasgger import Swagger
from werkzeug.security import generate_password_hash, check_password_hash

from settings import app, db
from modele.mod_classes import (User, Team, TeamMember, Player, PlayerTeam,
                                RoleUtilisateur, RoleMembreEquipe)
from schemas.user_schema import UserSchema
from schemas.team_schema import TeamSchema
from schemas.enfant_schema import EnfantSchema


# Rôles autorisés à GÉRER des équipes (créer, modifier, supprimer)
ROLES_ADMIN = (RoleUtilisateur.admin_equipe, RoleUtilisateur.admin_plateforme)


# ============================================================
# ROUTE RACINE — juste pour vérifier que le service est en ligne
# ============================================================
@app.route('/')
def index():
    return jsonify({'message': 'Bienvenue sur la plateforme de tournois sportifs'})


# ============================================================
# DÉCORATEUR D'AUTHENTIFICATION (qui es-tu ?)
# Ce décorateur s'ajoute au-dessus de toute route qu'on veut
# protéger. Il vérifie que la requête contient un token JWT
# valide avant de laisser passer l'utilisateur.
# ============================================================
def token_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 1. On cherche l'en-tête "Authorization" dans la requête HTTP
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']

            # 2. Le format attendu est "Bearer <token>" — on vérifie ce préfixe
            if auth_header.startswith("Bearer "):
                header_parts = auth_header.split(" ")

                # 3. On s'assure d'avoir bien 2 morceaux : ["Bearer", "<le_token>"]
                if len(header_parts) == 2:
                    # 4. On extrait le token et on retire des guillemets parasites, si présents
                    token = header_parts[1].strip('"')

        # 5. Si aucun token n'a été trouvé, on refuse l'accès (401 = non autorisé)
        if not token:
            return jsonify({
                "message": "Le jeton (token) est manquant ou mal configuré ! Format attendu : Bearer <votre_token>"
            }), 401

        try:
            # 6. On décode le token avec notre clé secrète (définie dans config.py / .env)
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])

            # 7. On stocke l'id de l'utilisateur connecté dans "request.current_user"
            request.current_user = data['sub']

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Le jeton a expiré !"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Le jeton est invalide !"}), 401

        # 8. Le token est valide : on exécute la vraie fonction de la route
        return f(*args, **kwargs)

    return decorated


# ============================================================
# DÉCORATEUR D'AUTORISATION (as-tu le droit ?)
# S'utilise SOUS @token_required. Relit le rôle de l'usager
# DANS LA BASE (pas dans le token) : un changement de rôle
# s'applique donc immédiatement.
#   401 = on ne sait pas qui tu es (token absent/invalide)
#   403 = on sait qui tu es, mais tu n'as pas le droit
# ============================================================
def role_requis(*roles):
    def decorateur(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user = db.session.get(User, request.current_user)
            if user is None:
                return jsonify({'message': 'Utilisateur introuvable'}), 401
            if user.role not in roles:
                return jsonify({'message': 'Action non autorisée pour votre rôle'}), 403
            request.current_user_obj = user
            return f(*args, **kwargs)
        return decorated
    return decorateur


def est_gestionnaire(user, team_id):
    '''Vrai si l'usager gère cette équipe (créateur = TeamMember admin)
    ou s'il est admin de la plateforme (gère toutes les équipes).'''
    if user.role == RoleUtilisateur.admin_plateforme:
        return True
    lien = TeamMember.query.filter_by(user_id=user.id, team_id=team_id,
                                      role=RoleMembreEquipe.admin).first()
    return lien is not None


def team_en_dict(team):
    return {'id': team.id, 'nom': team.nom, 'sport': team.sport, 'saison': team.saison}


def enfant_en_dict(enfant):
    return {
        'id': enfant.id,
        'prenom': enfant.prenom,
        'nom': enfant.nom,
        'date_naissance': enfant.date_naissance.isoformat() if enfant.date_naissance else None
    }


def enfant_du_parent(enfant_id):
    '''Retourne l'enfant s'il appartient au parent connecté, sinon None.
    Empêche un parent de lire ou d'inscrire l'enfant d'un autre parent.'''
    enfant = db.session.get(Player, enfant_id)
    if enfant is None or enfant.parent_id != request.current_user:
        return None
    return enfant


# ============================================================
# INSCRIPTION — création d'un nouveau compte utilisateur
# Toute inscription crée un compte PARENT.
# Les comptes admin sont créés par le script creer_admin.py.
# ============================================================
@app.route('/signup', methods=['POST'])
def signup():
    '''Inscription d'un nouvel utilisateur (rôle parent)
        ---
        tags: [Authentification]
        parameters:
          - in: body
            name: user
            required: true
            schema:
              type: object
              properties:
                email:
                  type: string
                  example: hanen@test.com
                password:
                  type: string
                  example: abcdef
                nom:
                  type: string
                  example: Chtourou
                prenom:
                  type: string
                  example: Hanen
        responses:
          201:
            description: Compte créé avec succès
          400:
            description: Données invalides ou email déjà existant
        '''
    data = request.get_json(silent=True) or {}

    # Validation des données reçues avec marshmallow (voir schemas/user_schema.py)
    schema = UserSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({'error': 'Data invalide', 'details': errors}), 400

    # On vérifie qu'aucun compte n'existe déjà avec cet email
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Cet email existe déjà'}), 400

    # IMPORTANT : on ne stocke jamais le mot de passe en clair.
    # generate_password_hash() le transforme en empreinte irréversible.
    password_hash = generate_password_hash(data['password'])

    user = User(
        email=data['email'],
        password_hash=password_hash,
        nom=data['nom'],
        prenom=data['prenom'],
        telephone=data.get('telephone'),  # optionnel — .get() évite une erreur si absent
        role=RoleUtilisateur.parent       # jamais admin par l'inscription publique
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Bienvenue sur notre service', 'id': user.id}), 201


# ============================================================
# CONNEXION — vérifie les identifiants et retourne un token JWT
# ============================================================
@app.route('/login', methods=['POST'])
def login():
    '''Connexion — retourne un token JWT, le prénom et le rôle
        ---
        tags: [Authentification]
        parameters:
          - in: body
            name: credentials
            required: true
            schema:
              type: object
              properties:
                email:
                  type: string
                  example: hanen@test.com
                password:
                  type: string
                  example: abcdef
        responses:
          200:
            description: Connexion réussie (token, prenom, role)
          401:
            description: Identifiants invalides
        '''
    auth_data = request.get_json(silent=True)

    # On vérifie que les deux champs nécessaires sont bien présents
    if not auth_data or 'email' not in auth_data or 'password' not in auth_data:
        return jsonify({'message': 'Email ou mot de passe manquant'}), 400

    email = auth_data['email']
    password = auth_data['password']

    # On cherche l'utilisateur correspondant à cet email dans la base
    user = User.query.filter_by(email=email).first()

    # check_password_hash compare le mot de passe fourni avec le hash stocké,
    # sans jamais avoir besoin de "déhacher" — c'est une comparaison à sens unique
    if user and check_password_hash(user.password_hash, password):
        # Le token expirera dans 30 minutes
        expiration = datetime.now(timezone.utc) + timedelta(minutes=30)

        # "sub" (subject) = l'identité que le token représente — ici, l'id de l'utilisateur
        payload = {
            'sub': user.id,
            'exp': expiration
        }
        # On signe le token avec notre clé secrète — c'est ce qui empêche
        # quelqu'un de fabriquer un faux token
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

        # Le rôle sert à l'app pour choisir le bon menu (admin ou parent).
        # La SÉCURITÉ, elle, est assurée côté serveur par @role_requis.
        return jsonify({'token': token, 'prenom': user.prenom,
                        'role': user.role.value}), 200

    # Email inconnu OU mot de passe incorrect — même message pour les deux
    return jsonify({'message': 'Informations de connexion invalide'}), 401


# ============================================================
# ===================  ÉQUIPES — ADMIN  =======================
# ============================================================

# ------------------------------------------------------------
# CRÉER UNE ÉQUIPE — admin seulement
# ------------------------------------------------------------
@app.route('/api/teams', methods=['POST'])
@token_required
@role_requis(*ROLES_ADMIN)
def creer_team():
    '''Créer une nouvelle équipe (admin)
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        parameters:
          - in: body
            name: team
            required: true
            schema:
              type: object
              properties:
                nom:
                  type: string
                  example: Les Faucons
                sport:
                  type: string
                  example: hockey
                saison:
                  type: string
                  example: "2026-2027"
        responses:
          201:
            description: Équipe créée avec succès
          400:
            description: Données invalides
          401:
            description: Token manquant ou invalide
          403:
            description: Réservé aux admins
        '''
    data = request.get_json(silent=True) or {}

    schema = TeamSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({'error': 'Data invalide', 'details': errors}), 400

    # On crée l'équipe
    team = Team(nom=data['nom'], sport=data['sport'], saison=data.get('saison'))
    db.session.add(team)
    db.session.commit()

    # Le créateur devient gestionnaire (admin) de cette équipe
    lien = TeamMember(user_id=request.current_user, team_id=team.id,
                      role=RoleMembreEquipe.admin)
    db.session.add(lien)
    db.session.commit()

    return jsonify(team_en_dict(team)), 201


# ------------------------------------------------------------
# MES ÉQUIPES — les équipes que l'admin connecté gère
# ------------------------------------------------------------
@app.route('/api/teams', methods=['GET'])
@token_required
@role_requis(*ROLES_ADMIN)
def get_my_teams():
    '''Équipes gérées par l'admin connecté
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        responses:
          200:
            description: Liste des équipes gérées
          401:
            description: Token manquant ou invalide
          403:
            description: Réservé aux admins
        '''
    user = request.current_user_obj

    if user.role == RoleUtilisateur.admin_plateforme:
        teams = Team.query.order_by(Team.nom).all()
    else:
        liens = TeamMember.query.filter_by(user_id=user.id, role=RoleMembreEquipe.admin).all()
        team_ids = [l.team_id for l in liens]
        teams = Team.query.filter(Team.id.in_(team_ids)).order_by(Team.nom).all() if team_ids else []

    listing = []
    for team in teams:
        d = team_en_dict(team)
        d['nb_inscrits'] = PlayerTeam.query.filter_by(team_id=team.id).count()
        listing.append(d)

    return jsonify({'teams': listing}), 200


# ------------------------------------------------------------
# MODIFIER UNE ÉQUIPE — admin qui gère cette équipe
# ------------------------------------------------------------
@app.route('/api/teams/<string:team_id>', methods=['PUT'])
@token_required
@role_requis(*ROLES_ADMIN)
def modifier_team(team_id):
    '''Modifier une équipe (admin gestionnaire)
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        parameters:
          - name: team_id
            in: path
            type: string
            required: true
          - in: body
            name: team
            required: true
            schema:
              type: object
              properties:
                nom:
                  type: string
                  example: Les Faucons U12
                sport:
                  type: string
                  example: hockey
                saison:
                  type: string
                  example: "2026-2027"
        responses:
          200:
            description: Équipe modifiée
          400:
            description: Données invalides
          403:
            description: Vous ne gérez pas cette équipe
          404:
            description: Équipe introuvable
        '''
    team = db.get_or_404(Team, team_id)

    if not est_gestionnaire(request.current_user_obj, team_id):
        return jsonify({'message': 'Vous ne gérez pas cette équipe'}), 403

    data = request.get_json(silent=True) or {}

    # partial=True : on peut n'envoyer que les champs à modifier
    errors = TeamSchema().validate(data, partial=True)
    if errors:
        return jsonify({'error': 'Data invalide', 'details': errors}), 400

    if 'nom' in data:
        team.nom = data['nom']
    if 'sport' in data:
        team.sport = data['sport']
    if 'saison' in data:
        team.saison = data['saison']
    db.session.commit()

    return jsonify(team_en_dict(team)), 200


# ------------------------------------------------------------
# SUPPRIMER UNE ÉQUIPE — admin qui gère cette équipe
# Supprime aussi les inscriptions d'enfants et les liens membres.
# ------------------------------------------------------------
@app.route('/api/teams/<string:team_id>', methods=['DELETE'])
@token_required
@role_requis(*ROLES_ADMIN)
def supprimer_team(team_id):
    '''Supprimer une équipe (admin gestionnaire)
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        parameters:
          - name: team_id
            in: path
            type: string
            required: true
        responses:
          200:
            description: Équipe supprimée
          403:
            description: Vous ne gérez pas cette équipe
          404:
            description: Équipe introuvable
        '''
    team = db.get_or_404(Team, team_id)

    if not est_gestionnaire(request.current_user_obj, team_id):
        return jsonify({'message': 'Vous ne gérez pas cette équipe'}), 403

    nom = team.nom
    # On supprime d'abord les lignes qui dépendent de l'équipe (clés étrangères)
    PlayerTeam.query.filter_by(team_id=team_id).delete()
    TeamMember.query.filter_by(team_id=team_id).delete()
    db.session.delete(team)
    db.session.commit()

    return jsonify({'message': f"L'équipe {nom} a été supprimée"}), 200


# ------------------------------------------------------------
# JOUEURS INSCRITS À UNE ÉQUIPE — admin qui gère cette équipe
# ------------------------------------------------------------
@app.route('/api/teams/<string:team_id>/joueurs', methods=['GET'])
@token_required
@role_requis(*ROLES_ADMIN)
def joueurs_team(team_id):
    '''Liste des joueurs (enfants) inscrits à une équipe (admin gestionnaire)
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        parameters:
          - name: team_id
            in: path
            type: string
            required: true
        responses:
          200:
            description: Liste des joueurs inscrits, avec leur parent
          403:
            description: Vous ne gérez pas cette équipe
          404:
            description: Équipe introuvable
        '''
    team = db.get_or_404(Team, team_id)

    if not est_gestionnaire(request.current_user_obj, team_id):
        return jsonify({'message': 'Vous ne gérez pas cette équipe'}), 403

    joueurs = []
    for inscription in PlayerTeam.query.filter_by(team_id=team.id).all():
        enfant = db.session.get(Player, inscription.player_id)
        if enfant is None:
            continue
        parent = db.session.get(User, enfant.parent_id)
        d = enfant_en_dict(enfant)
        d['parent'] = f'{parent.prenom} {parent.nom}' if parent else ''
        d['parent_email'] = parent.email if parent else ''
        joueurs.append(d)

    joueurs.sort(key=lambda j: (j['prenom'].lower(), j['nom'].lower()))
    return jsonify({'team': team_en_dict(team), 'joueurs': joueurs}), 200


# ------------------------------------------------------------
# RETIRER UN JOUEUR D'UNE ÉQUIPE (supprimer l'inscription)
# admin qui gère cette équipe — l'enfant lui-même n'est pas supprimé
# ------------------------------------------------------------
@app.route('/api/teams/<string:team_id>/joueurs/<string:enfant_id>', methods=['DELETE'])
@token_required
@role_requis(*ROLES_ADMIN)
def retirer_joueur(team_id, enfant_id):
    '''Supprimer l'inscription d'un joueur à une équipe (admin gestionnaire)
        ---
        tags: [Équipes - admin]
        security:
          - Bearer: []
        parameters:
          - name: team_id
            in: path
            type: string
            required: true
          - name: enfant_id
            in: path
            type: string
            required: true
        responses:
          200:
            description: Inscription supprimée
          403:
            description: Vous ne gérez pas cette équipe
          404:
            description: Équipe ou inscription introuvable
        '''
    team = db.get_or_404(Team, team_id)

    if not est_gestionnaire(request.current_user_obj, team_id):
        return jsonify({'message': 'Vous ne gérez pas cette équipe'}), 403

    inscription = PlayerTeam.query.filter_by(team_id=team.id, player_id=enfant_id).first()
    if inscription is None:
        return jsonify({'message': "Ce joueur n'est pas inscrit à cette équipe"}), 404

    enfant = db.session.get(Player, enfant_id)
    prenom = enfant.prenom if enfant else 'Le joueur'
    db.session.delete(inscription)
    db.session.commit()

    return jsonify({'message': f'{prenom} a été retiré(e) de {team.nom}'}), 200


# ============================================================
# ===============  ÉQUIPES — TOUS LES RÔLES  ==================
# ============================================================

@app.route('/api/teams/all', methods=['GET'])
@token_required
def get_all_teams():
    '''Lister toutes les équipes (tout usager connecté)
        ---
        tags: [Équipes - consultation]
        security:
          - Bearer: []
        parameters:
          - name: enfant_id
            in: query
            type: string
            required: false
            description: Si fourni (parent), ajoute deja_inscrit pour cet enfant
        responses:
          200:
            description: Liste de toutes les équipes
          401:
            description: Token manquant ou invalide
        '''
    # Option : marquer les équipes où l'enfant est déjà inscrit
    ids_inscrits = set()
    enfant_id = request.args.get('enfant_id')
    if enfant_id:
        enfant = enfant_du_parent(enfant_id)
        if enfant is None:
            return jsonify({'message': 'Enfant introuvable'}), 404
        ids_inscrits = {i.team_id for i in PlayerTeam.query.filter_by(player_id=enfant.id).all()}

    listing = []
    for team in Team.query.order_by(Team.nom).all():
        d = team_en_dict(team)
        d['deja_inscrit'] = team.id in ids_inscrits
        listing.append(d)

    return jsonify({'teams': listing}), 200


# ============================================================
# ===================  ENFANTS — PARENT  ======================
# ============================================================

# ------------------------------------------------------------
# AJOUTER UN ENFANT
# ------------------------------------------------------------
@app.route('/api/enfants', methods=['POST'])
@token_required
@role_requis(RoleUtilisateur.parent)
def ajouter_enfant():
    '''Ajouter un enfant (parent)
        ---
        tags: [Enfants - parent]
        security:
          - Bearer: []
        parameters:
          - in: body
            name: enfant
            required: true
            schema:
              type: object
              properties:
                prenom:
                  type: string
                  example: Adam
                nom:
                  type: string
                  example: Bahrini
                date_naissance:
                  type: string
                  example: "2015-04-23"
        responses:
          201:
            description: Enfant ajouté
          400:
            description: Données invalides
          403:
            description: Réservé aux parents
        '''
    data = request.get_json(silent=True) or {}

    schema = EnfantSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({'error': 'Data invalide', 'details': errors}), 400

    # load() convertit "2015-04-23" en objet date Python
    valeurs = schema.load(data)

    enfant = Player(parent_id=request.current_user,
                    prenom=valeurs['prenom'],
                    nom=valeurs['nom'],
                    date_naissance=valeurs.get('date_naissance'))
    db.session.add(enfant)
    db.session.commit()

    return jsonify(enfant_en_dict(enfant)), 201


# ------------------------------------------------------------
# MES ENFANTS
# ------------------------------------------------------------
@app.route('/api/enfants', methods=['GET'])
@token_required
@role_requis(RoleUtilisateur.parent)
def lister_enfants():
    '''Lister mes enfants (parent)
        ---
        tags: [Enfants - parent]
        security:
          - Bearer: []
        responses:
          200:
            description: Liste des enfants du parent connecté
          403:
            description: Réservé aux parents
        '''
    enfants = Player.query.filter_by(parent_id=request.current_user).order_by(Player.prenom).all()
    return jsonify({'enfants': [enfant_en_dict(e) for e in enfants]}), 200


# ------------------------------------------------------------
# ÉQUIPES D'UN ENFANT
# ------------------------------------------------------------
@app.route('/api/enfants/<string:enfant_id>/equipes', methods=['GET'])
@token_required
@role_requis(RoleUtilisateur.parent)
def equipes_enfant(enfant_id):
    '''Équipes auxquelles un enfant est inscrit (parent)
        ---
        tags: [Enfants - parent]
        security:
          - Bearer: []
        parameters:
          - name: enfant_id
            in: path
            type: string
            required: true
        responses:
          200:
            description: Liste des équipes de l'enfant
          404:
            description: Enfant introuvable (ou pas à vous)
        '''
    enfant = enfant_du_parent(enfant_id)
    if enfant is None:
        return jsonify({'message': 'Enfant introuvable'}), 404

    inscriptions = PlayerTeam.query.filter_by(player_id=enfant.id).all()
    team_ids = [i.team_id for i in inscriptions]
    teams = Team.query.filter(Team.id.in_(team_ids)).order_by(Team.nom).all() if team_ids else []

    return jsonify({'enfant': enfant_en_dict(enfant),
                    'teams': [team_en_dict(t) for t in teams]}), 200


# ------------------------------------------------------------
# INSCRIRE UN ENFANT À UNE ÉQUIPE
# ------------------------------------------------------------
@app.route('/api/enfants/<string:enfant_id>/equipes/<string:team_id>', methods=['POST'])
@token_required
@role_requis(RoleUtilisateur.parent)
def inscrire_enfant(enfant_id, team_id):
    '''Inscrire un enfant à une équipe (parent)
        ---
        tags: [Enfants - parent]
        security:
          - Bearer: []
        parameters:
          - name: enfant_id
            in: path
            type: string
            required: true
          - name: team_id
            in: path
            type: string
            required: true
        responses:
          201:
            description: Inscription réussie
          400:
            description: Déjà inscrit à cette équipe
          404:
            description: Enfant ou équipe introuvable
        '''
    enfant = enfant_du_parent(enfant_id)
    if enfant is None:
        return jsonify({'message': 'Enfant introuvable'}), 404

    team = db.session.get(Team, team_id)
    if team is None:
        return jsonify({'message': 'Équipe introuvable'}), 404

    if PlayerTeam.query.filter_by(player_id=enfant.id, team_id=team.id).first():
        return jsonify({'message': f'{enfant.prenom} est déjà inscrit(e) à {team.nom}'}), 400

    db.session.add(PlayerTeam(player_id=enfant.id, team_id=team.id))
    db.session.commit()

    return jsonify({'message': f'{enfant.prenom} est inscrit(e) à {team.nom}'}), 201


# ============================================================
# DÉMARRAGE DU SERVEUR
# ============================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()   # crée les nouvelles tables (players, player_teams) si absentes
    swagger = Swagger(app)
    app.run(host='0.0.0.0', port=5000, debug=True)
