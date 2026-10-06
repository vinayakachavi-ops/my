// main.js - Core application utilities and interactions

document.addEventListener("DOMContentLoaded", function () {
    // Refresh icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // Auto-dismiss alert notifications after 6 seconds
    const alerts = document.querySelectorAll(".flash-card");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-6px)";
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });
});

// Toggle password input visibility
function togglePasswordVisibility(inputId, btnElement) {
    const input = document.getElementById(inputId);
    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        if (btnElement) {
            btnElement.innerHTML = '<i data-lucide="eye-off"></i>';
            if (window.lucide) lucide.createIcons();
        }
    } else {
        input.type = "password";
        if (btnElement) {
            btnElement.innerHTML = '<i data-lucide="eye"></i>';
            if (window.lucide) lucide.createIcons();
        }
    }
}
