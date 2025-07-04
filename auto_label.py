def classify_bin_custom(image_path, use_std_h=True, use_std_s=True, use_std_v=True, seuil_h=50, seuil_s=34, seuil_v=49):
    image = cv2.imread(image_path)
    if image is None:
        print(f"{image_path} : image introuvable.")
        return None

    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_green = np.array([60, 40, 40])
    upper_green = np.array([120, 255, 255])
    mask_green = cv2.inRange(hsv_image, lower_green, upper_green)
    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print(f"{os.path.basename(image_path)} : Contour vert non détecté")
        return "erreur"
    largest_contour = max(contours, key=cv2.contourArea)
    mask_bin = np.zeros_like(mask_green)
    cv2.drawContours(mask_bin, [largest_contour], -1, 255, cv2.FILLED)
    kernel = np.ones((15, 15), np.uint8)
    mask_dilated = cv2.dilate(mask_bin, kernel, iterations=1)
    mask_surrounding = cv2.bitwise_xor(mask_dilated, mask_bin)
    surrounding_pixels = cv2.bitwise_and(image, image, mask=mask_surrounding)
    hsv_surrounding = cv2.cvtColor(surrounding_pixels, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_surrounding)
    h_vals = h[mask_surrounding == 255]
    s_vals = s[mask_surrounding == 255]
    v_vals = v[mask_surrounding == 255]
    std_h = float(np.std(h_vals))
    std_s = float(np.std(s_vals))
    std_v = float(np.std(v_vals))

    
    # Logique personnalisée selon les choix utilisateur
    conditions = []
    if use_std_h:
        conditions.append(std_h > seuil_h)
    if use_std_s:
        conditions.append(std_s > seuil_s)
    if use_std_v:
        conditions.append(std_v > seuil_v)
    # Si au moins 2 conditions sur 3 sont vraies (ou majorité), on considère "pleine"
    if sum(conditions) >= max(1, (use_std_h + use_std_s + use_std_v) // 2 + 1):
        label = "pleine"
    else:
        label = "vide"
    return label
import cv2
import numpy as np
import os

def classify_bin(image_path, debug=False):
    image = cv2.imread(image_path)
    if image is None:
        print(f"{image_path} : image introuvable.")
        return None

    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 1. Détection des pixels verts (contour poubelle)
    lower_green = np.array([60, 40, 40])
    upper_green = np.array([120, 255, 255])
    mask_green = cv2.inRange(hsv_image, lower_green, upper_green)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print(f"{os.path.basename(image_path)} : Contour vert non détecté")
        return

    largest_contour = max(contours, key=cv2.contourArea)

    # 2. Créer un masque de la poubelle (contour plein)
    mask_bin = np.zeros_like(mask_green)
    cv2.drawContours(mask_bin, [largest_contour], -1, 255, cv2.FILLED)

    # 3. Dilater le contour pour créer une "zone autour" (5 à 10 pixels de large)
    kernel = np.ones((15, 15), np.uint8)
    mask_dilated = cv2.dilate(mask_bin, kernel, iterations=1)
    mask_surrounding = cv2.bitwise_xor(mask_dilated, mask_bin)

    # 4. Extraire les pixels autour de la poubelle
    surrounding_pixels = cv2.bitwise_and(image, image, mask=mask_surrounding)

    # 5. Analyse de la couleur dans la zone autour
    hsv_surrounding = cv2.cvtColor(surrounding_pixels, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_surrounding)

    h_vals = h[mask_surrounding == 255]
    s_vals = s[mask_surrounding == 255]
    v_vals = v[mask_surrounding == 255]

    # 6. Calcul de l’hétérogénéité (écarts types)
    std_h = np.std(h_vals)
    std_s = np.std(s_vals)
    std_v = np.std(v_vals)

    # 7. Seuils déterminés manuellement
    seuil_h = 40
    seuil_s = 29
    seuil_v = 44

    if (
        (std_v > seuil_v and (std_h > seuil_h or std_s > seuil_s))
        or
        ((std_h < seuil_h and std_v > seuil_v)
        or
        (std_s > seuil_s and std_v > seuil_v))
        or
        (std_h > seuil_h and std_v < seuil_v)
        or
        (std_s > seuil_s and std_v < seuil_v)
    ):
        print(f"{os.path.basename(image_path)} : Poubelle pleine (dépôts autour détectés)")
        return "pleine"
    else:
        print(f"{os.path.basename(image_path)} : Poubelle vide (pas de dépôt autour)")
        return "vide"