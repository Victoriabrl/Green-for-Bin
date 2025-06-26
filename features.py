import os
from PIL import Image, ImageStat
import cv2
import numpy as np

def extract_image_features(image_path):
    file_size = os.path.getsize(image_path)  # en octets
    img = Image.open(image_path).convert('RGB')
    width, height = img.size

    # Couleur moyenne (RVB)
    stat = ImageStat.Stat(img)
    mean_r, mean_g, mean_b = stat.mean

    # Contraste (différence max-min des pixels)
    img_gray = img.convert('L')
    extrema = img_gray.getextrema()
    contrast = extrema[1] - extrema[0]

    # Détection de contours (Sobel via OpenCV)
    img_cv = cv2.imread(image_path)
    img_gray_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(img_gray_cv, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(img_gray_cv, cv2.CV_64F, 0, 1, ksize=3)
    edges = cv2.magnitude(sobelx, sobely)
    edges = np.uint8(edges)
    contour_count = int(np.sum(edges > 128))

    return {
        "file_size": file_size,
        "width": width,
        "height": height,
        "mean_r": int(mean_r),
        "mean_g": int(mean_g),
        "mean_b": int(mean_b),
        "contrast": int(contrast),
        "contour_count": contour_count
    }

def classify_image_rule(features, seuil_sombre=100, seuil_taille=500*1024):
    mean_color = (features["mean_r"] + features["mean_g"] + features["mean_b"]) / 3
    if mean_color < seuil_sombre and features["file_size"] > seuil_taille:
        return "pleine_auto"
    else:
        return "vide_auto"