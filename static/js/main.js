/**
 * Vision-Based Smart Medicine Waste Identifier
 * Interactive Dual-Stream Frontend JavaScript (plan.md Phase 7)
 */

let activeCameraSide = 'front';
let videoStream = null;

function openCameraModal(side) {
    activeCameraSide = side;
    const modal = document.getElementById('webcamModal');
    const title = document.getElementById('cameraModalTitle');
    const video = document.getElementById('webcamVideo');

    if (title) {
        title.innerText = side === 'front' ? 'Capture Front Packaging (Brand / Salt)' : 'Capture Back Packaging (Expiry / MFG)';
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
        }).then(stream => {
            videoStream = stream;
            video.srcObject = stream;
            modal.style.display = 'flex';
        }).catch(err => {
            alert('Unable to access device camera: ' + err.message);
        });
    } else {
        alert('Webcam API is not supported in this browser.');
    }
}

function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(t => t.stop());
        videoStream = null;
    }
    const modal = document.getElementById('webcamModal');
    if (modal) modal.style.display = 'none';
}

function resetSide(side) {
    const fileInput = document.getElementById(side + 'FileInput');
    const webcamInput = document.getElementById(side + 'WebcamInput');
    const prompt = document.getElementById(side + 'Prompt');
    const previewContainer = document.getElementById(side + 'PreviewContainer');
    const previewImg = document.getElementById(side + 'PreviewImg');

    if (fileInput) fileInput.value = '';
    if (webcamInput) webcamInput.value = '';
    if (previewImg) previewImg.src = '';
    if (previewContainer) previewContainer.style.display = 'none';
    if (prompt) prompt.style.display = 'block';
}

function resetAll() {
    resetSide('front');
    resetSide('back');
}

function setupDropzone(side) {
    const dropzone = document.getElementById(side + 'Dropzone');
    const fileInput = document.getElementById(side + 'FileInput');
    const prompt = document.getElementById(side + 'Prompt');
    const previewContainer = document.getElementById(side + 'PreviewContainer');
    const previewImg = document.getElementById(side + 'PreviewImg');

    if (!dropzone || !fileInput) return;

    ['dragenter', 'dragover'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            showFilePreview(files[0], prompt, previewContainer, previewImg);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            showFilePreview(fileInput.files[0], prompt, previewContainer, previewImg);
        }
    });
}

function showFilePreview(file, promptElem, containerElem, imgElem) {
    if (!file.type.match('image.*')) {
        alert('Please select a valid image file (JPG, PNG, WebP).');
        return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
        imgElem.src = e.target.result;
        promptElem.style.display = 'none';
        containerElem.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

document.addEventListener('DOMContentLoaded', () => {
    setupDropzone('front');
    setupDropzone('back');

    const closeWebcamBtn = document.getElementById('closeWebcamBtn');
    if (closeWebcamBtn) {
        closeWebcamBtn.addEventListener('click', stopCamera);
    }

    const captureWebcamBtn = document.getElementById('captureWebcamBtn');
    if (captureWebcamBtn) {
        captureWebcamBtn.addEventListener('click', () => {
            const video = document.getElementById('webcamVideo');
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth || 800;
            canvas.height = video.videoHeight || 600;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
            const side = activeCameraSide;

            const webcamInput = document.getElementById(side + 'WebcamInput');
            const prompt = document.getElementById(side + 'Prompt');
            const previewContainer = document.getElementById(side + 'PreviewContainer');
            const previewImg = document.getElementById(side + 'PreviewImg');

            if (webcamInput) webcamInput.value = dataUrl;
            if (previewImg) previewImg.src = dataUrl;
            if (prompt) prompt.style.display = 'none';
            if (previewContainer) previewContainer.style.display = 'block';

            stopCamera();
        });
    }

    const uploadForm = document.getElementById('uploadForm');
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (uploadForm && loadingOverlay) {
        uploadForm.addEventListener('submit', () => {
            loadingOverlay.style.display = 'flex';
        });
    }
});
