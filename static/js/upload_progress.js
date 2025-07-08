// Script pour gérer l'upload asynchrone avec barre de progression et affichage de la prédiction

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');
    const predictionDiv = document.getElementById('prediction-result');
    const fileInput = uploadForm ? uploadForm.querySelector('input[type="file"]') : null;

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            const xhr = new XMLHttpRequest();
            progressContainer.style.display = 'block';
            predictionDiv.innerHTML = '';
            // Afficher l'animation de chargement
            var predictionLoading = document.getElementById('prediction-loading');
            if (predictionLoading) predictionLoading.style.display = 'block';
            progressBar.style.width = '0%';
            progressBar.innerText = '0%';
            progressBar.classList.add('progress-bar-animated');

            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + '%';
                    progressBar.innerText = percent + '%';
                    if (percent >= 100) {
                        progressBar.classList.remove('progress-bar-animated');
                    }
                }
            });

            xhr.onreadystatechange = function() {
                if (xhr.readyState === XMLHttpRequest.DONE) {
                    progressBar.style.width = '100%';
                    progressBar.innerText = '100%';
                    progressBar.classList.remove('progress-bar-animated');
                    if (fileInput) fileInput.value = '';
                    try {
                        const resp = JSON.parse(xhr.responseText);
                        if (predictionLoading) predictionLoading.style.display = 'none';
                        if (resp.success) {
                            let meta = resp.metadata;
                            let metaHtml = '';
                            if (meta) {
                                metaHtml = `
                                    <ul class="list-group mt-2 mb-2">
                                        <li class="list-group-item">${i18n_taille} <b>${meta.width} x ${meta.height}</b> px</li>
                                        <li class="list-group-item">${i18n_lum} <b>${meta.luminosity}</b></li>
                                        <li class="list-group-item">${i18n_contraste} <b>${meta.contrast}</b></li>
                                    </ul>
                                `;
                            }
                            predictionDiv.innerHTML = `<div class="alert alert-info shadow-lg p-3 mb-3 rounded" style="font-size:1.3em; font-weight:bold; border:2px solid #007bff; background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%); color:#0d47a1;">
                                <span style="font-size:1.2em;">${i18n_pred_auto}</span> <span style="font-size:1.3em; color:#007bff;">${resp.auto_label}</span>
                                ${metaHtml}
                            </div>`;
                        } else {
                        predictionDiv.innerHTML = '<span style="color:red">' + (resp.error || i18n_erreur_traitement) + '</span>';
                        }
                    } catch {
                    if (predictionLoading) predictionLoading.style.display = 'none';
                    predictionDiv.innerHTML = '<span style="color:red">' + i18n_erreur_traitement + '</span>';
                    }
                }
            };

            xhr.open('POST', uploadForm.action, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
        });
    }
});
