from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret'

# Fichiers pour sauvegarder les données
USERS_FILE = 'users.json'
DATA_DIR = 'user_data'

# Créer le dossier pour les données utilisateurs s'il n'existe pas
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Liste des utilisateurs - maintenant sauvegardée dans un fichier
utilisateurs = []

# Variables globales pour les données de l'utilisateur connecté
vehicules = []
conducteurs = []
maintenances = []
trajets = []


# Fonctions de gestion des utilisateurs
def load_users():
    """Charge la liste des utilisateurs depuis le fichier"""
    global utilisateurs
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                utilisateurs = json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement des utilisateurs: {e}")


def save_users():
    """Sauvegarde la liste des utilisateurs"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(utilisateurs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des utilisateurs: {e}")


def get_user_data_file(user_id):
    """Retourne le chemin du fichier de données pour un utilisateur"""
    return os.path.join(DATA_DIR, f'user_{user_id}_data.json')


# Décorateur pour protéger les routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Route de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Rechercher l'utilisateur
        user = next((u for u in utilisateurs if u['username'] == username), None)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session['user_nom'] = f"{user['prenom']} {user['nom']}"

            # Charger les données de l'utilisateur
            load_user_data(user['id'])

            flash(f'Bienvenue {user["prenom"]} {user["nom"]} !', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')

    return render_template('login.html')


# Route d'inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nom = request.form['nom']
        prenom = request.form['prenom']

        # Vérifications
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('register.html')

        # Vérifier si l'utilisateur existe déjà
        if any(u['username'] == username for u in utilisateurs):
            flash('Ce nom d\'utilisateur existe déjà.', 'error')
            return render_template('register.html')

        if any(u['email'] == email for u in utilisateurs):
            flash('Cette adresse email est déjà utilisée.', 'error')
            return render_template('register.html')

        # Créer le nouvel utilisateur
        nouveau_id = max([u['id'] for u in utilisateurs], default=0) + 1
        nouvel_utilisateur = {
            'id': nouveau_id,
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'user',  # Par défaut
            'nom': nom,
            'prenom': prenom
        }

        utilisateurs.append(nouvel_utilisateur)
        save_users()

        # Créer un fichier de données vide pour le nouvel utilisateur
        create_empty_user_data(nouveau_id)

        flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Route de déconnexion
@app.route('/logout')
def logout():
    user_nom = session.get('user_nom', 'Utilisateur')

    # Sauvegarder les données avant de se déconnecter
    if 'user_id' in session:
        save_user_data(session['user_id'])

    session.clear()
    flash(f'Au revoir {user_nom} ! Vous êtes maintenant déconnecté.', 'info')
    return redirect(url_for('login'))


# Classes pour structurer les données (inchangées)
class Vehicule:
    def __init__(self, id, marque, modele, immatriculation, annee, kilometrage, statut="Disponible"):
        self.id = id
        self.marque = marque
        self.modele = modele
        self.immatriculation = immatriculation
        self.annee = annee
        self.kilometrage = kilometrage
        self.statut = statut
        self.date_ajout = datetime.now().isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'marque': self.marque,
            'modele': self.modele,
            'immatriculation': self.immatriculation,
            'annee': self.annee,
            'kilometrage': self.kilometrage,
            'statut': self.statut,
            'date_ajout': self.date_ajout
        }

    @classmethod
    def from_dict(cls, data):
        vehicule = cls(
            data['id'], data['marque'], data['modele'],
            data['immatriculation'], data['annee'], data['kilometrage'], data['statut']
        )
        vehicule.date_ajout = data['date_ajout']
        return vehicule


class Conducteur:
    def __init__(self, id, nom, prenom, permis, telephone, email, experience):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.permis = permis
        self.telephone = telephone
        self.email = email
        self.experience = experience
        self.vehicule_assigne = None
        self.date_ajout = datetime.now().isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'prenom': self.prenom,
            'permis': self.permis,
            'telephone': self.telephone,
            'email': self.email,
            'experience': self.experience,
            'vehicule_assigne': self.vehicule_assigne,
            'date_ajout': self.date_ajout
        }

    @classmethod
    def from_dict(cls, data):
        conducteur = cls(
            data['id'], data['nom'], data['prenom'],
            data['permis'], data['telephone'], data['email'], data['experience']
        )
        conducteur.vehicule_assigne = data.get('vehicule_assigne')
        conducteur.date_ajout = data['date_ajout']
        return conducteur


class Maintenance:
    def __init__(self, id, vehicule_id, type_maintenance, description, cout, date_maintenance):
        self.id = id
        self.vehicule_id = vehicule_id
        self.type_maintenance = type_maintenance
        self.description = description
        self.cout = cout
        self.date_maintenance = date_maintenance
        self.statut = "Programmée"

    def to_dict(self):
        return {
            'id': self.id,
            'vehicule_id': self.vehicule_id,
            'type_maintenance': self.type_maintenance,
            'description': self.description,
            'cout': self.cout,
            'date_maintenance': self.date_maintenance,
            'statut': self.statut
        }

    @classmethod
    def from_dict(cls, data):
        maintenance = cls(
            data['id'], data['vehicule_id'], data['type_maintenance'],
            data['description'], data['cout'], data['date_maintenance']
        )
        maintenance.statut = data.get('statut', 'Programmée')
        return maintenance


class Trajet:
    def __init__(self, id, vehicule_id, conducteur_id, depart, arrivee, distance, duree, date_trajet):
        self.id = id
        self.vehicule_id = vehicule_id
        self.conducteur_id = conducteur_id
        self.depart = depart
        self.arrivee = arrivee
        self.distance = distance
        self.duree = duree
        self.date_trajet = date_trajet.isoformat() if isinstance(date_trajet, date) else date_trajet

    def to_dict(self):
        return {
            'id': self.id,
            'vehicule_id': self.vehicule_id,
            'conducteur_id': self.conducteur_id,
            'depart': self.depart,
            'arrivee': self.arrivee,
            'distance': self.distance,
            'duree': self.duree,
            'date_trajet': self.date_trajet
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['id'], data['vehicule_id'], data['conducteur_id'],
            data['depart'], data['arrivee'], data['distance'],
            data['duree'], data['date_trajet']
        )


# Nouvelles fonctions de gestion des données par utilisateur
def create_empty_user_data(user_id):
    """Crée un fichier de données vide pour un nouvel utilisateur"""
    data = {
        'vehicules': [],
        'conducteurs': [],
        'maintenances': [],
        'trajets': []
    }
    user_file = get_user_data_file(user_id)
    try:
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la création des données utilisateur: {e}")


def save_user_data(user_id):
    """Sauvegarde les données de l'utilisateur connecté"""
    data = {
        'vehicules': [v.to_dict() for v in vehicules],
        'conducteurs': [c.to_dict() for c in conducteurs],
        'maintenances': [m.to_dict() for m in maintenances],
        'trajets': [t.to_dict() for t in trajets]
    }
    user_file = get_user_data_file(user_id)
    try:
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des données utilisateur: {e}")


def load_user_data(user_id):
    """Charge les données de l'utilisateur spécifié"""
    global vehicules, conducteurs, maintenances, trajets

    user_file = get_user_data_file(user_id)

    if not os.path.exists(user_file):
        # Créer un fichier vide si il n'existe pas
        create_empty_user_data(user_id)
        vehicules = []
        conducteurs = []
        maintenances = []
        trajets = []
        return

    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        vehicules = [Vehicule.from_dict(v) for v in data.get('vehicules', [])]
        conducteurs = [Conducteur.from_dict(c) for c in data.get('conducteurs', [])]
        maintenances = [Maintenance.from_dict(m) for m in data.get('maintenances', [])]
        trajets = [Trajet.from_dict(t) for t in data.get('trajets', [])]

        print(f"Données utilisateur {user_id} chargées avec succès!")
    except Exception as e:
        print(f"Erreur lors du chargement des données utilisateur: {e}")
        # En cas d'erreur, initialiser avec des listes vides
        vehicules = []
        conducteurs = []
        maintenances = []
        trajets = []


# Fonction modifiée pour sauvegarder automatiquement
def save_data():
    """Sauvegarde les données de l'utilisateur connecté"""
    if 'user_id' in session:
        save_user_data(session['user_id'])


# Routes principales
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/dashboard')
@login_required
def index():
    stats = {
        'total_vehicules': len(vehicules),
        'vehicules_disponibles': len([v for v in vehicules if v.statut == "Disponible"]),
        'total_conducteurs': len(conducteurs),
        'maintenances_programmees': len([m for m in maintenances if m.statut == "Programmée"])
    }
    return render_template('index.html', stats=stats)


# Routes pour les véhicules
@app.route('/vehicules')
@login_required
def liste_vehicules():
    return render_template('vehicules.html', vehicules=vehicules)


@app.route('/vehicules/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_vehicule():
    if request.method == 'POST':
        nouveau_id = max([v.id for v in vehicules], default=0) + 1
        vehicule = Vehicule(
            nouveau_id,
            request.form['marque'],
            request.form['modele'],
            request.form['immatriculation'],
            int(request.form['annee']),
            int(request.form['kilometrage'])
        )
        vehicules.append(vehicule)
        save_data()
        flash('Véhicule ajouté avec succès!', 'success')
        return redirect(url_for('liste_vehicules'))
    return render_template('ajouter_vehicule.html')


@app.route('/vehicules/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_vehicule(id):
    vehicule = next((v for v in vehicules if v.id == id), None)
    if not vehicule:
        flash('Véhicule non trouvé!', 'error')
        return redirect(url_for('liste_vehicules'))

    if request.method == 'POST':
        vehicule.marque = request.form['marque']
        vehicule.modele = request.form['modele']
        vehicule.immatriculation = request.form['immatriculation']
        vehicule.annee = int(request.form['annee'])
        vehicule.kilometrage = int(request.form['kilometrage'])
        vehicule.statut = request.form['statut']
        save_data()
        flash('Véhicule modifié avec succès!', 'success')
        return redirect(url_for('liste_vehicules'))

    return render_template('modifier_vehicule.html', vehicule=vehicule)


@app.route('/vehicules/supprimer/<int:id>')
@login_required
def supprimer_vehicule(id):
    global vehicules
    vehicules = [v for v in vehicules if v.id != id]
    save_data()
    flash('Véhicule supprimé avec succès!', 'success')
    return redirect(url_for('liste_vehicules'))


# Routes pour les conducteurs
@app.route('/conducteurs')
@login_required
def liste_conducteurs():
    return render_template('conducteurs.html', conducteurs=conducteurs)


@app.route('/conducteurs/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_conducteur():
    if request.method == 'POST':
        nouveau_id = max([c.id for c in conducteurs], default=0) + 1
        conducteur = Conducteur(
            nouveau_id,
            request.form['nom'],
            request.form['prenom'],
            request.form['permis'],
            request.form['telephone'],
            request.form['email'],
            int(request.form['experience'])
        )
        conducteurs.append(conducteur)
        save_data()
        flash('Conducteur ajouté avec succès!', 'success')
        return redirect(url_for('liste_conducteurs'))
    return render_template('ajouter_conducteur.html')


@app.route('/conducteurs/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_conducteur(id):
    conducteur = next((c for c in conducteurs if c.id == id), None)
    if not conducteur:
        flash('Conducteur non trouvé!', 'error')
        return redirect(url_for('liste_conducteurs'))

    if request.method == 'POST':
        conducteur.nom = request.form['nom']
        conducteur.prenom = request.form['prenom']
        conducteur.permis = request.form['permis']
        conducteur.telephone = request.form['telephone']
        conducteur.email = request.form['email']
        conducteur.experience = int(request.form['experience'])
        save_data()
        flash('Conducteur modifié avec succès!', 'success')
        return redirect(url_for('liste_conducteurs'))

    return render_template('modifier_conducteur.html', conducteur=conducteur)


@app.route('/conducteurs/supprimer/<int:id>')
@login_required
def supprimer_conducteur(id):
    global conducteurs
    conducteurs = [c for c in conducteurs if c.id != id]
    save_data()
    flash('Conducteur supprimé avec succès!', 'success')
    return redirect(url_for('liste_conducteurs'))


# Routes pour la maintenance
@app.route('/maintenance')
@login_required
def liste_maintenances():
    return render_template('maintenance.html', maintenances=maintenances, vehicules=vehicules)


@app.route('/maintenance/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_maintenance():
    if request.method == 'POST':
        nouveau_id = max([m.id for m in maintenances], default=0) + 1
        maintenance = Maintenance(
            nouveau_id,
            int(request.form['vehicule_id']),
            request.form['type_maintenance'],
            request.form['description'],
            float(request.form['cout']),
            datetime.strptime(request.form['date_maintenance'], '%Y-%m-%d').date()
        )
        maintenances.append(maintenance)
        save_data()
        flash('Maintenance programmée avec succès!', 'success')
        return redirect(url_for('liste_maintenances'))
    return render_template('ajouter_maintenance.html', vehicules=vehicules)


@app.route('/maintenance/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_maintenance(id):
    maintenance = next((m for m in maintenances if m.id == id), None)
    if not maintenance:
        flash('Maintenance non trouvée!', 'error')
        return redirect(url_for('liste_maintenances'))

    if request.method == 'POST':
        maintenance.vehicule_id = int(request.form['vehicule_id'])
        maintenance.type_maintenance = request.form['type_maintenance']
        maintenance.description = request.form['description']
        maintenance.cout = float(request.form['cout'])
        maintenance.date_maintenance = datetime.strptime(request.form['date_maintenance'], '%Y-%m-%d').date()
        maintenance.statut = request.form['statut']
        save_data()
        flash('Maintenance modifiée avec succès!', 'success')
        return redirect(url_for('liste_maintenances'))

    return render_template('modifier_maintenance.html', maintenance=maintenance, vehicules=vehicules)


@app.route('/maintenance/supprimer/<int:id>')
@login_required
def supprimer_maintenance(id):
    global maintenances
    maintenances = [m for m in maintenances if m.id != id]
    save_data()
    flash('Maintenance supprimée avec succès!', 'success')
    return redirect(url_for('liste_maintenances'))


# Routes pour les trajets
@app.route('/trajets')
@login_required
def liste_trajets():
    return render_template('trajets.html', trajets=trajets, vehicules=vehicules, conducteurs=conducteurs)


@app.route('/trajets/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_trajet():
    if request.method == 'POST':
        nouveau_id = max([t.id for t in trajets], default=0) + 1
        trajet = Trajet(
            nouveau_id,
            int(request.form['vehicule_id']),
            int(request.form['conducteur_id']),
            request.form['depart'],
            request.form['arrivee'],
            float(request.form['distance']),
            int(request.form['duree']),
            datetime.strptime(request.form['date_trajet'], '%Y-%m-%d').date()
        )
        trajets.append(trajet)
        save_data()
        flash('Trajet enregistré avec succès!', 'success')
        return redirect(url_for('liste_trajets'))

    return render_template('ajouter_trajet.html',
                           vehicules=vehicules,
                           conducteurs=conducteurs,
                           date_aujourdhui=date.today())


@app.route('/trajets/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_trajet(id):
    trajet = next((t for t in trajets if t.id == id), None)
    if not trajet:
        flash('Trajet non trouvé!', 'error')
        return redirect(url_for('liste_trajets'))

    if request.method == 'POST':
        trajet.vehicule_id = int(request.form['vehicule_id'])
        trajet.conducteur_id = int(request.form['conducteur_id'])
        trajet.depart = request.form['depart']
        trajet.arrivee = request.form['arrivee']
        trajet.distance = float(request.form['distance'])
        trajet.duree = int(request.form['duree'])
        trajet.date_trajet = datetime.strptime(request.form['date_trajet'], '%Y-%m-%d').date()
        save_data()
        flash('Trajet modifié avec succès!', 'success')
        return redirect(url_for('liste_trajets'))

    return render_template('modifier_trajet.html', trajet=trajet, vehicules=vehicules, conducteurs=conducteurs)


@app.route('/trajets/supprimer/<int:id>')
@login_required
def supprimer_trajet(id):
    global trajets
    trajets = [t for t in trajets if t.id != id]
    save_data()
    flash('Trajet supprimé avec succès!', 'success')
    return redirect(url_for('liste_trajets'))


# Route pour les rapports
@app.route('/rapports')
@login_required
def rapports():
    total_distance = sum(t.distance for t in trajets)
    cout_maintenance = sum(m.cout for m in maintenances)
    vehicule_plus_utilise = None

    if trajets:
        usage_vehicules = {}
        for trajet in trajets:
            if trajet.vehicule_id not in usage_vehicules:
                usage_vehicules[trajet.vehicule_id] = 0
            usage_vehicules[trajet.vehicule_id] += trajet.distance

        if usage_vehicules:
            vehicule_id_max = max(usage_vehicules, key=usage_vehicules.get)
            vehicule_plus_utilise = next((v for v in vehicules if v.id == vehicule_id_max), None)

    stats_rapports = {
        'total_distance': total_distance,
        'cout_maintenance': cout_maintenance,
        'vehicule_plus_utilise': vehicule_plus_utilise,
        'nb_trajets': len(trajets)
    }

    return render_template('rapports.html', stats=stats_rapports)


# API pour les données en temps réel
@app.route('/api/stats')
@login_required
def api_stats():
    stats = {
        'vehicules': len(vehicules),
        'conducteurs': len(conducteurs),
        'maintenances': len(maintenances),
        'trajets': len(trajets)
    }
    return jsonify(stats)


if __name__ == '__main__':
    # Charger les utilisateurs au démarrage
    load_users()
    app.run(debug=True)