import os
from auto_label import is_poubelle_pleine_v3

def test_folder(folder_path):
    count_full = 0
    count_empty = 0
    total = 0
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            total += 1
            path = os.path.join(folder_path, fname)
            result = is_poubelle_pleine_v3(path)
            if result == "dirty":
                count_full += 1
            elif result == "clean":
                count_empty += 1
    print(f"\nRésultats pour {folder_path}:")
    print(f"  Total images                : {total}")
    print(f"  Détectées comme pleines     : {count_full}")
    print(f"  Détectées comme vides       : {count_empty}")

if __name__ == "__main__":
    test_folder(r"Data\test\dirty_no_label")
    test_folder(r"Data\test\clean_no_label")
    result = is_poubelle_pleine_v3(path)
    if (expected_label == "vide" and result != "vide") or (expected_label == "pleine" and result != "pleine"):
        print(f"Erreur sur {fname} : détecté {result}")