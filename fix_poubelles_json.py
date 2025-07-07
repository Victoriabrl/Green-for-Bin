import json
import os
import re

# Chemin du fichier à corriger
json_path = os.path.join('static', 'data', 'poubelles.json')

# Lecture du fichier et suppression des marqueurs de conflit
with open(json_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Supprime les lignes de conflit git (>>>>>, <<<<<, =====)
clean_lines = [line for line in lines if not re.match(r'^(>{2,}|<{2,}|={2,})', line.strip())]
content = ''.join(clean_lines)

# Si le fichier n'est pas du JSON valide, essaye de l'évaluer comme un dict/list Python puis le réécrit en JSON
try:
    # Essaye de charger comme JSON (cas normal)
    data = json.loads(content)
except Exception:
    # Si erreur, essaye d'évaluer comme un objet Python (ex: guillemets simples)
    import ast
    data = ast.literal_eval(content)

# Réécriture au format JSON valide
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print('Fichier poubelles.json nettoyé et corrigé au format JSON standard.')
