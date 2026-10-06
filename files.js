// files.js - Client-side interactions for files vault

function openUploadModal() {
    const modal = document.getElementById("uploadModal");
    if (modal) {
        modal.style.display = "flex";
        if (window.lucide) lucide.createIcons();
    }
}

function closeUploadModal() {
    const modal = document.getElementById("uploadModal");
    if (modal) modal.style.display = "none";
}

function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const infoDiv = document.getElementById("selectedFileInfo");
        const nameSpan = document.getElementById("selectedFileName");
        const sizeSpan = document.getElementById("selectedFileSize");

        nameSpan.textContent = file.name;
        const sizeKb = (file.size / 1024).toFixed(1);
        sizeSpan.textContent = `(${sizeKb} KB)`;
        infoDiv.style.display = "inline-flex";
        if (window.lucide) lucide.createIcons();
    }
}

// Drag & Drop Setup
document.addEventListener("DOMContentLoaded", function () {
    const dropzone = document.getElementById("dropzoneArea");
    const fileInput = document.getElementById("fileInput");

    if (dropzone && fileInput) {
        ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ["dragenter", "dragover"].forEach((eventName) => {
            dropzone.addEventListener(eventName, () => dropzone.classList.add("dragover"), false);
        });

        ["dragleave", "drop"].forEach((eventName) => {
            dropzone.addEventListener(eventName, () => dropzone.classList.remove("dragover"), false);
        });

        dropzone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                fileInput.files = files;
                handleFileSelect(fileInput);
            }
        });

        dropzone.addEventListener("click", () => fileInput.click());
    }
});

// Filter files table
function filterFilesTable() {
    const query = document.getElementById("fileSearchInput").value.toLowerCase();
    const rows = document.querySelectorAll("#filesTable tbody tr.file-row");
    let visibleCount = 0;

    rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        if (text.includes(query)) {
            row.style.display = "";
            visibleCount++;
        } else {
            row.style.display = "none";
        }
    });

    const countDisplay = document.getElementById("fileCountDisplay");
    if (countDisplay) countDisplay.textContent = visibleCount;
}

// In-Memory Preview Modal Handler
function previewFile(fileId, filename) {
    const modal = document.getElementById("previewModal");
    const title = document.getElementById("previewTitle");
    const body = document.getElementById("previewBody");
    const downloadBtn = document.getElementById("previewDownloadBtn");

    if (!modal) return;

    title.textContent = `Decrypted: ${filename}`;
    downloadBtn.href = `/files/${fileId}/download`;
    body.innerHTML = `
        <div class="loading-spinner-box">
            <div class="spinner"></div>
            <p>Decrypting authenticated ciphertext in volatile memory...</p>
        </div>
    `;

    modal.style.display = "flex";
    if (window.lucide) lucide.createIcons();

    fetch(`/files/${fileId}/preview`)
        .then((res) => {
            if (!res.ok) throw new Error("Decryption or permission error");
            return res.json();
        })
        .then((data) => {
            if (data.status !== "success") {
                body.innerHTML = `<div class="flash-card flash-danger">Failed to decrypt: ${data.message}</div>`;
                return;
            }

            if (data.is_text) {
                body.innerHTML = `<pre class="preview-content-box">${escapeHtml(data.content)}</pre>`;
            } else if (data.mime_type && data.mime_type.startsWith("image/")) {
                body.innerHTML = `
                    <div class="preview-image-box">
                        <img src="${data.raw_url}" alt="${filename}">
                    </div>
                `;
            } else {
                body.innerHTML = `
                    <div class="empty-state">
                        <i data-lucide="file-check"></i>
                        <h3>Binary File Decrypted Successfully</h3>
                        <p>This file format (${data.mime_type}) is ready for secure download.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            }
        })
        .catch((err) => {
            body.innerHTML = `<div class="flash-card flash-danger">Error: ${err.message}</div>`;
        });
}

function closePreviewModal() {
    const modal = document.getElementById("previewModal");
    if (modal) modal.style.display = "none";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}
