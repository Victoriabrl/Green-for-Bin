import os
from flask import Flask, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
from PIL import Image
import numpy as np

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
                avg_color TEXT
            )
        ''')
        conn.commit()


# Extraire les métadonnées
def extract_metadata(filepath):
    img = Image.open(filepath)
    width, height = img.size
    file_size = os.path.getsize(filepath)
    np_img = np.array(img)
    avg_color = tuple(np.mean(np_img.reshape(-1, 3), axis=0).astype(int))
    return width, height, file_size, str(avg_color)


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

            width, height, file_size, avg_color = extract_metadata(filepath)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with sqlite3.connect('db.sqlite3') as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO images (filename, upload_date, annotation, width, height, file_size, avg_color)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (filename, upload_date, '', width, height, file_size, avg_color))
                conn.commit()

            return redirect(url_for('annotate', filename=filename))

    return render_template('index.html', filename=None)



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

@app.route('/gallery')
def gallery():
    with sqlite3.connect('db.sqlite3') as conn:
        c = conn.cursor()
        c.execute("SELECT filename, upload_date FROM images WHERE annotation = 'vide'")
        vides = c.fetchall()
        c.execute("SELECT filename, upload_date FROM images WHERE annotation = 'pleine'")
        pleines = c.fetchall()
    return render_template('gallery.html', vides=vides, pleines=pleines)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
