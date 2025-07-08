// Script pour afficher une animation de chargement lors de l'upload côté admin

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const adminPredictionLoading = document.getElementById('admin-prediction-loading');
    const adminPredictionResult = document.getElementById('admin-prediction-result');
    if (!uploadForm || !adminPredictionLoading || !adminPredictionResult) return;

    uploadForm.addEventListener('submit', function(e) {
        // Afficher l'animation de chargement
        adminPredictionResult.innerHTML = '';
        adminPredictionLoading.style.display = 'block';
    });

    // Pour masquer l'animation après le rechargement de la page (fin du POST)
    window.addEventListener('pageshow', function() {
        adminPredictionLoading.style.display = 'none';
    });
});
