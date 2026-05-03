/* ========================================
   LANDING PAGE PUBLIC JS - SILEBAT
   Interaksi navbar, scroll reveal, counter, chart, dan back-to-top.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initLandingNavbar();
    initBackToTop();
    initScrollReveal();
    initLandingCounters();
    initLandingCharts();
});

function readLandingJson(scriptId, fallbackValue) {
    const script = document.getElementById(scriptId);
    if (!script) {
        return fallbackValue;
    }

    try {
        return JSON.parse(script.textContent);
    } catch (error) {
        console.error('Gagal membaca data landing page.', error);
        return fallbackValue;
    }
}

function initLandingNavbar() {
    const navbar = document.getElementById('navbar');
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobileMenu');
    const menuLinks = document.querySelectorAll('.nav-menu a, .mobile-menu a[href^="#"]');
    const sections = document.querySelectorAll('section[id], footer[id], .profil-features[id]');
    let ticking = false;

    function setMobileMenu(open) {
        if (!hamburger || !mobileMenu) {
            return;
        }

        hamburger.classList.toggle('open', open);
        hamburger.setAttribute('aria-expanded', String(open));
        hamburger.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
        mobileMenu.classList.toggle('open', open);
        mobileMenu.setAttribute('aria-hidden', String(!open));
        document.body.classList.toggle('menu-open', open);
    }

    function setActiveLink() {
        if (!sections.length) {
            return;
        }

        let current = sections[0].id;
        sections.forEach(function (section) {
            if (window.scrollY >= section.offsetTop - 120) {
                current = section.id;
            }
        });

        menuLinks.forEach(function (link) {
            link.classList.toggle('active', link.getAttribute('href') === '#' + current);
        });
    }

    function updateNavbarState() {
        if (navbar) {
            navbar.classList.toggle('scrolled', window.scrollY > 40);
        }
        setActiveLink();
        ticking = false;
    }

    function requestNavbarUpdate() {
        if (ticking) {
            return;
        }
        ticking = true;
        window.requestAnimationFrame(updateNavbarState);
    }

    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', function () {
            setMobileMenu(!mobileMenu.classList.contains('open'));
        });

        mobileMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                setMobileMenu(false);
            });
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                setMobileMenu(false);
            }
        });

        document.addEventListener('click', function (event) {
            if (!mobileMenu.classList.contains('open')) {
                return;
            }

            const clickInsideMenu = mobileMenu.contains(event.target);
            const clickOnToggle = hamburger.contains(event.target);
            if (!clickInsideMenu && !clickOnToggle) {
                setMobileMenu(false);
            }
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 860) {
                setMobileMenu(false);
            }
        });
    }

    updateNavbarState();
    window.addEventListener('scroll', requestNavbarUpdate, { passive: true });
}

function initBackToTop() {
    const button = document.getElementById('backTop');
    if (!button) {
        return;
    }

    window.addEventListener('scroll', function () {
        button.classList.toggle('show', window.scrollY > 400);
    }, { passive: true });

    button.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

function initScrollReveal() {
    const selectors = [
        '.hero-content > *',
        '.hero-img-card',
        '.hero-badge',
        '.hero-badge2',
        '.section-label',
        '.section-title',
        '.section-desc',
        '.profil-img',
        '.profil-copy',
        '.profil-feat',
        '.stat-card',
        '.chart-card',
        '.inventory-heading > *',
        '.alat-card',
        '.peralatan-header > *',
        '.peralatan-card',
        '.footer-brand',
        '.footer-col',
        '.landing-empty-state:not(.is-hidden)',
    ];

    const elements = Array.from(new Set(
        selectors.flatMap(function (selector) {
            return Array.from(document.querySelectorAll(selector));
        })
    )).filter(function (element) {
        return !element.closest('.navbar, .mobile-menu, .chat-fab, .footer-bottom') && element.id !== 'backTop';
    });

    if (!elements.length) {
        return;
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || typeof IntersectionObserver === 'undefined') {
        elements.forEach(function (element) {
            element.classList.add('is-visible');
        });
        return;
    }

    const staggerGroups = [
        { cardClass: 'stat-card', gridSelector: '.stats-grid', revealClass: 'reveal-stagger-card', delayStep: 240 },
        { cardClass: 'alat-card', gridSelector: '.alat-grid', revealClass: 'reveal-stagger-card', delayStep: 240 },
        { cardClass: 'peralatan-card', gridSelector: '.peralatan-grid', revealClass: 'reveal-peralatan-card', delayStep: 260 },
    ];

    function applyStaggerDelay(element, fallbackIndex) {
        const groupConfig = staggerGroups.find(function (config) {
            return element.classList.contains(config.cardClass);
        });

        if (!groupConfig) {
            return Math.min((fallbackIndex % 7) * 120, 600);
        }

        const grid = element.closest(groupConfig.gridSelector);
        const cardIndex = grid
            ? Array.from(grid.querySelectorAll('.' + groupConfig.cardClass)).indexOf(element)
            : fallbackIndex;

        element.classList.add(groupConfig.revealClass);
        return Math.max(cardIndex, 0) * groupConfig.delayStep;
    }

    elements.forEach(function (element, index) {
        const delay = applyStaggerDelay(element, index);
        element.classList.add('reveal-on-scroll');
        element.style.setProperty('--reveal-delay', delay + 'ms');
    });

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) {
                return;
            }

            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
        });
    }, {
        threshold: 0.18,
        rootMargin: '0px 0px -6% 0px',
    });

    elements.forEach(function (element) {
        observer.observe(element);
    });
}

function animateCounter(id, target, duration) {
    const element = document.getElementById(id);
    const numericTarget = Number(target || 0);

    if (!element) {
        return;
    }

    if (numericTarget <= 0) {
        element.textContent = '0';
        return;
    }

    let start = 0;
    const safeDuration = Number(duration || 1600);
    const step = Math.max(numericTarget / (safeDuration / 16), 1);
    const timer = window.setInterval(function () {
        start += step;
        if (start >= numericTarget) {
            element.textContent = numericTarget.toLocaleString('id-ID');
            window.clearInterval(timer);
            return;
        }
        element.textContent = Math.floor(start).toLocaleString('id-ID');
    }, 16);
}

function initLandingCounters() {
    const statsSection = document.querySelector('.traffic');
    const stats = readLandingJson('landing-stats-data', {});
    let counted = false;

    function runCounters() {
        if (counted) {
            return;
        }
        counted = true;
        animateCounter('ctr1', stats.kegiatan_berjalan);
        animateCounter('ctr2', stats.kegiatan_selesai);
        animateCounter('ctr3', stats.total_kegiatan_survei);
        animateCounter('ctr4', stats.jumlah_peralatan_survei);
    }

    if (!statsSection || typeof IntersectionObserver === 'undefined') {
        runCounters();
        return;
    }

    const observer = new IntersectionObserver(function (entries) {
        if (entries[0] && entries[0].isIntersecting) {
            runCounters();
            observer.disconnect();
        }
    }, { threshold: 0.3 });

    observer.observe(statsSection);
}

function hasChartData(chartPayload) {
    return Array.isArray(chartPayload?.labels)
        && Array.isArray(chartPayload?.data)
        && chartPayload.labels.length > 0
        && chartPayload.data.some(function (value) { return Number(value || 0) > 0; });
}

function showChartEmpty(canvasId) {
    const canvas = document.getElementById(canvasId);
    const empty = document.querySelector('[data-chart-empty="' + canvasId + '"]');

    if (canvas) {
        canvas.classList.add('is-hidden');
    }
    if (empty) {
        empty.classList.remove('is-hidden');
    }
}

function initLandingCharts() {
    if (typeof Chart === 'undefined') {
        return;
    }

    const charts = readLandingJson('landing-chart-data', {});
    renderLandingBarChart('chartSurvei', charts.survei, 'Jumlah Kegiatan', false);
    renderLandingPieChart('chartLayanan', charts.layanan);
    renderLandingBarChart('chartLapangan', charts.pengukuran, 'Jumlah Titik/Lintasan', true);
}

function renderLandingBarChart(canvasId, chartPayload, label, horizontal) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return;
    }

    if (!hasChartData(chartPayload)) {
        showChartEmpty(canvasId);
        return;
    }

    new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: chartPayload.labels,
            datasets: [{
                label: label,
                data: chartPayload.data,
                backgroundColor: chartPayload.colors,
                borderColor: chartPayload.colors,
                borderRadius: 7,
                borderSkipped: false,
                maxBarThickness: horizontal ? 34 : 52,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: horizontal ? 'y' : 'x',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return 'Total: ' + Number(context.raw || 0).toLocaleString('id-ID');
                        },
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: horizontal,
                    grid: { display: horizontal, color: '#f0f4f6' },
                    ticks: { precision: 0, font: { family: 'Poppins', size: 10 } },
                },
                y: {
                    beginAtZero: !horizontal,
                    grid: { display: !horizontal, color: '#f0f4f6' },
                    ticks: { precision: 0, font: { family: 'Poppins', size: 10 } },
                },
            },
        },
    });
}

function renderLandingPieChart(canvasId, chartPayload) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        return;
    }

    if (!hasChartData(chartPayload)) {
        showChartEmpty(canvasId);
        return;
    }

    new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: chartPayload.labels,
            datasets: [{
                data: chartPayload.data,
                backgroundColor: chartPayload.colors,
                borderWidth: 2,
                borderColor: '#fff',
                hoverOffset: 10,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Poppins', size: 10 }, padding: 12, boxWidth: 12 },
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || 'Data';
                            return label + ': ' + Number(context.raw || 0).toLocaleString('id-ID');
                        },
                    },
                },
            },
        },
    });
}
