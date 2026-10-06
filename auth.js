// auth.js - Password strength validation and real-time feedback

document.addEventListener("DOMContentLoaded", function () {
    const passwordInput = document.getElementById("reg_password");
    if (!passwordInput) return;

    const strengthBar = document.getElementById("strengthBar");
    const ruleLength = document.getElementById("rule-length");
    const ruleUpper = document.getElementById("rule-upper");
    const ruleLower = document.getElementById("rule-lower");
    const ruleDigit = document.getElementById("rule-digit");
    const ruleSpecial = document.getElementById("rule-special");

    function updateRule(element, isValid) {
        if (!element) return;
        if (isValid) {
            element.classList.add("valid");
            element.querySelector("i")?.setAttribute("data-lucide", "check-circle-2");
        } else {
            element.classList.remove("valid");
            element.querySelector("i")?.setAttribute("data-lucide", "circle");
        }
    }

    passwordInput.addEventListener("input", function () {
        const val = passwordInput.value;

        const hasLength = val.length >= 8;
        const hasUpper = /[A-Z]/.test(val);
        const hasLower = /[a-z]/.test(val);
        const hasDigit = /\d/.test(val);
        const hasSpecial = /[@$!%*?&#^()_\-+=\[\]{}|:;<>,./?~`]/.test(val);

        updateRule(ruleLength, hasLength);
        updateRule(ruleUpper, hasUpper);
        updateRule(ruleLower, hasLower);
        updateRule(ruleDigit, hasDigit);
        updateRule(ruleSpecial, hasSpecial);

        if (window.lucide) {
            lucide.createIcons();
        }

        // Calculate score 0 to 5
        let score = 0;
        if (hasLength) score++;
        if (hasUpper) score++;
        if (hasLower) score++;
        if (hasDigit) score++;
        if (hasSpecial) score++;

        const percentage = (score / 5) * 100;
        strengthBar.style.width = percentage + "%";

        if (score <= 2) {
            strengthBar.style.backgroundColor = "var(--accent-rose)";
        } else if (score <= 4) {
            strengthBar.style.backgroundColor = "var(--accent-amber)";
        } else {
            strengthBar.style.backgroundColor = "var(--accent-emerald)";
        }
    });
});
