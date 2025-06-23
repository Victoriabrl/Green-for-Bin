import os
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from PIL import Image

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Créer le dossier d'upload s’il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Vérifie le type de fichier
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Créer la BDD si elle n'existe pas
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
                avg_color INTEGER,
                contrast INTEGER,
                contour_count INTEGER
            )
        ''')
        conn.commit()


# Extraire les métadonnées
def extract_metadata(filepath):
    img = Image.open(filepath).convert('RGB')
    width, height = img.size
    file_size = os.path.getsize(filepath)

    # Moyenne des couleurs
    np_img = np.array(img)
    avg_color = tuple(np.mean(np_img.reshape(-1, 3), axis=0).astype(int))

    # Contraste avec PIL
    img_gray = img.convert('L')
    extrema = img_gray.getextrema()
    contrast = extrema[1] - extrema[0]

    # Contours avec OpenCV
    img_cv = cv2.imread(filepath)
    img_gray_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(img_gray_cv, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(img_gray_cv, cv2.CV_64F, 0, 1, ksize=3)
    edges = cv2.magnitude(sobelx, sobely)
    edges = np.uint8(edges)
    contour_count = int(np.sum(edges > 128))

    return width, height, file_size, str(avg_color), contrast, contour_count

# Route principale pour l'upload d'image)
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

            # Extraire les nouvelles métadonnées
            width, height, file_size, avg_color, contrast, contour_count = extract_metadata(filepath)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with sqlite3.connect('db.sqlite3') as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO images (
                        filename, upload_date, annotation, width, height, 
                        file_size, avg_color, contrast, contour_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (filename, upload_date, '', width, height, file_size, avg_color, contrast, contour_count))
                conn.commit()

            return redirect(url_for('annotate', filename=filename))

    return render_template('index.html', filename=None)

# Route pour visualiser les statistiques
@app.route('/visualisations')
def stats():
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        
        # Nombre total d'annotations (nombre total d'entrées dans la table)
        c.execute("SELECT COUNT(*) FROM images")
        total_annotations = c.fetchone()[0]

        # Nombre d'annotations pleines 
        c.execute("SELECT COUNT(*) FROM images WHERE annotation IS NOT NULL AND annotation = 'pleine'")
        full_annotations = c.fetchone()[0]

        # Nombre d'annotations vides 
        c.execute("SELECT COUNT(*) FROM images WHERE annotation IS NOT NULL AND annotation = 'vide'")
        empty_annotations = c.fetchone()[0]

    return render_template('visualisations.html',
                           total_annotations=total_annotations,
                           full_annotations=full_annotations,
                           empty_annotations=empty_annotations)

# Route pour annoter une image
@app.route('/annotate/<filename>', methods=['GET', 'POST'])
def annotate(filename):
    if request.method == 'POST':
        annotation = request.form['annotation']
        with sqlite3.connect('db.sqlite3') as conn:
            c = conn.cursor()
            c.execute('UPDATE images SET annotation = ? WHERE filename = ?', (annotation, filename))
            conn.commit()
        return render_template('result.html', filename=filename, annotation=annotation)

    return render_template('annotate.html', filename=filename)


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



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
