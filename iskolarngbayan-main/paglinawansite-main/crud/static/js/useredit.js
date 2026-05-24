function checkBeforeSubmit() {
    const fields = [
        { name: 'username'       },
        { name: 'full_name'      },
        { name: 'role'           },
        { name: 'gender'         },
        { name: 'birthdate'      },
        { name: 'address'        },
        { name: 'contact_number' },
        { name: 'email'          },
    ];
    for (const f of fields) {
        const el = document.querySelector(`[name="${f.name}"]`);
        if (el && !el.value.trim()) {
            el.style.borderColor = '#f43f5e';
            el.style.boxShadow   = '0 0 0 2px rgba(244,63,94,0.2)';
            el.focus();
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return false;
        }
    }
    if (submitBtn.disabled) return false;
    return true;
}

function previewImage(event) {
    const preview     = document.getElementById('imagePreview');
    const placeholder = document.getElementById('avatarPlaceholder');
    const file        = event.target.files[0];
    if (file) {
        preview.src = URL.createObjectURL(file);
        preview.classList.remove('hidden');
        if (placeholder) placeholder.classList.add('hidden');
    }
}

// ── SHARED ──
const submitBtn = document.getElementById('submitBtn');

// ── ICONS ──
const warningIcon = `<svg xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;flex-shrink:0;" fill="none" viewBox="0 0 24 24" stroke="#f43f5e" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`;
const checkIcon   = `<svg xmlns="http://www.w3.org/2000/svg" style="width:14px;height:14px;flex-shrink:0;" fill="none" viewBox="0 0 24 24" stroke="#22c55e" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>`;

// ── HELPERS ──
function enableSubmit()  { submitBtn.disabled = false; submitBtn.style.opacity = '1';   submitBtn.style.cursor = ''; }
function disableSubmit() { submitBtn.disabled = true;  submitBtn.style.opacity = '0.5'; submitBtn.style.cursor = 'not-allowed'; }

function showFeedback(el, icon, msg, color) {
    el.innerHTML     = `${icon}<span style="color:${color};">${msg}</span>`;
    el.style.display = 'flex';
}
function hideFeedback(el) {
    el.innerHTML     = '';
    el.style.display = 'none';
}
function setInputOk(input) {
    input.style.borderColor = '#22c55e';
    input.style.boxShadow   = '0 0 0 2px rgba(34,197,94,0.3)';
}
function setInputErr(input) {
    input.style.borderColor = '#f43f5e';
    input.style.boxShadow   = '0 0 0 2px rgba(244,63,94,0.3)';
}
function resetInput(input) {
    input.style.borderColor = '';
    input.style.boxShadow   = '';
}

// ══════════════════════════
// USERNAME
// ══════════════════════════
const usernameInput    = document.getElementById('usernameInput');
const usernameFeedback = document.getElementById('usernameFeedback');
let usernameDebounce   = null;

usernameInput.addEventListener('input', function () {
    const value = this.value.trim();
    clearTimeout(usernameDebounce);

    if (!value || value.toLowerCase() === originalUsername) {
        resetInput(usernameInput);
        hideFeedback(usernameFeedback);
        enableSubmit();
        return;
    }
    if (value.length < 3) {
        setInputErr(usernameInput);
        showFeedback(usernameFeedback, warningIcon, 'Username must be at least 3 characters.', '#f43f5e');
        disableSubmit(); return;
    }
    if (/\s/.test(value)) {
        setInputErr(usernameInput);
        showFeedback(usernameFeedback, warningIcon, 'Username cannot contain spaces.', '#f43f5e');
        disableSubmit(); return;
    }
    if (/[^a-zA-Z0-9_-]/.test(value)) {
        setInputErr(usernameInput);
        showFeedback(usernameFeedback, warningIcon, 'Letters, numbers, underscores and dashes only.', '#f43f5e');
        disableSubmit(); return;
    }

    usernameDebounce = setTimeout(() => {
        fetch(`/user/check-username/?username=${encodeURIComponent(value)}&user_id=${currentUserId}`)
            .then(r => r.json())
            .then(data => {
                if (data.available) {
                    setInputOk(usernameInput);
                    showFeedback(usernameFeedback, checkIcon, '✓ Username is available.', '#22c55e');
                    enableSubmit();
                } else {
                    setInputErr(usernameInput);
                    showFeedback(usernameFeedback, warningIcon, '✕ Username already exists, please choose another.', '#f43f5e');
                    disableSubmit();
                }
            })
            .catch(() => { resetInput(usernameInput); hideFeedback(usernameFeedback); enableSubmit(); });
    }, 500);
});

// ══════════════════════════
// CONTACT NUMBER
// ══════════════════════════
const contactInput    = document.getElementById('contactInput');
const contactFeedback = document.getElementById('contactFeedback');
let contactDebounce   = null;

function validateContact(input) {
    const value = input.value;
    clearTimeout(contactDebounce);

    if (!value || value === originalContact) {
        resetInput(contactInput);
        hideFeedback(contactFeedback);
        enableSubmit();
        return;
    }
    if (/[^0-9]/.test(value))                                { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Numbers only.', '#f43f5e');                  disableSubmit(); return; }
    if (!(value.startsWith('09') || value.startsWith('63'))) { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Must start with 09 or 63.', '#f43f5e');       disableSubmit(); return; }
    if (value.startsWith('09') && value.length < 11)         { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Too short — must be 11 digits.', '#f43f5e'); disableSubmit(); return; }
    if (value.startsWith('09') && value.length > 11)         { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Too long — must be 11 digits.', '#f43f5e');  disableSubmit(); return; }
    if (value.startsWith('63') && value.length < 12)         { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Too short — must be 12 digits.', '#f43f5e'); disableSubmit(); return; }
    if (value.startsWith('63') && value.length > 12)         { setInputErr(contactInput); showFeedback(contactFeedback, warningIcon, 'Too long — must be 12 digits.', '#f43f5e');  disableSubmit(); return; }

    contactDebounce = setTimeout(() => {
        fetch(`/user/check-contact/?contact_number=${encodeURIComponent(value)}&user_id=${currentUserId}`)
            .then(r => r.json())
            .then(data => {
                if (data.available) {
                    setInputOk(contactInput);
                    showFeedback(contactFeedback, checkIcon, '✓ Contact number is available.', '#22c55e');
                    enableSubmit();
                } else {
                    setInputErr(contactInput);
                    showFeedback(contactFeedback, warningIcon, 'This contact number is already in use.', '#f43f5e');
                    disableSubmit();
                }
            })
            .catch(() => { resetInput(contactInput); hideFeedback(contactFeedback); enableSubmit(); });
    }, 500);
}

// ══════════════════════════
// EMAIL
// ══════════════════════════
const emailInput    = document.getElementById('emailInput');
const emailFeedback = document.getElementById('emailFeedback');
let emailDebounce   = null;

emailInput.addEventListener('input', function () {
    const value = this.value.trim();
    clearTimeout(emailDebounce);

    if (!value || value.toLowerCase() === originalEmail) {
        resetInput(emailInput);
        hideFeedback(emailFeedback);
        enableSubmit();
        return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        setInputErr(emailInput);
        showFeedback(emailFeedback, warningIcon, 'Please enter a valid email address.', '#f43f5e');
        disableSubmit(); return;
    }

    emailDebounce = setTimeout(() => {
        fetch(`/user/check-email/?email=${encodeURIComponent(value)}&user_id=${currentUserId}`)
            .then(r => r.json())
            .then(data => {
                if (data.available) {
                    setInputOk(emailInput);
                    showFeedback(emailFeedback, checkIcon, '✓ Email is available.', '#22c55e');
                    enableSubmit();
                } else {
                    setInputErr(emailInput);
                    showFeedback(emailFeedback, warningIcon, '✕ Email already exists, please use another.', '#f43f5e');
                    disableSubmit();
                }
            })
            .catch(() => { resetInput(emailInput); hideFeedback(emailFeedback); enableSubmit(); });
    }, 500);
});