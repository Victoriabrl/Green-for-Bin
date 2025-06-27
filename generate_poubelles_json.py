import sqlite3
import json
import os

# Chemin de la base de données
DB_PATH = "db.sqlite3"

# Chemin du fichier JSON à générer
OUTPUT_JSON_PATH = "data/poubelles.json"

# Crée le dossier s'il n'existe pas
os.makedirs("data", exist_ok=True)

# Connexion à la base
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Requête pour récupérer les données utiles
cursor.execute("""
    SELECT localisation, annotation, upload_date
    FROM images
    WHERE localisation IS NOT NULL AND annotation IS NOT NULL
""")

rows = cursor.fetchall()
conn.close()

# Traitement des résultats
points = []
for loc, remplissage, date in rows:
    try:
        lat_str, lon_str = loc.split(",")
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
    except Exception:
        continue  # Ignore les lignes incorrectes

    points.append({
        "lat": lat,
        "lon": lon,
        "remplissage": remplissage.lower(),
        "date": date
    })

# Sauvegarde dans un fichier JSON
with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(points, f, ensure_ascii=False, indent=4)

print(f"✅ Fichier JSON généré avec {len(points)} points : {OUTPUT_JSON_PATH}")
