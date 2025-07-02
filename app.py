def random_localisation_in_arrondissement(arr_name):
    """Génère une localisation aléatoire à l'intérieur d'un arrondissement donné (par nom)."""
    arr_file = os.path.join('static', 'data', 'arrondissements.geojson')
    try:
        with open(arr_file, encoding='utf-8') as f:
            arr_geo = json.load(f)
        for feature in arr_geo['features']:
            feature_name = feature['properties'].get('nom', feature['properties'].get('l_ar'))
            if feature_name == arr_name:
                arr_poly = shape(feature['geometry'])
                minx, miny, maxx, maxy = arr_poly.bounds
                for _ in range(100):  # 100 essais max
                    lon = random.uniform(minx, maxx)
                    lat = random.uniform(miny, maxy)
                    pt = Point(lon, lat)
                    if arr_poly.contains(pt):
                        return f"{lat},{lon}"
    except Exception as e:
        print(f"[ARRONDISSEMENT LOC] Erreur: {e}")
    return random_localisation_paris()
'''
    SOMMAIRE :
CONFIGURATION
BABEL/INTERNATIONALIZATION
UTILITAIRES
BASE DE DONNÉES
AUTHENTIFICATION
TRAITEMENT D'IMAGES
ROUTES PRINCIPALES
ROUTES ADMIN
VISUALISATIONS ET GALERIE
CARTE
GESTION D'ERREURS
FONCTIONS UTILITAIRES ADMIN
POINT D'ENTRÉE
'''

import os
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, session, jsonify, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')
import base64
import io
import ast
from flask_babel import Babel, gettext as _
import random
import collections
import shutil
import json
from threading import Thread
from math import ceil
from shapely.geometry import shape, Point

# ==================== CONFIGURATION ====================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'votre_cle_secrete_super_securisee_changez_moi'
app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

# Créer le dossier d'upload s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static/data", exist_ok=True)

DB_PATH = os.path.join(BASE_DIR, 'db.sqlite3')


# ==================== BABEL/INTERNATIONALIZATION ====================

def get_locale():
    return session.get('lang', request.accept_languages.best_match(['en', 'fr']))


@app.context_processor
def inject_locale():
    return dict(get_locale=get_locale)


babel = Babel(app, locale_selector=get_locale)


@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


# ==================== UTILITAIRES ====================

def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def random_localisation_france():
    """Génère une localisation aléatoire autour de Paris"""
    lat = round(random.uniform(48.82, 48.90), 6)
    lon = round(random.uniform(2.25, 2.42), 6)
    return f"{lat},{lon}"


# ==================== BASE DE DONNÉES ====================

def init_db():
    """Initialise la base de données avec les tables nécessaires"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Table pour les images
        c.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                upload_date TEXT,
                annotation TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                avg_color TEXT,
                hist_rgb TEXT,
                hist_lum TEXT,
                contrast INTEGER,
                contour_count INTEGER,
                localisation TEXT
            )
        ''')

        # Table pour les utilisateurs
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        ''')

        conn.commit()

        # Créer un admin par défaut s'il n'existe pas
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        if c.fetchone()[0] == 0:
            admin_hash = generate_password_hash('admin123')
            c.execute('''
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (?, ?, 'admin', ?)
            ''', ('admin', admin_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            print("Admin par défaut créé - Login: admin, Mot de passe: admin123")


# ==================== AUTHENTIFICATION ====================

def login_required(f):
    """Décorateur pour les pages nécessitant une authentification"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Décorateur pour les pages réservées aux administrateurs"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'error')
            return redirect(url_for('login'))

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT role FROM users WHERE id = ?", (session['user_id'],))
            user = c.fetchone()

        if not user or user[0] != 'admin':
            flash('Accès réservé aux administrateurs.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
            user = c.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            session['role'] = user[2]

            # Mise à jour de la dernière connexion
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET last_login = ? WHERE id = ?",
                          (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user[0]))
                conn.commit()

            flash(f'Bienvenue {username}!', 'success')
            return redirect(url_for('about'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
            return render_template('register.html')

        password_hash = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO users (username, password_hash, role, created_at)
                    VALUES (?, ?, 'user', ?)
                ''', (username, password_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()

            flash('Inscription réussie! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            flash('Ce nom d\'utilisateur existe déjà.', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord utilisateur/admin"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Statistiques générales
        c.execute("SELECT COUNT(*) FROM images")
        total_images = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%pleine%'")
        full_bins = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%vide%'")
        empty_bins = c.fetchone()[0]

        stats = {
            'total_images': total_images,
            'full_bins': full_bins,
            'empty_bins': empty_bins
        }

        # Statistiques admin
        admin_stats = {}
        if session.get('role') == 'admin':
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = c.fetchone()[0]

            admin_stats = {
                'total_users': total_users,
                'admin_count': admin_count,
                'regular_users': total_users - admin_count
            }

    return render_template('dashboard.html', stats=stats, admin_stats=admin_stats)


# ==================== TRAITEMENT D'IMAGES ====================

def extract_metadata(filepath):
    img = Image.open(filepath).convert('RGB')
    width, height = img.size
    file_size = os.path.getsize(filepath)
    np_img = np.array(img)
    avg_color = tuple(np.mean(np_img.reshape(-1, 3), axis=0).astype(int))
    img_gray = img.convert('L')
    extrema = img_gray.getextrema()
    contrast = extrema[1] - extrema[0]
    img_cv = cv2.imread(filepath)
    img_gray_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(img_gray_cv, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(img_gray_cv, cv2.CV_64F, 0, 1, ksize=3)
    edges = cv2.magnitude(sobelx, sobely).astype(np.uint8)
    contour_count = int(np.sum(edges > 128))
    hist_rgb = [[0]*256 for _ in range(3)]
    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            hist_rgb[0][r] += 1
            hist_rgb[1][g] += 1
            hist_rgb[2][b] += 1
    hist_lum = [0]*256
    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            lum = int((r + g + b) / 3)
            hist_lum[lum] += 1
    return width, height, file_size, str(avg_color), contrast, contour_count, str(hist_rgb), str(hist_lum)


def classify_bin_automatically(avg_color, file_size, contrast, contour_count):
    """Classification automatique d'une poubelle"""
    avg_tuple = eval(avg_color)
    mean_r, mean_g, mean_b = avg_tuple
    mean_color = (mean_r + mean_g + mean_b) / 3
    file_size_Ko = file_size / 1024

    # Seuils de classification
    SEUIL_SOMBRE = 110
    SEUIL_TAILLE = 400
    SEUIL_CONTOURS = 100000

    if file_size_Ko > SEUIL_TAILLE and contour_count > SEUIL_CONTOURS:
        return "pleine_auto"
    elif mean_color < SEUIL_SOMBRE and file_size_Ko > 100:
        return "pleine_auto"
    elif file_size_Ko < 250 and contour_count < 80000:
        return "vide_auto"
    else:
        return "vide_auto"


# ==================== ROUTES PRINCIPALES ====================

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Ajout : stats arrondissements (3 premières lignes) pour la page d'accueil
    arr_stats = []
    try:
        with open(os.path.join('static', 'data', 'arrondissements.geojson'), encoding='utf-8') as f:
            arr_geo = json.load(f)
        with open(os.path.join('static', 'data', 'poubelles.json'), encoding='utf-8') as f:
            poubelles = json.load(f)
        arr_polys = []
        for feature in arr_geo['features']:
            arr_name = feature['properties'].get('nom', feature['properties'].get('l_ar'))
            arr_poly = shape(feature['geometry'])
            arr_polys.append((arr_name, arr_poly))
        arr_full_bins = {arr_name: 0 for arr_name, _ in arr_polys}
        for pb in poubelles:
            if pb.get('remplissage', '').startswith('pleine'):
                pt = Point(pb['lon'], pb['lat'])
                for arr_name, arr_poly in arr_polys:
                    if arr_poly.contains(pt):
                        arr_full_bins[arr_name] += 1
                        break
        for arr_name, _ in arr_polys:
            arr_stats.append({
                'arr': arr_name,
                'nb_pleines': arr_full_bins[arr_name]
            })
    except Exception as e:
        print(f"[INDEX] Erreur lors du calcul des stats par arrondissement: {e}")
        arr_stats = [
            {'arr': f"{i}e", 'nb_pleines': 0}
            for i in range(1, 21)
        ]
    return render_template('about.html', arr_stats=arr_stats)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload d'images (utilisateurs connectés seulement) avec compression et traitement asynchrone pour users, synchrone pour admin. Retour JSON si AJAX."""
    # Préparer la liste des arrondissements pour la barre déroulante (admin)
    arrondissements = []
    arr_file = os.path.join('static', 'data', 'arrondissements.geojson')
    try:
        with open(arr_file, encoding='utf-8') as f:
            arr_geo = json.load(f)
        for feature in arr_geo['features']:
            arr_name = feature['properties'].get('nom', feature['properties'].get('l_ar'))
            arrondissements.append(arr_name)
        arrondissements = sorted(arrondissements)
    except Exception as e:
        print(f"[UPLOAD] Erreur chargement arrondissements: {e}")
        arrondissements = []

    if request.method == 'POST':
        if 'image' not in request.files:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error='Aucun fichier sélectionné.')
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error='Aucun fichier sélectionné.')
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(request.url)

        # Pour admin : récupération du choix d'arrondissement
        selected_arr = request.form.get('arrondissement') if session.get('role') == 'admin' else None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            temp_path = filepath + '.tmp'
            file.save(temp_path)
            # Compression de l'image
            compress_image(temp_path, filepath)
            os.remove(temp_path)

            if session.get('role') == 'admin':
                try:
                    # Traitement synchrone pour admin
                    width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(filepath)
                    upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if selected_arr and selected_arr.strip():
                        localisation = random_localisation_in_arrondissement(selected_arr)
                    else:
                        localisation = random_localisation_paris()
                    auto_label = classify_bin_automatically(avg_color, file_size, contrast, contour_count)
                    with sqlite3.connect(DB_PATH) as conn:
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO images (
                                filename, upload_date, annotation, width, height,
                                file_size, avg_color, hist_rgb, hist_lum,
                                contrast, contour_count, localisation
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            filename, upload_date, auto_label, width, height,
                            file_size, avg_color, hist_rgb, hist_lum,
                            contrast, contour_count, localisation
                        ))
                        conn.commit()
                    flash('Image uploadée avec succès! Veuillez annoter.', 'success')
                    return redirect(url_for('annotate', filename=filename) + f'?auto_label={auto_label}')
                except Exception as e:
                    print(f"[ADMIN UPLOAD ERROR] {e}")
                    flash('Erreur lors du traitement de l\'image (admin): ' + str(e), 'error')
                    return redirect(url_for('upload'))
            else:
                # Traitement asynchrone pour les autres
                width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(filepath)
                upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                localisation = random_localisation_paris()  # localisation dans Paris
                auto_label = classify_bin_automatically(avg_color, file_size, contrast, contour_count)
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO images (
                            filename, upload_date, annotation, width, height,
                            file_size, avg_color, hist_rgb, hist_lum,
                            contrast, contour_count, localisation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        filename, upload_date, auto_label, width, height,
                        file_size, avg_color, hist_rgb, hist_lum,
                        contrast, contour_count, localisation
                    ))
                    conn.commit()
                # Ajout des métadonnées dans la réponse JSON AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Calcul de la luminosité moyenne (grayscale) et du contraste (écart-type)
                    img = Image.open(filepath).convert('L')
                    np_img = np.array(img)
                    luminosity = round(float(np.mean(np_img)), 2)
                    contrast_std = round(float(np.std(np_img)), 2)
                    metadata = {
                        'width': width,
                        'height': height,
                        'luminosity': luminosity,
                        'contrast': contrast_std
                    }
                    return jsonify(
                        success=True,
                        auto_label=auto_label.replace('_auto', '').capitalize(),
                        metadata=metadata
                    )
                flash('Image uploadée avec succès! Prédiction : ' + auto_label.replace('_auto','').capitalize(), 'success')
                return redirect(url_for('upload'))
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error='Type de fichier non autorisé.')
            flash('Type de fichier non autorisé.', 'error')

    return render_template('upload.html', arrondissements=arrondissements)


@app.route('/annotate/<filename>', methods=['GET', 'POST'])
@login_required
def annotate(filename):
    """Annotation d'une image"""
    auto_label = request.args.get('auto_label')

    if request.method == 'POST':
        annotation = request.form['annotation']
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            if annotation == 'annuler':
                c.execute('UPDATE images SET annotation = NULL WHERE filename = ?', (filename,))
                conn.commit()
                flash("Annotation annulée !", 'info')
                return redirect(url_for('annotate', filename=filename))
            else:
                c.execute('UPDATE images SET annotation = ? WHERE filename = ?', (annotation, filename))
                conn.commit()
        flash('Annotation sauvegardée!', 'success')
        return render_template('result.html', filename=filename, annotation=annotation)

    # --- Récupération des métadonnées depuis la BDD ---
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT width, height, contrast
            FROM images
            WHERE filename = ?
        ''', (filename,))
        row = c.fetchone()
        if row:
            width, height, contrast = row
        else:
            width, height, contrast = None, None, None

    # Calcul de la luminosité moyenne à partir du fichier image
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    luminosity = None
    try:
        img = Image.open(image_path).convert('L')
        np_img = np.array(img)
        luminosity = round(float(np.mean(np_img)), 2)
    except Exception as e:
        print(f"[ANNOTATE] Erreur calcul luminosité : {e}")

    metadata = {
        'width': width,
        'height': height,
        'contrast': contrast,
        'luminosity': luminosity
    }

    return render_template('annotate.html', filename=filename, auto_label=auto_label, metadata=metadata)


@app.route('/about', methods=['GET', 'POST'])
def about():
    message_sent = False
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        username = session.get('username', 'Anonyme')
        if subject and message:
            msg_obj = {
                'from': username,
                'subject': subject,
                'message': message,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            messages_path = os.path.join('static', 'data', 'messages_admin.json')
            if os.path.exists(messages_path):
                with open(messages_path, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            else:
                messages = []
            messages.append(msg_obj)
            with open(messages_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            message_sent = True
    # Ajout : stats arrondissements (3 premières lignes)
    arr_stats = []
    try:
        with open(os.path.join('static', 'data', 'arrondissements.geojson'), encoding='utf-8') as f:
            arr_geo = json.load(f)
        with open(os.path.join('static', 'data', 'poubelles.json'), encoding='utf-8') as f:
            poubelles = json.load(f)
        arr_polys = []
        for feature in arr_geo['features']:
            arr_name = feature['properties'].get('nom', feature['properties'].get('l_ar'))
            arr_poly = shape(feature['geometry'])
            arr_polys.append((arr_name, arr_poly))
        arr_full_bins = {arr_name: 0 for arr_name, _ in arr_polys}
        for pb in poubelles:
            if pb.get('remplissage', '').startswith('pleine'):
                pt = Point(pb['lon'], pb['lat'])
                for arr_name, arr_poly in arr_polys:
                    if arr_poly.contains(pt):
                        arr_full_bins[arr_name] += 1
                        break
        for arr_name, _ in arr_polys:
            arr_stats.append({
                'arr': arr_name,
                'nb_pleines': arr_full_bins[arr_name]
            })
    except Exception as e:
        print(f"[ABOUT] Erreur lors du calcul des stats par arrondissement: {e}")
        arr_stats = [
            {'arr': f"{i}e", 'nb_pleines': 0}
            for i in range(1, 21)
        ]
    return render_template('about.html', message_sent=message_sent, arr_stats=arr_stats)


# ==================== ROUTES ADMIN ====================

@app.route('/admin/users')
@admin_required
def admin_users():
    """Page de gestion des utilisateurs"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, username, role, created_at, last_login
            FROM users
            ORDER BY created_at DESC
        """)
        users = c.fetchall()
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
    return render_template('admin/users.html', users=users, admin_count=admin_count)

@app.route('/admin/create_admin', methods=['POST'])
@admin_required
def create_admin():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not password:
        flash('Nom d\'utilisateur et mot de passe requis.', 'danger')
        return redirect(url_for('admin_users'))
    if len(password) < 6:
        flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
        return redirect(url_for('admin_users'))
    password_hash = generate_password_hash(password)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (?, ?, 'admin', ?)
            ''', (username, password_hash, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        flash('Administrateur créé avec succès.', 'success')
    except sqlite3.IntegrityError:
        flash('Ce nom d\'utilisateur existe déjà.', 'danger')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    # Ne pas permettre de supprimer son propre compte
    if session['user_id'] == user_id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin_users'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            flash('Utilisateur introuvable.', 'danger')
            return redirect(url_for('admin_users'))
        if user[0] == 'admin':
            c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = c.fetchone()[0]
            if admin_count <= 1:
                flash('Impossible de supprimer le dernier administrateur.', 'danger')
                return redirect(url_for('admin_users'))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    flash('Utilisateur supprimé avec succès.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/promote_user/<int:user_id>')
@admin_required
def promote_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
        conn.commit()
    flash('Utilisateur promu administrateur avec succès.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/demote_user/<int:user_id>')
@admin_required
def demote_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Vérifier qu'il reste au moins un admin
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        if admin_count <= 1:
            flash('Impossible de rétrograder le dernier administrateur.', 'danger')
        else:
            c.execute("UPDATE users SET role = 'user' WHERE id = ?", (user_id,))
            conn.commit()
            flash('Utilisateur rétrogradé avec succès.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/bdd')
@admin_required
def afficher_bdd():
    """Affichage de la base de données (admin seulement) avec pagination"""
    page = int(request.args.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM images")
        total_rows = c.fetchone()[0]
        c.execute("SELECT * FROM images ORDER BY upload_date DESC LIMIT ? OFFSET ?", (per_page, offset))
        rows = c.fetchall()
        colonnes = [description[0] for description in c.description]
    processed_rows = []
    for row in rows:
        row_dict = dict(row)
        for col_name, title in [('hist_rgb', 'Histogramme RGB'), ('hist_lum', 'Histogramme Luminance')]:
            if col_name in row_dict and row_dict[col_name]:
                try:
                    data = ast.literal_eval(row_dict[col_name])
                    img = plot_histogram(data, title)
                    row_dict[col_name] = f'<img src="data:image/png;base64,{img}"/>'
                except Exception as e:
                    print(f"[ADMIN BDD] Erreur d'affichage pour {col_name} (valeur={row_dict[col_name]}): {e}")
                    row_dict[col_name] = "Erreur d'affichage"
        processed_rows.append(row_dict)
    total_pages = max(ceil(total_rows / per_page), 1)
    return render_template('admin/bdd.html', rows=processed_rows, colonnes=colonnes, page=page, total_pages=total_pages)


@app.route('/admin/messages')
@admin_required
def admin_messages():
    messages_path = os.path.join('static', 'data', 'messages_admin.json')
    if os.path.exists(messages_path):
        with open(messages_path, 'r', encoding='utf-8') as f:
            messages = json.load(f)
    else:
        messages = []
    return render_template('admin/messages.html', messages=messages)


# ==================== VISUALISATIONS ET GALERIE ====================

def plot_histogram(data, title=''):
    """Génère un histogramme sous forme d'image base64"""
    fig, ax = plt.subplots(figsize=(4, 2))
    if isinstance(data[0], list):  # RGB
        colors = ['red', 'green', 'blue']
        for i, color in enumerate(colors):
            ax.plot(data[i], color=color, linewidth=0.7)
    else:
        ax.plot(data, color='black', linewidth=0.7)
    ax.set_title(title)
    ax.axis('off')

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


@app.route('/visualisations')
@login_required
def stats():
    """Visualisations et statistiques"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM images")
        total_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%pleine%'")
        full_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%vide%'")
        empty_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation IS NULL OR annotation = ''")
        non_labelled_annotations = c.fetchone()[0]

    # --- Ajout : stats par arrondissement basées sur les données de la carte ---
    arr_stats = []
    try:
        # Charger les arrondissements
        with open(os.path.join('static', 'data', 'arrondissements.geojson'), encoding='utf-8') as f:
            arr_geo = json.load(f)
        # Charger les poubelles
        with open(os.path.join('static', 'data', 'poubelles.json'), encoding='utf-8') as f:
            poubelles = json.load(f)
        # Préparer les polygones
        arr_polys = []
        for feature in arr_geo['features']:
            arr_name = feature['properties'].get('nom', feature['properties'].get('l_ar'))
            arr_poly = shape(feature['geometry'])
            arr_polys.append((arr_name, arr_poly))
        # Compter les poubelles pleines par arrondissement
        arr_full_bins = {arr_name: 0 for arr_name, _ in arr_polys}
        for pb in poubelles:
            if pb.get('remplissage', '').startswith('pleine'):
                pt = Point(pb['lon'], pb['lat'])
                for arr_name, arr_poly in arr_polys:
                    if arr_poly.contains(pt):
                        arr_full_bins[arr_name] += 1
                        break
        # Construire arr_stats
        for arr_name, _ in arr_polys:
            arr_stats.append({
                'arr': arr_name,
                'nb_pleines': arr_full_bins[arr_name]
            })
    except Exception as e:
        print(f"[VISU] Erreur lors du calcul des stats par arrondissement: {e}")
        # Fallback: ancienne méthode
        arr_stats = [
            {'arr': f"{i}e", 'nb_pleines': 0}
            for i in range(1, 21)
        ]

    # Affichage du graphique donut pour le nombre d'annotations
    donut_values = [total_annotations, 720 - total_annotations]  # 720 est le nombre total d'images attendues
    donut_labels = ["Annotations actuelles", "Annotations possibles"]       
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.pie(donut_values, labels=donut_labels, autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#FFC107'])
    ax.set_title("Nombre total d'images uploadées")
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_base64_nombre = "data:image/png;base64," + base64.b64encode(buf.read()).decode('utf-8')



    #affichage du graphique en camembert pour la repartition des annotations 
    data = [full_annotations,empty_annotations]
    labels=["pleines","vides"]

    #graphique 
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.pie(data,labels=labels,autopct='%1.1f%%')
    ax.set_title("Répartitions des annotations")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_base64 = "data:image/png;base64," + base64.b64encode(buf.read()).decode('utf-8')

    #affichage de la distribution des tailles des fichiers 
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT file_size, COUNT(*) as count
    FROM images
    WHERE file_size IS NOT NULL
    GROUP BY file_size
    ORDER BY file_size
""")
    
    rows = cursor.fetchall()

    # Formatage pour affichage
    size_files = [file_size for file_size, _ in rows]
    occ_size_files = [count for _, count in rows]

    #graphique de la distribution des tailles de fichiers

    #graphique en barres     
    fig, ax = plt.subplots(figsize=(4, 2))
    barColors = ['#4CAF50'] * len(size_files)

    # Utiliser des indices pour les x pour éviter les problèmes de taille
    # et pour que les barres soient bien espacées
    indices = list(range(len(size_files)))
    ax.bar(indices, occ_size_files, color=barColors)

    # Affichage des labels de tailles converties en Ko
    ax.set_xticks(indices)
    ax.set_xticklabels([f"{size/1024:.1f} Ko" for size in size_files], rotation=45, ha='right')

    ax.set_xlabel('Taille des fichiers (Ko)')   
    ax.set_ylabel('Nombre de fichiers')
    ax.set_title('Distribution des tailles de fichiers')

    #sauvegarde de l'image dans un buffer
    buf = io.BytesIO()
    plt.tight_layout()      
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)

    img_base64_distribution = "data:image/png;base64," + base64.b64encode (buf.read()).decode('utf-8')
    

    return render_template('visualisations.html',
                           total_annotations=total_annotations,
                           full_annotations=full_annotations,
                           empty_annotations=empty_annotations,
                           non_labelled_annotations=non_labelled_annotations,
                           image_base64=img_base64,
                           size_files=size_files,
                           occ_size_files=occ_size_files,
                           img_base64_distribution=img_base64_distribution,
                           img_base64_nombre=img_base64_nombre,
                           arr_stats=arr_stats)


@app.route('/gallery')
@login_required
def gallery():
    """Galerie d'images avec pagination"""
    page = int(request.args.get('page', 1))
    per_page = 5
    offset = (page - 1) * per_page
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%vide%'")
        total_vides = c.fetchone()[0]
        c.execute("SELECT filename, upload_date FROM images WHERE annotation LIKE '%vide%' ORDER BY upload_date DESC LIMIT ? OFFSET ?", (per_page, offset))
        vides = c.fetchall()
        c.execute("SELECT COUNT(*) FROM images WHERE annotation LIKE '%pleine%'")
        total_pleines = c.fetchone()[0]
        c.execute("SELECT filename, upload_date FROM images WHERE annotation LIKE '%pleine%' ORDER BY upload_date DESC LIMIT ? OFFSET ?", (per_page, offset))
        pleines = c.fetchall()
        c.execute("SELECT COUNT(*) FROM images WHERE annotation IS NULL OR annotation = ''")
        total_non_label = c.fetchone()[0]
        c.execute("SELECT filename, upload_date FROM images WHERE annotation IS NULL OR annotation = '' ORDER BY upload_date DESC LIMIT ? OFFSET ?", (per_page, offset))
        non_labelisees = c.fetchall()
    total_pages = max(ceil(max(total_vides, total_pleines, total_non_label) / per_page), 1)
    return render_template('gallery.html', vides=vides, pleines=pleines, non_labelisees=non_labelisees, page=page, total_pages=total_pages)


# ==================== CARTE ====================

def random_localisation_paris():
    """Génère une localisation aléatoire à l'intérieur de la zone Paris intramuros réduite."""
    PARIS_MIN_LAT = 48.84
    PARIS_MAX_LAT = 48.89
    PARIS_MIN_LON = 2.28
    PARIS_MAX_LON = 2.41
    lat = round(random.uniform(PARIS_MIN_LAT, PARIS_MAX_LAT), 6)
    lon = round(random.uniform(PARIS_MIN_LON, PARIS_MAX_LON), 6)
    return f"{lat},{lon}"


def generer_json_poubelles():
    """Génère le fichier JSON pour la carte (utilise la localisation stockée en base, qui est déjà dans Paris)"""
    FINAL_JSON_PATH = os.path.join(BASE_DIR, 'static', 'data', 'poubelles.json')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT localisation, annotation, upload_date
        FROM images
        WHERE localisation IS NOT NULL AND annotation IS NOT NULL AND localisation != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    points = []
    for loc, remplissage, date in rows:
        try:
            lat_str, lon_str = loc.split(",")
            lat = float(lat_str.strip())
            lon = float(lon_str.strip())
        except Exception as e:
            print(f"[WARN] Localisation mal formée ignorée: '{loc}' ({e})")
            continue
        points.append({
            "lat": lat,
            "lon": lon,
            "remplissage": remplissage.lower() if remplissage else "",
            "date": date
        })

    with open(FINAL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=4)


@app.route("/map")
@login_required
def map_view():
    """Affichage de la carte"""
    generer_json_poubelles()
    return render_template("map.html")


# ==================== GESTION D'ERREURS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500


# ==================== FONCTIONS UTILITAIRES ADMIN ====================

def batch_upload_images():
    """Upload en lot des images d'entraînement (fonction utilitaire)"""
    base_dirs = [
        ('Data/train/with_label/dirty', 'dirty'),
        ('Data/train/with_label/clean', 'clean')
    ]

    for dir_path, label_hint in base_dirs:
        full_dir = os.path.join(os.getcwd(), dir_path)
        if not os.path.exists(full_dir):
            print(f"Le dossier {full_dir} n'existe pas.")
            continue

        for fname in os.listdir(full_dir):
            if not allowed_file(fname):
                continue

            src_path = os.path.join(full_dir, fname)
            dest_path = os.path.join(UPLOAD_FOLDER, fname)

            if not os.path.exists(dest_path):
                shutil.copy(src_path, dest_path)

            # Extraction des features et sauvegarde
            width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(
                dest_path)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            localisation = random_localisation_france()

            auto_label = classify_bin_automatically(avg_color, file_size, contrast, contour_count)
            annotation = f"{auto_label}|{label_hint}"

            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO images (
                        filename, upload_date, annotation, width, height,
                        file_size, avg_color, hist_rgb, hist_lum,
                        contrast, contour_count, localisation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fname, upload_date, annotation, width, height,
                    file_size, avg_color, hist_rgb, hist_lum,
                    contrast, contour_count, localisation
                ))
                conn.commit()

            print(f"{fname} : {annotation}")


def compress_image(input_path, output_path, quality=70, max_size=(1024, 1024)):
    """Compresse et redimensionne l'image pour optimiser la taille."""
    img = Image.open(input_path)
    # Utilise LANCZOS (équivalent moderne d'ANTIALIAS)
    img.thumbnail(max_size, Image.LANCZOS)
    img.save(output_path, optimize=True, quality=quality)
    img.close()


# ==================== POINT D'ENTRÉE ====================

if __name__ == '__main__':
    init_db()
    print("Base de données initialisée.")
    print("Admin par défaut - Login: admin, Mot de passe: admin123")
    app.run(debug=True)