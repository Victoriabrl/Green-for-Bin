import sqlite3

DB_PATH = 'db.sqlite3'

# Colonnes à ajouter
COLUMNS = [
    ('std_h', 'REAL'),
    ('std_s', 'REAL'),
    ('std_v', 'REAL'),
]

def add_column_if_missing(cursor, table, col_name, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if col_name not in columns:
        print(f"Ajout de la colonne {col_name} à la table {table}...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
    else:
        print(f"Colonne {col_name} déjà présente.")

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for col_name, col_type in COLUMNS:
        add_column_if_missing(c, 'images', col_name, col_type)
    conn.commit()
    conn.close()
    print("Migration terminée.")

if __name__ == '__main__':
    main()
