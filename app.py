import os
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template, session
from werkzeug.utils import secure_filename
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import base64
import io
import ast  
from flask_babel import Babel, gettext as _
import random
import ast  # utile si avg_color est stocké comme chaîne de texte dans la base

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'votre_cle_secrete'  # Nécessaire pour les sessions
app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

#CHANGEMENT DE LANGUE
# Fonction pour déterminer la langue
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

# Créer le dossier d'upload s’il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Vérifie le type de fichier
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_db():
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                upload_date TEXT,
                annotation TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                avg_color Text,
                hist_rgb TEXT,
                hist_lum TEXT,
                contrast INTEGER,
                contour_count INTEGER,
                localisation TEXT
            )
        ''')
        conn.commit()

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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(filepath)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            localisation = random_localisation_france()

            # --- Début du label automatique adapté à tes données ---
            avg_tuple = eval(avg_color)  # ex: (123, 120, 110)
            mean_r, mean_g, mean_b = avg_tuple
            mean_color = (mean_r + mean_g + mean_b) / 3
            file_size_Ko = file_size / 1024  # conversion octets -> Ko
            if file_size_Ko > 400 and contour_count > 100000:
                auto_label = "pleine_auto"
            elif mean_color < 110 and file_size_Ko > 100:
                auto_label = "pleine_auto"
            elif file_size_Ko < 250 and contour_count < 80000:
                auto_label = "vide_auto"
            else:
                auto_label = "vide_auto"
            # --- Fin du label automatique ---

            with sqlite3.connect('db.sqlite3') as conn:
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
            return redirect(url_for('annotate', filename=filename, auto_label=auto_label))
    return render_template('index.html', filename=None)




def plot_histogram(data, title=''):
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

@app.route('/bdd')
def afficher_bdd():
    with sqlite3.connect('db.sqlite3') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM images")
        rows = c.fetchall()
        colonnes = [description[0] for description in c.description]

    processed_rows = []
    for row in rows:
        row_dict = dict(row)
        print("DEBUG avg_color:", row_dict['avg_color'], type(row_dict['avg_color']))

        # ✅ Conversion avg_color en tuple de int natifs
        if 'avg_color' in row_dict and row_dict['avg_color']:
            try:
                avg_str = row_dict['avg_color']
                
                # Évalue la chaîne même si elle contient np.int64()
                avg_tuple = eval(avg_str, {"np": np})  # ⚠️ safe car contexte limité à numpy

                row_dict['avg_color'] = tuple(int(x) for x in avg_tuple)
            except Exception as e:
                print("Erreur avg_color:", e)
                row_dict['avg_color'] = "Erreur"

        # ✅ Remplacement des histogrammes texte par images
        for col_name, title in [('hist_rgb', 'Histogramme RGB'), ('hist_lum', 'Histogramme Luminance')]:
            if col_name in row_dict and row_dict[col_name]:
                try:
                    data = ast.literal_eval(row_dict[col_name])
                    img = plot_histogram(data, title)
                    row_dict[col_name] = f'<img src="data:image/png;base64,{img}"/>'
                except Exception:
                    row_dict[col_name] = "Erreur d'affichage"

        processed_rows.append(row_dict)

    return render_template('bdd.html', rows=processed_rows, colonnes=colonnes)



# Route pour visualiser les statistiques
@app.route('/visualisations')
def stats():
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM images")
        total_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation = 'pleine'")
        full_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation = 'vide'")
        empty_annotations = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM images WHERE annotation IS NULL OR annotation = ''")
        non_labelled_annotations = c.fetchone()[0]

    return render_template('visualisations.html',
                           total_annotations=total_annotations,
                           full_annotations=full_annotations,
                           empty_annotations=empty_annotations,
                           non_labelled_annotations=non_labelled_annotations)


# Route pour annoter une image
@app.route('/annotate/<filename>', methods=['GET', 'POST'])
def annotate(filename):
    auto_label = request.args.get('auto_label')  # récupère le label automatique
    if request.method == 'POST':
        annotation = request.form['annotation']
        with sqlite3.connect('db.sqlite3') as conn:
            c = conn.cursor()
            c.execute('UPDATE images SET annotation = ? WHERE filename = ?', (annotation, filename))
            conn.commit()
        return render_template('result.html', filename=filename, annotation=annotation)

    return render_template('annotate.html', filename=filename, auto_label=auto_label)


# Route pour la galerie
@app.route('/gallery')
def gallery():
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()

        # Images annotées comme "vide"
        c.execute("SELECT filename, upload_date FROM images WHERE annotation = 'vide'")
        vides = c.fetchall()

        # Images annotées comme "pleine"
        c.execute("SELECT filename, upload_date FROM images WHERE annotation = 'pleine'")
        pleines = c.fetchall()

        # Images non annotées (NULL ou vide)
        c.execute("SELECT filename, upload_date FROM images WHERE annotation IS NULL OR annotation = ''")
        non_labelisees = c.fetchall()

    return render_template('gallery.html', vides=vides, pleines=pleines, non_labelisees=non_labelisees)



def random_localisation_france():
    # Paris centre : lat 48.8566, lon 2.3522
    # Rayon ~10 km autour du centre (environ 0.09° latitude/longitude)
    lat = round(random.uniform(48.82, 48.90), 6)
    lon = round(random.uniform(2.25, 2.42), 6)
    return f"{lat},{lon}"

def batch_upload_images():
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
            # Copie l'image dans le dossier d'upload
            dest_path = os.path.join(UPLOAD_FOLDER, fname)
            if not os.path.exists(dest_path):
                import shutil
                shutil.copy(src_path, dest_path)
            # Extraction des features
            width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(dest_path)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            localisation = random_localisation_france()
            avg_tuple = eval(avg_color)
            mean_r, mean_g, mean_b = avg_tuple
            mean_color = (mean_r + mean_g + mean_b) / 3
            file_size_Ko = file_size / 1024

            # --- Classification automatique avancée ---
            SEUIL_SOMBRE = 100
            SEUIL_TAILLE = 500
            SEUIL_CONTRASTE = 80
            SEUIL_CONTOURS = 10000

            if mean_color < SEUIL_SOMBRE and file_size_Ko > SEUIL_TAILLE and contrast > SEUIL_CONTRASTE and contour_count > SEUIL_CONTOURS:
                auto_label = "pleine_auto"
            elif mean_color > 180 and file_size_Ko < 200 and contrast < 50 and contour_count < 5000:
                auto_label = "vide_auto"
            elif mean_color < SEUIL_SOMBRE and contrast > SEUIL_CONTRASTE:
                auto_label = "pleine_auto"
            elif mean_color > 150 and contrast < 60:
                auto_label = "vide_auto"
            else:
                auto_label = "vide_auto"

            # Ajoute le vrai label pour analyse (dirty/clean)
            annotation = f"{auto_label}|{label_hint}"

            with sqlite3.connect('db.sqlite3') as conn:
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
            print(f"{fname} : {annotation} | mean_color={mean_color:.1f} | file_size_Ko={file_size_Ko:.1f} | contrast={contrast} | contours={contour_count}")

# Pour lancer le batch automatiquement au démarrage (décommente la ligne ci-dessous si tu veux)
# batch_upload_images()

def analyse_dirty_clean():
    base_dirs = [
        ('Data/train/with_label/dirty', 'pleine'),
        ('Data/train/with_label/clean', 'vide')
    ]
    stats = {'pleine': [], 'vide': []}
    for dir_path, label in base_dirs:
        full_dir = os.path.join(os.getcwd(), dir_path)
        if not os.path.exists(full_dir):
            print(f"Le dossier {full_dir} n'existe pas.")
            continue
        for fname in os.listdir(full_dir):
            if not allowed_file(fname):
                continue
            src_path = os.path.join(full_dir, fname)
            width, height, file_size, avg_color, contrast, contour_count, hist_rgb, hist_lum = extract_metadata(src_path)
            avg_tuple = eval(avg_color)
            mean_r, mean_g, mean_b = avg_tuple
            mean_color = (mean_r + mean_g + mean_b) / 3
            file_size_Ko = file_size / 1024
            stats[label].append({
                'filename': fname,
                'mean_color': mean_color,
                'file_size_Ko': file_size_Ko,
                'contrast': contrast,
                'contour_count': contour_count
            })
            print(f"{label} | {fname} | mean_color={mean_color:.1f} | file_size_Ko={file_size_Ko:.1f} | contrast={contrast} | contours={contour_count}")

    # Affiche les moyennes pour chaque classe
    for label in ['pleine', 'vide']:
        if stats[label]:
            mean_color = np.mean([x['mean_color'] for x in stats[label]])
            file_size_Ko = np.mean([x['file_size_Ko'] for x in stats[label]])
            contrast = np.mean([x['contrast'] for x in stats[label]])
            contour_count = np.mean([x['contour_count'] for x in stats[label]])
            print(f"\n--- {label.upper()} ---")
            print(f"Moyenne mean_color : {mean_color:.1f}")
            print(f"Moyenne file_size_Ko : {file_size_Ko:.1f}")
            print(f"Moyenne contrast : {contrast:.1f}")
            print(f"Moyenne contour_count : {contour_count:.1f}")
        else:
            print(f"Aucune image pour {label}")

# Pour lancer l'analyse (décommente la ligne ci-dessous pour lancer une fois)
# analyse_dirty_clean()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
