from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'secret'

# Configuration SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --------------------
# MODELES SQLALCHEMY
# ---------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')

    # Relations
    vehicules = db.relationship('Vehicule', backref='proprietaire', lazy=True, cascade='all, delete-orphan')
    conducteurs = db.relationship('Conducteur', backref='proprietaire', lazy=True, cascade='all, delete-orphan')
    maintenances = db.relationship('Maintenance', backref='proprietaire', lazy=True, cascade='all, delete-orphan')
    trajets = db.relationship('Trajet', backref='proprietaire', lazy=True, cascade='all, delete-orphan')


class Vehicule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # AJOUTÉ
    marque = db.Column(db.String(100))
    modele = db.Column(db.String(100))
    immatriculation = db.Column(db.String(100))
    annee = db.Column(db.Integer)
    kilometrage = db.Column(db.Integer)
    statut = db.Column(db.String(50), default="Disponible")
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)

    # Index composite pour assurer l'unicité par utilisateur
    __table_args__ = (db.UniqueConstraint('user_id', 'immatriculation', name='_user_immatriculation'),)


class Conducteur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # AJOUTÉ
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    permis = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    experience = db.Column(db.Integer)
    
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)


class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # AJOUTÉ
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicule.id'))
    type_maintenance = db.Column(db.String(100))
    description = db.Column(db.Text)
    cout = db.Column(db.Float)
    date_maintenance = db.Column(db.Date)
    statut = db.Column(db.String(50), default="Programmée")


class Trajet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # AJOUTÉ
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicule.id'))
    conducteur_id = db.Column(db.Integer, db.ForeignKey('conducteur.id'))
    depart = db.Column(db.String(100))
    arrivee = db.Column(db.String(100))
    distance = db.Column(db.Float)
    duree = db.Column(db.Integer)
    date_trajet = db.Column(db.Date)


# -----------------------------
# DECORATEUR LOGIN REQUIS
# -----------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# -----------------------------
# ROUTES AUTHENTIFICATION
# -----------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        nom = request.form['nom']
        prenom = request.form['prenom']

        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Nom d\'utilisateur existant.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email déjà utilisé.', 'error')
            return render_template('register.html')

        hashed_pw = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_pw, nom=nom, prenom=prenom)
        db.session.add(user)
        db.session.commit()
        flash('Inscription réussie !', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_nom'] = f"{user.prenom} {user.nom}"
            session['user_role'] = user.role
            flash(f"Bienvenue {user.prenom} !", 'success')
            return redirect(url_for('index'))

        flash('Identifiants incorrects.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnexion réussie.", 'info')
    return redirect(url_for('login'))


# -----------------------------
# ROUTES PRINCIPALES
# -----------------------------

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/dashboard')
@login_required
def index():
    user_id = session['user_id']

    stats = {
        'total_vehicules': Vehicule.query.filter_by(user_id=user_id).count(),
        'vehicules_disponibles': Vehicule.query.filter_by(user_id=user_id, statut='Disponible').count(),
        'total_conducteurs': Conducteur.query.filter_by(user_id=user_id).count(),
        'maintenances_programmees': Maintenance.query.filter_by(user_id=user_id, statut='Programmée').count(),
        'total_trajets': Trajet.query.filter_by(user_id=user_id).count(),
        'total_km': db.session.query(db.func.sum(Trajet.distance)).filter_by(user_id=user_id).scalar() or 0,
        'cout_maintenance': db.session.query(db.func.sum(Maintenance.cout)).filter_by(user_id=user_id).scalar() or 0
    }
    return render_template('index.html', stats=stats)


# -----------------------------
# ROUTES VEHICULES (MODIFIÉES)
# -----------------------------

@app.route('/vehicules')
@login_required
def liste_vehicules():
    user_id = session['user_id']
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('vehicules.html', vehicules=vehicules)


@app.route('/vehicules/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_vehicule():
    if request.method == 'POST':
        user_id = session['user_id']
        vehicule = Vehicule(
            user_id=user_id,  # AJOUTÉ
            marque=request.form['marque'],
            modele=request.form['modele'],
            immatriculation=request.form['immatriculation'],
            annee=int(request.form['annee']),
            kilometrage=int(request.form['kilometrage']),
            statut=request.form.get('statut', 'Disponible')
        )
        db.session.add(vehicule)
        db.session.commit()
        flash('Véhicule ajouté avec succès!', 'success')
        return redirect(url_for('liste_vehicules'))
    return render_template('ajouter_vehicule.html')


@app.route('/vehicules/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_vehicule(id):
    user_id = session['user_id']
    vehicule = Vehicule.query.filter_by(id=id, user_id=user_id).first_or_404()

    if request.method == 'POST':
        vehicule.marque = request.form['marque']
        vehicule.modele = request.form['modele']
        vehicule.immatriculation = request.form['immatriculation']
        vehicule.annee = int(request.form['annee'])
        vehicule.kilometrage = int(request.form['kilometrage'])
        vehicule.statut = request.form['statut']
        db.session.commit()
        flash('Véhicule modifié avec succès!', 'success')
        return redirect(url_for('liste_vehicules'))
    return render_template('modifier_vehicule.html', vehicule=vehicule)


@app.route('/vehicules/supprimer/<int:id>')
@login_required
def supprimer_vehicule(id):
    user_id = session['user_id']
    vehicule = Vehicule.query.filter_by(id=id, user_id=user_id).first_or_404()
    db.session.delete(vehicule)
    db.session.commit()
    flash('Véhicule supprimé avec succès!', 'success')
    return redirect(url_for('liste_vehicules'))


# -----------------------------
# ROUTES CONDUCTEURS
# -----------------------------

@app.route('/conducteurs')
@login_required
def liste_conducteurs():
    user_id = session['user_id']
    conducteurs = Conducteur.query.filter_by(user_id=user_id).all()
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('conducteurs.html', conducteurs=conducteurs, vehicules=vehicules)


@app.route('/conducteurs/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_conducteur():
    if request.method == 'POST':
        user_id = session['user_id']
        conducteur = Conducteur(
            user_id=user_id,  # AJOUTÉ
            nom=request.form['nom'],
            prenom=request.form['prenom'],
            permis=request.form['permis'],
            telephone=request.form['telephone'],
            email=request.form['email'],
            experience=int(request.form['experience'])
        )
        db.session.add(conducteur)
        db.session.commit()
        flash('Conducteur ajouté avec succès!', 'success')
        return redirect(url_for('liste_conducteurs'))

    user_id = session['user_id']
    vehicules = Vehicule.query.filter_by(user_id=user_id, statut='Disponible').all()
    return render_template('ajouter_conducteur.html', vehicules=vehicules)


@app.route('/conducteurs/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_conducteur(id):
    user_id = session['user_id']
    conducteur = Conducteur.query.filter_by(id=id, user_id=user_id).first_or_404()

    if request.method == 'POST':
        conducteur.nom = request.form['nom']
        conducteur.prenom = request.form['prenom']
        conducteur.permis = request.form['permis']
        conducteur.telephone = request.form['telephone']
        conducteur.email = request.form['email']
        conducteur.experience = int(request.form['experience'])
        db.session.commit()
        flash('Conducteur modifié avec succès!', 'success')
        return redirect(url_for('liste_conducteurs'))

    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('modifier_conducteur.html', conducteur=conducteur, vehicules=vehicules)


@app.route('/conducteurs/supprimer/<int:id>')
@login_required
def supprimer_conducteur(id):
    user_id = session['user_id']
    conducteur = Conducteur.query.filter_by(id=id, user_id=user_id).first_or_404()
    db.session.delete(conducteur)
    db.session.commit()
    flash('Conducteur supprimé avec succès!', 'success')
    return redirect(url_for('liste_conducteurs'))


# -----------------------------
# ROUTES MAINTENANCES
# -----------------------------

@app.route('/maintenances')
@login_required
def liste_maintenances():
    user_id = session['user_id']
    maintenances = Maintenance.query.filter_by(user_id=user_id).all()
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('maintenance.html', maintenances=maintenances, vehicules=vehicules)


@app.route('/maintenance/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_maintenance():
    if request.method == 'POST':
        user_id = session['user_id']
        maintenance = Maintenance(
            user_id=user_id,  # AJOUTÉ
            vehicule_id=int(request.form['vehicule_id']),
            type_maintenance=request.form['type_maintenance'],
            description=request.form['description'],
            cout=float(request.form['cout']),
            date_maintenance=datetime.strptime(request.form['date_maintenance'], '%Y-%m-%d').date(),
            statut=request.form.get('statut', 'Programmée')
        )
        db.session.add(maintenance)
        db.session.commit()
        flash('Maintenance ajoutée avec succès!', 'success')
        return redirect(url_for('liste_maintenances'))

    user_id = session['user_id']
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('ajouter_maintenance.html', vehicules=vehicules)


@app.route('/maintenances/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_maintenance(id):
    user_id = session['user_id']
    maintenance = Maintenance.query.filter_by(id=id, user_id=user_id).first_or_404()

    if request.method == 'POST':
        maintenance.vehicule_id = int(request.form['vehicule_id'])
        maintenance.type_maintenance = request.form['type_maintenance']
        maintenance.description = request.form['description']
        maintenance.cout = float(request.form['cout'])
        maintenance.date_maintenance = datetime.strptime(request.form['date_maintenance'], '%Y-%m-%d').date()
        maintenance.statut = request.form['statut']
        db.session.commit()
        flash('Maintenance modifiée avec succès!', 'success')
        return redirect(url_for('liste_maintenances'))

    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    return render_template('modifier_maintenance.html', maintenance=maintenance, vehicules=vehicules)


@app.route('/maintenances/supprimer/<int:id>')
@login_required
def supprimer_maintenance(id):
    user_id = session['user_id']
    maintenance = Maintenance.query.filter_by(id=id, user_id=user_id).first_or_404()
    db.session.delete(maintenance)
    db.session.commit()
    flash('Maintenance supprimée avec succès!', 'success')
    return redirect(url_for('liste_maintenances'))


# -----------------------------
#       ROUTES TRAJETS
# -----------------------------

@app.route('/trajets')
@login_required
def liste_trajets():
    user_id = session['user_id']
    trajets = Trajet.query.filter_by(user_id=user_id).all()
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    conducteurs = Conducteur.query.filter_by(user_id=user_id).all()
    return render_template('trajets.html', trajets=trajets, vehicules=vehicules, conducteurs=conducteurs)


@app.route('/trajets/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter_trajet():
    if request.method == 'POST':
        user_id = session['user_id']
        trajet = Trajet(
            user_id=user_id,  # AJOUTÉ
            vehicule_id=int(request.form['vehicule_id']),
            conducteur_id=int(request.form['conducteur_id']),
            depart=request.form['depart'],
            arrivee=request.form['arrivee'],
            distance=float(request.form['distance']),
            duree=int(request.form['duree']),
            date_trajet=datetime.strptime(request.form['date_trajet'], '%Y-%m-%d').date()
        )
        db.session.add(trajet)

        # Mettre à jour le kilométrage du véhicule (uniquement si c'est le véhicule de l'utilisateur)
        vehicule = Vehicule.query.filter_by(id=trajet.vehicule_id, user_id=user_id).first()
        if vehicule:
            vehicule.kilometrage += int(trajet.distance)

        db.session.commit()
        flash('Trajet ajouté avec succès!', 'success')
        return redirect(url_for('liste_trajets'))

    user_id = session['user_id']
    vehicules = Vehicule.query.filter_by(user_id=user_id, statut='Disponible').all()
    conducteurs = Conducteur.query.filter_by(user_id=user_id).all()
    return render_template('ajouter_trajet.html', vehicules=vehicules, conducteurs=conducteurs)


@app.route('/trajets/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_trajet(id):
    user_id = session['user_id']
    trajet = Trajet.query.filter_by(id=id, user_id=user_id).first_or_404()
    ancienne_distance = trajet.distance

    if request.method == 'POST':
        trajet.vehicule_id = int(request.form['vehicule_id'])
        trajet.conducteur_id = int(request.form['conducteur_id'])
        trajet.depart = request.form['depart']
        trajet.arrivee = request.form['arrivee']
        trajet.distance = float(request.form['distance'])
        trajet.duree = int(request.form['duree'])
        trajet.date_trajet = datetime.strptime(request.form['date_trajet'], '%Y-%m-%d').date()

        # Ajuster le kilométrage du véhicule (uniquement si c'est le véhicule de l'utilisateur)
        vehicule = Vehicule.query.filter_by(id=trajet.vehicule_id, user_id=user_id).first()
        if vehicule:
            vehicule.kilometrage = vehicule.kilometrage - int(ancienne_distance) + int(trajet.distance)

        db.session.commit()
        flash('Trajet modifié avec succès!', 'success')
        return redirect(url_for('liste_trajets'))

    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    conducteurs = Conducteur.query.filter_by(user_id=user_id).all()
    return render_template('modifier_trajet.html', trajet=trajet, vehicules=vehicules, conducteurs=conducteurs)


@app.route('/trajets/supprimer/<int:id>')
@login_required
def supprimer_trajet(id):
    user_id = session['user_id']
    trajet = Trajet.query.filter_by(id=id, user_id=user_id).first_or_404()

    # Soustraire la distance du kilométrage du véhicule (uniquement si c'est le véhicule de l'utilisateur)
    vehicule = Vehicule.query.filter_by(id=trajet.vehicule_id, user_id=user_id).first()
    if vehicule:
        vehicule.kilometrage -= int(trajet.distance)

    db.session.delete(trajet)
    db.session.commit()
    flash('Trajet supprimé avec succès!', 'success')
    return redirect(url_for('liste_trajets'))


# -----------------------------
#       ROUTES RAPPORTS
# -----------------------------

@app.route('/rapports')
@login_required
def rapports():
    user_id = session['user_id']

    # Statistiques générales avec gestion robuste des statuts pour l'utilisateur courant
    total_vehicules = Vehicule.query.filter_by(user_id=user_id).count()

    vehicules_disponibles = Vehicule.query.filter(
        Vehicule.user_id == user_id,
        db.func.lower(db.func.trim(Vehicule.statut)) == 'disponible'
    ).count()

    vehicules_maintenance = Vehicule.query.filter(
        Vehicule.user_id == user_id,
        db.or_(
            db.func.lower(db.func.trim(Vehicule.statut)) == 'en maintenance',
            db.func.lower(db.func.trim(Vehicule.statut)) == 'maintenance'
        )
    ).count()

    stats = {
        'total_vehicules': total_vehicules,
        'vehicules_disponibles': vehicules_disponibles,
        'vehicules_maintenance': vehicules_maintenance,
        'total_conducteurs': Conducteur.query.filter_by(user_id=user_id).count(),
        'total_trajets': Trajet.query.filter_by(user_id=user_id).count(),
        'total_km': db.session.query(db.func.sum(Trajet.distance)).filter_by(user_id=user_id).scalar() or 0,
        'cout_maintenance': db.session.query(db.func.sum(Maintenance.cout)).filter_by(user_id=user_id).scalar() or 0,
        'maintenances_programmees': Maintenance.query.filter(
            Maintenance.user_id == user_id,
            db.func.lower(db.func.trim(Maintenance.statut)) == 'programmée'
        ).count(),
        'maintenances_terminees': Maintenance.query.filter(
            Maintenance.user_id == user_id,
            db.func.lower(db.func.trim(Maintenance.statut)) == 'terminée'
        ).count()
    }

    # Trajets récents (10 derniers) pour l'utilisateur
    trajets_recents = Trajet.query.filter_by(user_id=user_id).order_by(Trajet.date_trajet.desc()).limit(10).all()

    # Maintenances à venir pour l'utilisateur
    maintenances_a_venir = Maintenance.query.filter(
        Maintenance.user_id == user_id,
        Maintenance.date_maintenance >= date.today(),
        db.func.lower(db.func.trim(Maintenance.statut)) == 'programmée'
    ).order_by(Maintenance.date_maintenance).limit(5).all()

    # Véhicules avec le plus de kilomètres pour l'utilisateur
    vehicules_km = Vehicule.query.filter_by(user_id=user_id).order_by(Vehicule.kilometrage.desc()).limit(5).all()

    # Conducteurs les plus actifs (par nombre de trajets) pour l'utilisateur
    conducteurs_actifs = db.session.query(
        Conducteur.id,
        Conducteur.nom,
        Conducteur.prenom,
        db.func.count(Trajet.id).label('nb_trajets')
    ).join(Trajet).filter(
        Conducteur.user_id == user_id,
        Trajet.user_id == user_id
    ).group_by(Conducteur.id, Conducteur.nom, Conducteur.prenom).order_by(
        db.func.count(Trajet.id).desc()).limit(5).all()

    # Convertir les résultats en objets accessibles dans le template
    conducteurs_actifs_list = []
    for conducteur in conducteurs_actifs:
        conducteurs_actifs_list.append({
            'id': conducteur.id,
            'nom': conducteur.nom,
            'prenom': conducteur.prenom,
            'nb_trajets': conducteur.nb_trajets
        })

    # Récupérer tous les véhicules et conducteurs de l'utilisateur pour les afficher dans les tableaux
    vehicules = Vehicule.query.filter_by(user_id=user_id).all()
    conducteurs = Conducteur.query.filter_by(user_id=user_id).all()

    return render_template('rapports.html',
                           stats=stats,
                           trajets_recents=trajets_recents,
                           maintenances_a_venir=maintenances_a_venir,
                           vehicules_km=vehicules_km,
                           conducteurs_actifs=conducteurs_actifs_list,
                           vehicules=vehicules,
                           conducteurs=conducteurs)


# -----------------------------
# INIT DB
# -----------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)