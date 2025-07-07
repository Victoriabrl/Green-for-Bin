def classify_bin(image_path, debug=False):
    import cv2
    import numpy as np
    import os

    image = cv2.imread(image_path)
    if image is None:
        print(f"{image_path} : image introuvable.")
        return "erreur"

    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 1. Détection des pixels verts (contour poubelle)
    lower_green = np.array([60, 40, 40])
    upper_green = np.array([120, 255, 255])
    mask_green = cv2.inRange(hsv_image, lower_green, upper_green)

    contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print(f"{os.path.basename(image_path)} : Contour vert non détecté")
        return "erreur"

    largest_contour = max(contours, key=cv2.contourArea)

    # 2. Créer un masque de la poubelle (contour plein)
    mask_bin = np.zeros_like(mask_green)
    cv2.drawContours(mask_bin, [largest_contour], -1, 255, cv2.FILLED)

    # 3. Dilater le contour pour créer une "zone autour" (15x15 kernel)
    kernel = np.ones((15, 15), np.uint8)
    mask_dilated = cv2.dilate(mask_bin, kernel, iterations=1)
    mask_surrounding = cv2.bitwise_xor(mask_dilated, mask_bin)

    # 4. Extraire les pixels autour de la poubelle
    surrounding_pixels = cv2.bitwise_and(image, image, mask=mask_surrounding)

    # 5. Analyse HSV dans la zone autour
    hsv_surrounding = cv2.cvtColor(surrounding_pixels, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_surrounding)

    h_vals = h[mask_surrounding == 255]
    s_vals = s[mask_surrounding == 255]
    v_vals = v[mask_surrounding == 255]

    # 6. Calcul de l’hétérogénéité (écarts types) sur la zone entourante
    std_h = np.std(h_vals)
    std_s = np.std(s_vals)
    std_v = np.std(v_vals)

    # 7. Calcul de luminance et contraste sur la zone entourante
    gray_surrounding = cv2.cvtColor(surrounding_pixels, cv2.COLOR_BGR2GRAY)
    mean_lum = float(np.mean(gray_surrounding[mask_surrounding == 255]))
    contrast = float(np.std(gray_surrounding[mask_surrounding == 255]))

    # 8. Calcul de luminance et contraste sur l'image entière
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_lum_full = float(np.mean(gray_image))
    contrast_full = float(np.std(gray_image))

    # 9. Seuils
    seuil_h = 55
    seuil_s = 37
    seuil_v = 54
    seuil_lum = 104
    seuil_contrast = 60

    # 10. Condition complexe existante sur hétérogénéité
    condition_std = (
        (std_v < seuil_v and std_h < seuil_h and std_s > seuil_s)
        or (std_v < seuil_v and std_h > seuil_h and std_s < seuil_s)
        or (std_v < seuil_v and std_h > seuil_h and std_s > seuil_s)
        or (std_v > seuil_v and std_h < seuil_h and std_s < seuil_s)
        or (std_v > seuil_v and std_h < seuil_h and std_s > seuil_s)
        or (std_v > seuil_v and std_h > seuil_h and std_s < seuil_s)
        or (std_v > seuil_v and std_h > seuil_h and std_s > seuil_s)
    )

    # 11. Nouveau critère luminance/contraste sur la zone entourante
    condition_lum_contrast = (mean_lum < seuil_lum) or (contrast > seuil_contrast)

    # 12. Nouveau critère luminance/contraste sur l'image entière
    condition_lum_contrast_full = (mean_lum_full < seuil_lum) or (contrast_full > seuil_contrast)

    # 13. Décision finale : OR entre conditions
    if condition_std or condition_lum_contrast or condition_lum_contrast_full:
        if debug:
            print(f"Poubelle pleine (dépôts autour détectés)")
        return "pleine"
    else:
        if debug:
            print("Poubelle vide (pas de dépôt autour)")
        return "vide"