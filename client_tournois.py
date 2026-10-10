"""
Client Python de l'API « Plateforme de tournois sportifs » (420-A15-BB).

Livrable de l'énoncé : un client qui utilise la bibliothèque `requests`
pour tester toutes les opérations de l'API, avec gestion des erreurs.

Utilisation (le serveur app.py doit être lancé) :
    python client_tournois.py                 -> menu interactif
    python client_tournois.py --demo admin@test.com abcdef parent@test.com abcdef
                                              -> scénario complet automatique

Adresse du serveur : variable d'environnement API_URL
(par défaut http://127.0.0.1:5000).
"""
import os
import sys

import requests

URL_PAR_DEFAUT = os.getenv("API_URL", "http://127.0.0.1:5000")
DELAI_SECONDES = 10


class ErreurApi(Exception):
    """Erreur renvoyée par l'API (code HTTP 4xx/5xx) ou serveur injoignable."""

    def __init__(self, code, message):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class ClientTournois:
    """Enveloppe chaque route de l'API dans une méthode Python."""

    def __init__(self, url_base=URL_PAR_DEFAUT):
        self.url_base = url_base.rstrip("/")
        self.token = None
        self.prenom = None
        self.role = None

    # --------------------------------------------------------
    # Méthode centrale : envoie la requête et gère les erreurs
    # --------------------------------------------------------
    def _requete(self, methode, chemin, json=None, params=None):
        en_tetes = {"Accept": "application/json"}
        if self.token:
            en_tetes["Authorization"] = f"Bearer {self.token}"

        try:
            reponse = requests.request(methode, self.url_base + chemin, json=json,
                                       params=params, headers=en_tetes,
                                       timeout=DELAI_SECONDES)
        except requests.exceptions.ConnectionError:
            raise ErreurApi(-1, f"Serveur injoignable à {self.url_base} (app.py est-il lancé ?)")
        except requests.exceptions.Timeout:
            raise ErreurApi(-1, f"Le serveur n'a pas répondu en {DELAI_SECONDES} s")
        except requests.exceptions.RequestException as e:
            raise ErreurApi(-1, f"Erreur réseau : {e}")

        # Le corps est normalement du JSON ; on se protège si ce n'est pas le cas
        try:
            donnees = reponse.json()
        except ValueError:
            donnees = {"message": reponse.text or "Réponse vide"}

        if not reponse.ok:  # ok = code 2xx
            raise ErreurApi(reponse.status_code, self._message_erreur(donnees))
        return donnees

    @staticmethod
    def _message_erreur(donnees):
        """Même logique que ReponseApi.getMessageErreur() côté Android."""
        if isinstance(donnees, dict):
            if "message" in donnees:
                return donnees["message"]
            details = donnees.get("details")
            if isinstance(details, dict):
                return "; ".join(f"{champ} : {msgs[0] if msgs else ''}"
                                 for champ, msgs in details.items())
        return str(donnees)

    # ================= Authentification =================
    def inscrire(self, email, mot_de_passe, nom, prenom):
        return self._requete("POST", "/signup", json={
            "email": email, "password": mot_de_passe, "nom": nom, "prenom": prenom})

    def connecter(self, email, mot_de_passe):
        donnees = self._requete("POST", "/login",
                                json={"email": email, "password": mot_de_passe})
        self.token = donnees["token"]
        self.prenom = donnees.get("prenom")
        self.role = donnees.get("role")
        return donnees

    def deconnecter(self):
        self.token = self.prenom = self.role = None

    # ================= Équipes (admin) =================
    def creer_equipe(self, nom, sport, saison=None):
        return self._requete("POST", "/api/teams",
                             json={"nom": nom, "sport": sport, "saison": saison})

    def mes_equipes(self):
        return self._requete("GET", "/api/teams")["teams"]

    def modifier_equipe(self, team_id, **champs):
        return self._requete("PUT", f"/api/teams/{team_id}", json=champs)

    def supprimer_equipe(self, team_id):
        return self._requete("DELETE", f"/api/teams/{team_id}")

    def joueurs_equipe(self, team_id):
        return self._requete("GET", f"/api/teams/{team_id}/joueurs")["joueurs"]

    def retirer_joueur(self, team_id, enfant_id):
        return self._requete("DELETE", f"/api/teams/{team_id}/joueurs/{enfant_id}")

    # ================= Équipes (tous) =================
    def toutes_les_equipes(self, enfant_id=None):
        params = {"enfant_id": enfant_id} if enfant_id else None
        return self._requete("GET", "/api/teams/all", params=params)["teams"]

    # ================= Enfants (parent) =================
    def ajouter_enfant(self, prenom, nom, date_naissance=None):
        corps = {"prenom": prenom, "nom": nom}
        if date_naissance:
            corps["date_naissance"] = date_naissance
        return self._requete("POST", "/api/enfants", json=corps)

    def mes_enfants(self):
        return self._requete("GET", "/api/enfants")["enfants"]

    def equipes_enfant(self, enfant_id):
        return self._requete("GET", f"/api/enfants/{enfant_id}/equipes")["teams"]

    def inscrire_enfant(self, enfant_id, team_id):
        return self._requete("POST", f"/api/enfants/{enfant_id}/equipes/{team_id}")


# ============================================================
# Affichage
# ============================================================
def afficher_equipes(equipes):
    if not equipes:
        print("   (aucune équipe)")
    for i, t in enumerate(equipes, 1):
        extra = ""
        if "nb_inscrits" in t:
            extra = f" - {t['nb_inscrits']} inscrit(s)"
        if t.get("deja_inscrit"):
            extra += " ✓ déjà inscrit(e)"
        print(f"   {i}. {t['nom']} ({t['sport']}){extra}")


def afficher_enfants(enfants):
    if not enfants:
        print("   (aucun enfant)")
    for i, e in enumerate(enfants, 1):
        date = f" - né(e) le {e['date_naissance']}" if e.get("date_naissance") else ""
        print(f"   {i}. {e['prenom']} {e['nom']}{date}")


def choisir(liste, libelle):
    """Fait choisir un élément d'une liste par son numéro ; None si annulé."""
    if not liste:
        print(f"   Aucun(e) {libelle} disponible.")
        return None
    saisie = input(f"   Numéro de l'{libelle} (Entrée = annuler) : ").strip()
    if not saisie.isdigit() or not 1 <= int(saisie) <= len(liste):
        return None
    return liste[int(saisie) - 1]


# ============================================================
# Menu interactif
# ============================================================
def menu_admin(client):
    while True:
        print(f"\n=== Menu ADMIN ({client.prenom}) ===")
        print(" 1. Créer une équipe\n 2. Équipes que je gère\n 3. Modifier une équipe")
        print(" 4. Supprimer une équipe\n 5. Joueurs d'une équipe\n 6. Retirer un joueur")
        print(" 0. Se déconnecter")
        choix = input("Choix : ").strip()
        try:
            if choix == "1":
                t = client.creer_equipe(input("   Nom : "), input("   Sport : "),
                                        input("   Saison (facultatif) : ") or None)
                print(f"   ✔ Équipe créée : {t['nom']}")
            elif choix == "2":
                afficher_equipes(client.mes_equipes())
            elif choix == "3":
                equipes = client.mes_equipes()
                afficher_equipes(equipes)
                t = choisir(equipes, "équipe")
                if t:
                    champs = {}
                    nom = input(f"   Nouveau nom [{t['nom']}] : ").strip()
                    sport = input(f"   Nouveau sport [{t['sport']}] : ").strip()
                    if nom:
                        champs["nom"] = nom
                    if sport:
                        champs["sport"] = sport
                    t = client.modifier_equipe(t["id"], **champs)
                    print(f"   ✔ Équipe modifiée : {t['nom']} ({t['sport']})")
            elif choix == "4":
                equipes = client.mes_equipes()
                afficher_equipes(equipes)
                t = choisir(equipes, "équipe")
                if t and input(f"   Supprimer {t['nom']} ? (o/n) ").lower() == "o":
                    print("   ✔", client.supprimer_equipe(t["id"])["message"])
            elif choix in ("5", "6"):
                equipes = client.mes_equipes()
                afficher_equipes(equipes)
                t = choisir(equipes, "équipe")
                if t:
                    joueurs = client.joueurs_equipe(t["id"])
                    for i, j in enumerate(joueurs, 1):
                        print(f"   {i}. {j['prenom']} {j['nom']} (parent : {j['parent']})")
                    if not joueurs:
                        print("   (aucun joueur inscrit)")
                    if choix == "6":
                        j = choisir(joueurs, "joueur")
                        if j:
                            print("   ✔", client.retirer_joueur(t["id"], j["id"])["message"])
            elif choix == "0":
                client.deconnecter()
                return
        except ErreurApi as e:
            print(f"   ✘ Erreur {e.code} : {e.message}")


def menu_parent(client):
    while True:
        print(f"\n=== Menu PARENT ({client.prenom}) ===")
        print(" 1. Voir toutes les équipes\n 2. Mes enfants\n 3. Ajouter un enfant")
        print(" 4. Équipes d'un enfant\n 5. Inscrire un enfant à une équipe")
        print(" 0. Se déconnecter")
        choix = input("Choix : ").strip()
        try:
            if choix == "1":
                afficher_equipes(client.toutes_les_equipes())
            elif choix == "2":
                afficher_enfants(client.mes_enfants())
            elif choix == "3":
                e = client.ajouter_enfant(input("   Prénom : "), input("   Nom : "),
                                          input("   Date de naissance AAAA-MM-JJ (facultatif) : ") or None)
                print(f"   ✔ {e['prenom']} ajouté(e)")
            elif choix in ("4", "5"):
                enfants = client.mes_enfants()
                afficher_enfants(enfants)
                e = choisir(enfants, "enfant")
                if e and choix == "4":
                    afficher_equipes(client.equipes_enfant(e["id"]))
                elif e:
                    equipes = client.toutes_les_equipes(enfant_id=e["id"])
                    afficher_equipes(equipes)
                    t = choisir(equipes, "équipe")
                    if t:
                        print("   ✔", client.inscrire_enfant(e["id"], t["id"])["message"])
            elif choix == "0":
                client.deconnecter()
                return
        except ErreurApi as err:
            print(f"   ✘ Erreur {err.code} : {err.message}")


def menu_principal():
    client = ClientTournois()
    print(f"Client API Plateforme de tournois — serveur : {client.url_base}")
    while True:
        print("\n=== Accueil ===\n 1. Se connecter\n 2. Créer un compte parent\n 0. Quitter")
        choix = input("Choix : ").strip()
        try:
            if choix == "1":
                client.connecter(input("   Courriel : "), input("   Mot de passe : "))
                print(f"   ✔ Connecté(e) : {client.prenom} ({client.role})")
                if client.role in ("admin_equipe", "admin_plateforme"):
                    menu_admin(client)
                else:
                    menu_parent(client)
            elif choix == "2":
                client.inscrire(input("   Courriel : "), input("   Mot de passe (6 car. min) : "),
                                input("   Nom : "), input("   Prénom : "))
                print("   ✔ Compte créé, vous pouvez vous connecter")
            elif choix == "0":
                return
        except ErreurApi as e:
            print(f"   ✘ Erreur {e.code} : {e.message}")


# ============================================================
# Scénario de démonstration automatique (toutes les opérations)
# ============================================================
def etape(titre, fonction, attendu_erreur=None):
    """Exécute une étape et affiche OK / ÉCHEC. attendu_erreur = code HTTP attendu."""
    try:
        resultat = fonction()
        if attendu_erreur:
            print(f"✘ {titre} : aurait dû échouer avec {attendu_erreur}")
            return None
        print(f"✔ {titre}")
        return resultat
    except ErreurApi as e:
        if attendu_erreur == e.code:
            print(f"✔ {titre} : refusé comme prévu ({e.code} - {e.message})")
        else:
            print(f"✘ {titre} : erreur {e.code} - {e.message}")
        return None


def demo(email_admin, mdp_admin, email_parent, mdp_parent):
    admin = ClientTournois()
    parent = ClientTournois()
    print(f"Démonstration — serveur : {admin.url_base}\n")

    print("--- Admin ---")
    etape("Connexion admin", lambda: admin.connecter(email_admin, mdp_admin))
    t = etape("Créer l'équipe « Démo Client »",
              lambda: admin.creer_equipe("Démo Client", "soccer", "2026-2027"))
    if not t:
        return
    etape("Lister mes équipes", admin.mes_equipes)
    etape("Modifier l'équipe", lambda: admin.modifier_equipe(t["id"], nom="Démo Client U12"))

    print("\n--- Parent ---")
    # Inscription du parent : 400 si le compte existe déjà, ce n'est pas grave
    try:
        parent.inscrire(email_parent, mdp_parent, "Parent", "Démo")
        print("✔ Compte parent créé")
    except ErreurApi:
        print("✔ Compte parent déjà existant")
    etape("Connexion parent", lambda: parent.connecter(email_parent, mdp_parent))
    etape("Parent tente de créer une équipe", lambda: parent.creer_equipe("Interdit", "hockey"),
          attendu_erreur=403)
    e = etape("Ajouter un enfant", lambda: parent.ajouter_enfant("Léa", "Démo", "2016-05-12"))
    etape("Date invalide refusée", lambda: parent.ajouter_enfant("X", "Y", "pas-une-date"),
          attendu_erreur=400)
    if not e:
        return
    etape("Voir toutes les équipes", parent.toutes_les_equipes)
    etape("Inscrire l'enfant", lambda: parent.inscrire_enfant(e["id"], t["id"]))
    etape("Double inscription refusée", lambda: parent.inscrire_enfant(e["id"], t["id"]),
          attendu_erreur=400)
    etape("Équipes de l'enfant", lambda: parent.equipes_enfant(e["id"]))

    print("\n--- Admin : joueurs ---")
    etape("Joueurs de l'équipe", lambda: admin.joueurs_equipe(t["id"]))
    etape("Parent tente de voir les joueurs",
          lambda: parent.joueurs_equipe(t["id"]), attendu_erreur=403)
    etape("Retirer le joueur", lambda: admin.retirer_joueur(t["id"], e["id"]))
    etape("Supprimer l'équipe", lambda: admin.supprimer_equipe(t["id"]))

    print("\n--- Sécurité ---")
    anonyme = ClientTournois()
    etape("Accès sans token refusé", anonyme.toutes_les_equipes, attendu_erreur=401)


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--demo":
        demo(*sys.argv[2:6])
    else:
        menu_principal()
