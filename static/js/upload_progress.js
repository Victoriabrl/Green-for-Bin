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
                        if (resp.success) {
                            predictionDiv.innerHTML = '<b>Prédiction automatique :</b> ' + resp.auto_label;
                        } else {
                            predictionDiv.innerHTML = '<span style="color:red">' + (resp.error || 'Erreur lors du traitement.') + '</span>';
                        }
                    } catch {
                        predictionDiv.innerHTML = '<span style="color:red">Erreur lors du traitement.</span>';
                    }
                }
            };

            xhr.open('POST', uploadForm.action, true);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.send(formData);
        });
    }
});
