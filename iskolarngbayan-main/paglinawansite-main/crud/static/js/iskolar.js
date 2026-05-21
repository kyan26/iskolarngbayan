// ── Apply saved theme IMMEDIATELY before paint ──
(function () {
    const saved = localStorage.getItem('iskolar-theme');
    if (saved === 'light') document.body.classList.add('light-mode');
})();

// ── After DOM ready ──
document.addEventListener('DOMContentLoaded', function () {

    // Hide skeleton, show real content
    const skeleton = document.getElementById('skeletonScreen');
    const content  = document.getElementById('pageContent');
    if (skeleton && content) {
        setTimeout(function () {
            skeleton.style.display = 'none';
            content.style.display  = 'block';
        }, 600);
    }

    // Theme toggle
    function updateThemeIcon(isLight) {
        const moon = document.getElementById('icon-moon');
        const sun  = document.getElementById('icon-sun');
        if (moon) moon.style.display = isLight ? 'none' : '';
        if (sun)  sun.style.display  = isLight ? '' : 'none';
    }

    window.toggleTheme = function () {
        const isLight = document.body.classList.toggle('light-mode');
        localStorage.setItem('iskolar-theme', isLight ? 'light' : 'dark');
        updateThemeIcon(isLight);
    };

    updateThemeIcon(document.body.classList.contains('light-mode'));

    // Sidebar: auto-open active group + mark active link
    const path = window.location.pathname;

    document.querySelectorAll('.snb-group-items').forEach(function (group) {
        const hasActive = Array.from(group.querySelectorAll('a')).some(function (a) {
            return path.startsWith(a.getAttribute('href'));
        });
        if (hasActive) {
            group.classList.add('open');
            const btn = group.previousElementSibling;
            if (btn && btn.classList.contains('snb-group-btn')) btn.classList.add('open');
        }
    });

    document.querySelectorAll('.snb-item').forEach(function (a) {
        if (path === a.getAttribute('href') || path.startsWith(a.getAttribute('href') + '/')) {
            a.classList.add('snb-active');
        }
    });

});

// Sidebar group toggle
function toggleGroup(btn, groupId) {
    const items = document.getElementById(groupId);
    const isOpen = items.classList.contains('open');
    items.classList.toggle('open', !isOpen);
    btn.classList.toggle('open', !isOpen);
}