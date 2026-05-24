// ── ICONS ──
const warningIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-[#f43f5e]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`;
const checkIcon  = `<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-[#10b981]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;

// ── HELPERS ──
function showError(msgId, inputId, message) {
    const msg   = document.getElementById(msgId);
    const input = document.getElementById(inputId);
    msg.innerHTML = `${warningIcon}<span style="color:#f43f5e;">${message}</span>`;
    msg.style.display = 'flex';
    input.style.borderColor = '#f43f5e';
    input.style.boxShadow   = '0 0 0 2px rgba(244,63,94,0.3)';
}

function showSuccess(msgId, inputId, message = '') {
    const msg   = document.getElementById(msgId);
    const input = document.getElementById(inputId);
    input.style.borderColor = '#10b981';
    input.style.boxShadow   = '0 0 0 2px rgba(16,185,129,0.3)';
    if (message) {
        msg.innerHTML = `${checkIcon}<span style="color:#10b981;">${message}</span>`;
        msg.style.display = 'flex';
    } else {
        msg.style.display = 'none';
    }
}

function resetField(msgId, inputId) {
    const msg   = document.getElementById(msgId);
    const input = document.getElementById(inputId);
    msg.innerHTML = '';
    msg.style.display = 'none';
    input.style.borderColor = '';
    input.style.boxShadow   = '';
}

// ── FULL NAME ──
function validateFullName() {
    const value = document.getElementById('full_name').value.trim();
    if (value === '')          { resetField('fullNameMsg', 'full_name'); return false; }
    if (value.length < 2)      { showError('fullNameMsg', 'full_name', 'Full name must be at least 2 characters.'); return false; }
    if (/[^a-zA-Z\s]/.test(value)) { showError('fullNameMsg', 'full_name', 'Full name must contain letters only.'); return false; }
    showSuccess('fullNameMsg', 'full_name');
    return true;
}

// ── ADDRESS ──
function validateAddress() {
    const value = document.getElementById('address').value.trim();
    if (value === '')     { resetField('addressMsg', 'address'); return false; }
    if (value.length < 5) { showError('addressMsg', 'address', 'Address must be at least 5 characters.'); return false; }
    showSuccess('addressMsg', 'address');
    return true;
}

// ── BIRTHDATE ──
function validateBirthDate() {
    const value = document.getElementById('birthdate').value;
    if (!value) { resetField('birthDateMsg', 'birthdate'); return false; }
    const birth = new Date(value);
    const today = new Date();
    const age   = today.getFullYear() - birth.getFullYear();
    if (birth >= today) { showError('birthDateMsg', 'birthdate', 'Birth date cannot be today or in the future.'); return false; }
    if (age > 120)      { showError('birthDateMsg', 'birthdate', 'Please enter a valid birth date.'); return false; }
    if (age < 15)       { showError('birthDateMsg', 'birthdate', 'Must be at least 15 years old.'); return false; }
    showSuccess('birthDateMsg', 'birthdate');
    return true;
}

// ── CONTACT NUMBER ──
function validatePHNumber(input) {
    const value = input.value;
    input.style.borderColor = '';
    input.style.boxShadow   = '';
    document.getElementById('contactMsg').classList.add('hidden');
    if (value === '') { return; }
    if (/[^0-9]/.test(value))                                { showError('contactMsg', 'contact_number', 'Numbers only.'); return; }
    if (!(value.startsWith('09') || value.startsWith('63'))) { showError('contactMsg', 'contact_number', 'Must start with 09 or 63.'); return; }
    if (value.startsWith('09') && value.length < 11)         { showError('contactMsg', 'contact_number', 'Too short — must be 11 digits.'); return; }
    if (value.startsWith('09') && value.length > 11)         { showError('contactMsg', 'contact_number', 'Too long — must be 11 digits.'); return; }
    if (value.startsWith('63') && value.length < 12)         { showError('contactMsg', 'contact_number', 'Too short — must be 12 digits.'); return; }
    if (value.startsWith('63') && value.length > 12)         { showError('contactMsg', 'contact_number', 'Too long — must be 12 digits.'); return; }
    clearTimeout(window.contactDebounce);
    window.contactDebounce = setTimeout(() => {
        fetch(`/user/check-contact/?contact_number=${encodeURIComponent(value)}`)
            .then(res => res.json())
            .then(data => {
                if (data.available) { showSuccess('contactMsg', 'contact_number', '✓ Contact number is available.'); }
                else                showError('contactMsg', 'contact_number', 'This contact number is already in use.');
            }).catch(() => resetField('contactMsg', 'contact_number'));
    }, 500);
}

// ── USERNAME ──
let usernameDebounce  = null;
let usernameAvailable = false;

function validateUsername() {
    const value = document.getElementById('username').value.trim();
    clearTimeout(usernameDebounce);
    if (value === '')          { resetField('usernameMsg', 'username'); usernameAvailable = false; return false; }
    if (value.length < 3)      { showError('usernameMsg', 'username', 'Username must be at least 3 characters.'); usernameAvailable = false; return false; }
    if (/\s/.test(value))      { showError('usernameMsg', 'username', 'Username cannot contain spaces.'); usernameAvailable = false; return false; }
    if (/[^a-zA-Z0-9_-]/.test(value)) { showError('usernameMsg', 'username', 'Letters, numbers, underscores and dashes only.'); usernameAvailable = false; return false; }
    usernameDebounce = setTimeout(() => {
        fetch(`/user/check-username/?username=${encodeURIComponent(value)}`)
            .then(res => res.json())
            .then(data => {
                if (data.available) { showSuccess('usernameMsg', 'username', '✓ Username is available.'); usernameAvailable = true; }
                else                { showError('usernameMsg', 'username', '✕ Username already exists, please choose another.'); usernameAvailable = false; }
            }).catch(() => { resetField('usernameMsg', 'username'); usernameAvailable = true; });
    }, 500);
    return true;
}

// ── EMAIL ──
let emailDebounce  = null;
let emailAvailable = true;

function validateEmail() {
    const value = document.getElementById('email').value.trim();
    clearTimeout(emailDebounce);
    if (value === '') { resetField('emailMsg', 'email'); emailAvailable = true; return true; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        showError('emailMsg', 'email', 'Please enter a valid email address.');
        emailAvailable = false; return false;
    }
    emailDebounce = setTimeout(() => {
        fetch(`/user/check-email/?email=${encodeURIComponent(value)}`)
            .then(res => res.json())
            .then(data => {
                if (data.available) { showSuccess('emailMsg', 'email', '✓ Email is available.'); emailAvailable = true; }
                else                { showError('emailMsg', 'email', '✕ Email already exists, please use another.'); emailAvailable = false; }
            }).catch(() => { resetField('emailMsg', 'email'); emailAvailable = true; });
    }, 500);
    return true;
}

// ── PASSWORD ──
function validatePassword() {
    const value = document.getElementById('password').value;
    if (value === '')    { resetField('passwordMsg', 'password'); return false; }
    if (value.length < 3) { showError('passwordMsg', 'password', 'Password must be at least 3 characters.'); return false; }
    showSuccess('passwordMsg', 'password');
    checkPasswordMatch();
    return true;
}

// ── CONFIRM PASSWORD ──
function checkPasswordMatch() {
    const password     = document.getElementById('password').value;
    const confirm      = document.getElementById('confirm_password').value;
    const msg          = document.getElementById('matchMessage');
    const confirmInput = document.getElementById('confirm_password');

    if (confirm === '') {
        msg.style.display = 'none';
        confirmInput.style.borderColor = '';
        confirmInput.style.boxShadow   = '';
        return false;
    }

    msg.style.display = 'flex';
    if (password === confirm) {
        msg.innerHTML = `${checkIcon}<span style="color:#10b981;">✓ Passwords match</span>`;
        confirmInput.style.borderColor = '#10b981';
        confirmInput.style.boxShadow   = '0 0 0 2px rgba(16,185,129,0.3)';
        return true;
    } else {
        msg.innerHTML = `${warningIcon}<span style="color:#f43f5e;">✕ Passwords do not match</span>`;
        confirmInput.style.borderColor = '#f43f5e';
        confirmInput.style.boxShadow   = '0 0 0 2px rgba(244,63,94,0.3)';
        return false;
    }
}

// ── VALIDATE ON SUBMIT ──
function validateForm(event) {
    if (!usernameAvailable) {
        const val = document.getElementById('username').value.trim();
        if (val.length >= 3) {
            showError('usernameMsg', 'username', '✕ Username already exists, please choose another.');
            event.preventDefault();
            document.getElementById('username').scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
    }
    if (!emailAvailable) {
        const val = document.getElementById('email').value.trim();
        if (val.length > 0) {
            showError('emailMsg', 'email', '✕ Email already exists, please use another.');
            event.preventDefault();
            document.getElementById('email').scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
    }
    const results = [
        validateFullName(),
        validateAddress(),
        validateBirthDate(),
        validatePassword(),
        checkPasswordMatch(),
    ];
    if (results.includes(false)) {
        event.preventDefault();
        const firstError = document.querySelector('[style*="border-color: rgb(244"]');
        if (firstError) firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// ── TOGGLE PASSWORD ──
function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon  = document.getElementById(iconId);
    if (input.type === 'password') {
        input.type   = 'text';
        icon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a9.97 9.97 0 012.186-3.411M6.53 6.53A9.969 9.969 0 0112 5c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411M3 3l18 18"/>`;
    } else {
        input.type   = 'password';
        icon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>`;
    }
}