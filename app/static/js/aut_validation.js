document.addEventListener('DOMContentLoaded', function() {
    const password = document.getElementById('password');
    const confirm = document.getElementById('confirm_password');
    const strengthBar = document.getElementById('passwordStrength');

    // 1. Vérification de la force du mot de passe
    password.addEventListener('input', function() {
        const val = password.value;
        let strength = 0;
        if (val.length > 5) strength += 40;
        if (/[A-Z]/.test(val)) strength += 30;
        if (/[0-9]/.test(val)) strength += 30;

        strengthBar.style.width = strength + '%';
        strengthBar.className = 'progress-bar ' + 
            (strength < 50 ? 'bg-danger' : strength < 100 ? 'bg-warning' : 'bg-success');
    });

    // 2. Vérification de la correspondance
    function validatePassword() {
        if (password.value !== confirm.value) {
            confirm.setCustomValidity("Les mots de passe ne correspondent pas");
        } else {
            confirm.setCustomValidity('');
        }
    }

    password.addEventListener('change', validatePassword);
    confirm.addEventListener('keyup', validatePassword);
});