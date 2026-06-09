/* ========================================
   LANDING PAGE PUBLIC JS - SILEBAT
   Interaksi navbar, scroll reveal, counter, chart, dan back-to-top.
======================================== */
document.addEventListener('DOMContentLoaded', function () {
    initLandingNavbar();
    initBackToTop();
    initScrollReveal();
    initLandingCounters();
    initChartsWhenVisible();
    initEquipmentGalleries();
});

function initEquipmentGalleries() {
    const galleries = Array.from(document.querySelectorAll('[data-equipment-gallery]'));
    const lightbox = document.querySelector('[data-equipment-lightbox]');
    if (!galleries.length || !lightbox) {
        return;
    }

    const lightboxImage = lightbox.querySelector('[data-lightbox-image]');
    const lightboxTitle = lightbox.querySelector('[data-lightbox-title]');
    const lightboxCounter = lightbox.querySelector('[data-lightbox-counter]');
    const lightboxPrev = lightbox.querySelector('[data-lightbox-prev]');
    const lightboxNext = lightbox.querySelector('[data-lightbox-next]');
    let lightboxItems = [];
    let lightboxIndex = 0;

    function normalizeIndex(index, total) {
        return (index + total) % total;
    }

    function renderLightbox() {
        if (!lightboxItems.length) {
            return;
        }
        const item = lightboxItems[lightboxIndex];
        lightboxImage.src = item.src;
        lightboxImage.alt = item.alt;
        lightboxCounter.textContent = (lightboxIndex + 1) + ' / ' + lightboxItems.length;
        const showNav = lightboxItems.length > 1;
        lightboxPrev.hidden = !showNav;
        lightboxNext.hidden = !showNav;
    }

    function openLightbox(gallery, index) {
        lightboxItems = Array.from(gallery.querySelectorAll('[data-gallery-slide]')).map(function (image) {
            return { src: image.currentSrc || image.src, alt: image.alt };
        });
        lightboxIndex = normalizeIndex(index, lightboxItems.length);
        lightboxTitle.textContent = gallery.getAttribute('data-gallery-title') || 'Galeri Peralatan';
        renderLightbox();
        lightbox.classList.add('is-open');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.classList.add('equipment-lightbox-open');
        lightbox.querySelector('[data-lightbox-close]:not(.equipment-lightbox__backdrop)')?.focus();
    }

    function closeLightbox() {
        lightbox.classList.remove('is-open');
        lightbox.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('equipment-lightbox-open');
        lightboxImage.removeAttribute('src');
        lightboxItems = [];
    }

    function moveLightbox(step) {
        if (lightboxItems.length < 2) {
            return;
        }
        lightboxIndex = normalizeIndex(lightboxIndex + step, lightboxItems.length);
        renderLightbox();
    }

    galleries.forEach(function (gallery) {
        const slides = Array.from(gallery.querySelectorAll('[data-gallery-slide]'));
        const dots = Array.from(gallery.querySelectorAll('[data-gallery-dot]'));
        let index = 0;

        function show(nextIndex) {
            index = normalizeIndex(nextIndex, slides.length);
            slides.forEach(function (slide, slideIndex) {
                slide.classList.toggle('is-active', slideIndex === index);
            });
            dots.forEach(function (dot, dotIndex) {
                dot.classList.toggle('is-active', dotIndex === index);
            });
        }

        gallery.querySelector('[data-gallery-prev]')?.addEventListener('click', function () {
            show(index - 1);
        });
        gallery.querySelector('[data-gallery-next]')?.addEventListener('click', function () {
            show(index + 1);
        });
        gallery.querySelector('[data-gallery-open]')?.addEventListener('click', function () {
            openLightbox(gallery, index);
        });
    });

    lightbox.querySelectorAll('[data-lightbox-close]').forEach(function (button) {
        button.addEventListener('click', closeLightbox);
    });
    lightboxPrev.addEventListener('click', function () { moveLightbox(-1); });
    lightboxNext.addEventListener('click', function () { moveLightbox(1); });
    document.addEventListener('keydown', function (event) {
        if (!lightbox.classList.contains('is-open')) {
            return;
        }
        if (event.key === 'Escape') {
            closeLightbox();
        } else if (event.key === 'ArrowLeft') {
            moveLightbox(-1);
        } else if (event.key === 'ArrowRight') {
            moveLightbox(1);
        }
    });
}

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
    const menuLinks = Array.from(document.querySelectorAll('.nav-menu a, .mobile-menu a[href^="#"]'));
    const sections = Array.from(document.querySelectorAll('section[id], footer[id], .profil-features[id]'));
    let sectionPositions = [];
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

    function refreshSectionPositions() {
        sectionPositions = sections.map(function (section) {
            return {
                id: section.id,
                top: section.getBoundingClientRect().top + window.scrollY,
            };
        });
    }

    function setActiveLink(scrollTop) {
        if (!sectionPositions.length) {
            return;
        }

        const current = sectionPositions.reduce(function (activeId, section) {
            return scrollTop >= section.top - 120 ? section.id : activeId;
        }, sectionPositions[0].id);

        menuLinks.forEach(function (link) {
            link.classList.toggle('active', link.getAttribute('href') === '#' + current);
        });
    }

    function updateNavbarState() {
        const scrollTop = window.scrollY;
        if (navbar) {
            navbar.classList.toggle('scrolled', scrollTop > 40);
        }
        setActiveLink(scrollTop);
        ticking = false;
    }

    function requestNavbarUpdate() {
        if (ticking) {
            return;
        }
        ticking = true;
        requestAnimationFrameSafe(updateNavbarState);
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
    }

    refreshSectionPositions();
    updateNavbarState();

    window.addEventListener('resize', function () {
        refreshSectionPositions();
        if (window.innerWidth > 860) {
            setMobileMenu(false);
        }
        requestNavbarUpdate();
    }, { passive: true });
    window.addEventListener('load', refreshSectionPositions, { once: true });
    window.addEventListener('scroll', requestNavbarUpdate, { passive: true });
}

function initBackToTop() {
    const button = document.getElementById('backTop');
    let ticking = false;

    if (!button) {
        return;
    }

    function updateBackToTop() {
        button.classList.toggle('show', window.scrollY > 400);
        ticking = false;
    }

    window.addEventListener('scroll', function () {
        if (!ticking) {
            ticking = true;
            requestAnimationFrameSafe(updateBackToTop);
        }
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

function showChartMessage(canvasId, message, state) {
    const canvas = document.getElementById(canvasId);
    const empty = document.querySelector('[data-chart-empty="' + canvasId + '"]');
    const frame = document.querySelector('[data-chart-frame="' + canvasId + '"]');
    const wrap = canvas ? canvas.closest('.chart-wrap') : null;

    if (canvas) {
        canvas.classList.add('is-hidden');
    }
    if (frame) {
        frame.classList.add('is-hidden');
    }
    if (wrap) {
        wrap.classList.toggle('is-chart-error', state === 'error');
    }
    if (empty) {
        if (message) {
            empty.textContent = message;
        }
        empty.classList.toggle('landing-empty-state--error', state === 'error');
        empty.classList.remove('is-hidden');
    }
}

function showChartEmpty(canvasId) {
    showChartMessage(canvasId, null, 'empty');
}

function showChartError(canvasId, message) {
    showChartMessage(
        canvasId,
        message || 'Grafik gagal dimuat. Periksa koneksi internet atau muat ulang halaman.',
        'error'
    );
}

function splitLongChartWord(word, maxLength) {
    const chunks = [];
    const text = String(word || '');

    for (let index = 0; index < text.length; index += maxLength) {
        chunks.push(text.slice(index, index + maxLength));
    }

    return chunks;
}

function wrapChartLabel(value, maxLength) {
    const label = Array.isArray(value) ? value.join(' ') : String(value || '-');
    const words = label.split(/\s+/).filter(Boolean);
    const lines = [];
    let currentLine = '';

    words.forEach(function (word) {
        if (word.length > maxLength) {
            if (currentLine) {
                lines.push(currentLine);
                currentLine = '';
            }
            lines.push.apply(lines, splitLongChartWord(word, maxLength));
            return;
        }

        const candidate = currentLine ? currentLine + ' ' + word : word;
        if (candidate.length > maxLength) {
            if (currentLine) {
                lines.push(currentLine);
            }
            currentLine = word;
            return;
        }

        currentLine = candidate;
    });

    if (currentLine) {
        lines.push(currentLine);
    }

    return lines.length ? lines : ['-'];
}

function getLongestLabelLength(labels) {
    if (!Array.isArray(labels) || !labels.length) {
        return 0;
    }

    return labels.reduce(function (longest, label) {
        return Math.max(longest, String(label || '').length);
    }, 0);
}

function getBarChartLayoutPlan(canvas, labels, horizontal) {
    const frame = canvas.closest('.chart-canvas-frame');
    const scrollWrap = canvas.closest('.chart-wrap--scroll');

    if (!frame || !scrollWrap) {
        return null;
    }

    const labelCount = Array.isArray(labels) ? labels.length : 0;
    const longestLabelLength = getLongestLabelLength(labels);
    const currentWidth = scrollWrap.clientWidth || 0;
    const minVisibleWidth = Math.max(currentWidth, 320);
    const itemWidth = horizontal ? 56 : 72;
    const labelWidthBuffer = Math.min(Math.max(longestLabelLength - 18, 0) * 9, 260);
    const densityWidth = labelCount * itemWidth + labelWidthBuffer;
    const needsScroll = labelCount > (horizontal ? 5 : 4) || longestLabelLength > (horizontal ? 28 : 18);
    const minWidth = needsScroll ? Math.max(minVisibleWidth, densityWidth, 560) : minVisibleWidth;

    return {
        frame: frame,
        scrollWrap: scrollWrap,
        minWidth: Math.ceil(minWidth),
        needsScroll: needsScroll,
    };
}

function applyBarChartLayout(layoutPlan) {
    if (!layoutPlan) {
        return;
    }

    layoutPlan.frame.style.setProperty('--chart-min-width', layoutPlan.minWidth + 'px');
    layoutPlan.scrollWrap.classList.toggle('is-scrollable', layoutPlan.needsScroll);
}

function requestAnimationFrameSafe(callback) {
    if (typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(callback);
        return;
    }
    window.setTimeout(callback, 16);
}

function initChartsWhenVisible() {
    const chartsSection = document.querySelector('.charts');
    let initialized = false;

    function runOnce() {
        if (initialized) {
            return;
        }
        initialized = true;
        loadChartLibrary(chartsSection)
            .then(initLandingCharts)
            .catch(initLandingCharts);
    }

    if (!chartsSection || typeof IntersectionObserver === 'undefined') {
        runOnce();
        return;
    }

    const observer = new IntersectionObserver(function (entries) {
        if (entries[0] && entries[0].isIntersecting) {
            observer.disconnect();
            requestAnimationFrameSafe(runOnce);
        }
    }, {
        rootMargin: '240px 0px',
        threshold: 0.05,
    });

    observer.observe(chartsSection);
}

function loadChartLibrary(chartsSection) {
    if (typeof Chart !== 'undefined') {
        return Promise.resolve();
    }

    const scriptUrl = chartsSection?.dataset.chartjsUrl;
    if (!scriptUrl) {
        return Promise.reject(new Error('URL Chart.js tidak tersedia.'));
    }

    return new Promise(function (resolve, reject) {
        const existing = document.querySelector('script[data-chartjs-loader]');
        if (existing) {
            existing.addEventListener('load', resolve, { once: true });
            existing.addEventListener('error', reject, { once: true });
            return;
        }

        const script = document.createElement('script');
        script.src = scriptUrl;
        script.async = true;
        script.dataset.chartjsLoader = 'true';
        script.addEventListener('load', resolve, { once: true });
        script.addEventListener('error', reject, { once: true });
        document.head.appendChild(script);
    });
}

function initLandingCharts() {
    const charts = readLandingJson('landing-chart-data', {});
    const chartConfigs = [
        { type: 'bar', canvasId: 'chartSurvei', payload: charts.survei, label: 'Jumlah Kegiatan', horizontal: false },
        { type: 'doughnut', canvasId: 'chartLayanan', payload: charts.layanan },
        { type: 'bar', canvasId: 'chartLapangan', payload: charts.pengukuran, label: 'Jumlah Titik/Lintasan', horizontal: true },
        { type: 'bar', canvasId: 'chartInstansi', payload: charts.instansi, label: 'Jumlah Kegiatan', horizontal: false },
    ];

    const renderableConfigs = chartConfigs.filter(function (config) {
        if (!hasChartData(config.payload)) {
            showChartEmpty(config.canvasId);
            return false;
        }
        return true;
    });

    if (!renderableConfigs.length) {
        return;
    }

    if (typeof Chart === 'undefined') {
        const message = 'Grafik gagal dimuat karena library Chart.js tidak tersedia. Periksa koneksi internet/CDN lalu muat ulang halaman.';
        renderableConfigs.forEach(function (config) {
            showChartError(config.canvasId, message);
        });
        return;
    }

    requestAnimationFrameSafe(function () {
        const layoutPlans = renderableConfigs
            .filter(function (config) { return config.type === 'bar'; })
            .map(function (config) {
                const canvas = document.getElementById(config.canvasId);
                return canvas ? getBarChartLayoutPlan(canvas, config.payload.labels, config.horizontal) : null;
            });

        requestAnimationFrameSafe(function () {
            layoutPlans.forEach(applyBarChartLayout);
            renderableConfigs.forEach(function (config) {
                if (config.type === 'bar') {
                    renderLandingBarChart(config.canvasId, config.payload, config.label, config.horizontal);
                    return;
                }
                renderLandingPieChart(config.canvasId, config.payload);
            });
        });
    });
}

function getChartFontSize() {
    if (window.innerWidth >= 2200) {
        return 13;
    }
    return window.innerWidth <= 560 ? 11 : 12;
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

    const categoryAxis = horizontal ? 'y' : 'x';
    const categoryLabelLength = horizontal ? 22 : 14;
    const fontSize = getChartFontSize();
    const originalLabels = chartPayload.labels;

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
            animation: {
                duration: 380,
            },
            layout: {
                padding: {
                    bottom: horizontal ? 2 : 10,
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function (items) {
                            if (!items.length) {
                                return '';
                            }
                            return originalLabels[items[0].dataIndex] || 'Data';
                        },
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
                    ticks: {
                        precision: 0,
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0,
                        font: { family: 'Poppins', size: fontSize },
                        callback: function (value) {
                            if (categoryAxis === 'x') {
                                return wrapChartLabel(this.getLabelForValue(value), categoryLabelLength);
                            }
                            return Number(value || 0).toLocaleString('id-ID');
                        },
                    },
                },
                y: {
                    beginAtZero: !horizontal,
                    grid: { display: !horizontal, color: '#f0f4f6' },
                    ticks: {
                        precision: 0,
                        autoSkip: false,
                        font: { family: 'Poppins', size: fontSize },
                        callback: function (value) {
                            if (categoryAxis === 'y') {
                                return wrapChartLabel(this.getLabelForValue(value), categoryLabelLength);
                            }
                            return Number(value || 0).toLocaleString('id-ID');
                        },
                    },
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

    const fontSize = getChartFontSize();

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
            animation: {
                duration: 380,
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { font: { family: 'Poppins', size: fontSize }, padding: 14, boxWidth: 14 },
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
