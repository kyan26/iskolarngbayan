// ── Apply saved theme IMMEDIATELY before paint ──
(function () {
    const saved = localStorage.getItem('iskolar-theme');
    if (saved === 'light') document.body.classList.add('light-mode');
})();

// ── Sidebar group toggle (global, called from inline onclick) ──
function toggleGroup(btn, groupId) {
    const items = document.getElementById(groupId);
    if (!items) return;
    const isOpen = items.classList.contains('open');
    items.classList.toggle('open', !isOpen);
    btn.classList.toggle('open', !isOpen);
}

// ── After DOM ready ──
document.addEventListener('DOMContentLoaded', function () {

    // ── Skeleton → real content ──
    const skeleton = document.getElementById('skeletonScreen');
    const content  = document.getElementById('pageContent');

    if (skeleton && content) {
        const minDisplay = 1500; // ms — adjust to taste
        const start      = Date.now();
        let   shown      = false; // guard: run only once

        function showContent() {
            if (shown) return;
            shown = true;

            const elapsed   = Date.now() - start;
            const remaining = Math.max(0, minDisplay - elapsed);

            setTimeout(function () {
                skeleton.style.transition = 'opacity 0.3s ease';
                skeleton.style.opacity    = '0';

                setTimeout(function () {
                    skeleton.style.display   = 'none';
                    content.style.opacity    = '0';
                    content.style.display    = 'block';

                    requestAnimationFrame(function () {
                        content.style.transition = 'opacity 0.3s ease';
                        content.style.opacity    = '1';
                    });
                }, 300);
            }, remaining);
        }

        if (document.readyState === 'complete') {
            showContent();
        } else {
            window.addEventListener('load', showContent);
            setTimeout(showContent, 3000); // hard fallback — never gets stuck
        }
    }

    // ── Theme toggle ──
    function updateThemeIcon(isLight) {
        const moon = document.getElementById('icon-moon');
        const sun  = document.getElementById('icon-sun');
        if (moon) moon.style.display = isLight ? 'none' : '';
        if (sun)  sun.style.display  = isLight ? ''     : 'none';
    }

    window.toggleTheme = function () {
        const isLight = document.body.classList.toggle('light-mode');
        localStorage.setItem('iskolar-theme', isLight ? 'light' : 'dark');
        updateThemeIcon(isLight);
    };

    updateThemeIcon(document.body.classList.contains('light-mode'));

    // ── Sidebar: auto-open active group + mark active link ──
    const path = window.location.pathname;

    document.querySelectorAll('.snb-group-items').forEach(function (group) {
        const hasActive = Array.from(group.querySelectorAll('a')).some(function (a) {
            const href = a.getAttribute('href');
            return href && path.startsWith(href);
        });
        if (hasActive) {
            group.classList.add('open');
            const btn = group.previousElementSibling;
            if (btn && btn.classList.contains('snb-group-btn')) btn.classList.add('open');
        }
    });

    document.querySelectorAll('.snb-item').forEach(function (a) {
        const href = a.getAttribute('href');
        if (href && (path === href || path.startsWith(href + '/'))) {
            a.classList.add('snb-active');
        }
    });

});

// ── Mobile sidebar toggle ──
function toggleSidebar() {
    const sidebar = document.getElementById('top-bar-sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const isOpen  = !sidebar.classList.contains('-translate-x-full');

    if (isOpen) {
        closeSidebar();
    } else {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeSidebar() {
    const sidebar = document.getElementById('top-bar-sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
}

// Close sidebar when a nav link is clicked on mobile
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('#top-bar-sidebar .snb-item').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth < 640) closeSidebar();
        });
    });
});