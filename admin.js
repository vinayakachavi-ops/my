// admin.js - Admin dashboard interaction handlers

function switchAdminTab(tabId, btnElement) {
    // Hide all tab contents
    document.querySelectorAll(".tab-content").forEach((el) => {
        el.style.display = "none";
    });

    // Deactivate all tab buttons
    document.querySelectorAll(".tab-btn").forEach((el) => {
        el.classList.remove("active");
    });

    // Show target tab
    const target = document.getElementById(tabId);
    if (target) target.style.display = "block";

    if (btnElement) btnElement.classList.add("active");
    if (window.lucide) lucide.createIcons();
}

function openAddUserModal() {
    const modal = document.getElementById("addUserModal");
    if (modal) {
        modal.style.display = "flex";
        if (window.lucide) lucide.createIcons();
    }
}

function closeAddUserModal() {
    const modal = document.getElementById("addUserModal");
    if (modal) modal.style.display = "none";
}

function filterAuditTable() {
    const query = document.getElementById("auditFilterInput").value.toLowerCase();
    const rows = document.querySelectorAll("#auditTable tbody tr.audit-row");

    rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
    });
}
