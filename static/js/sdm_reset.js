(() => {
    const navigation = performance.getEntriesByType('navigation')[0];
    if (navigation?.type !== 'reload' || !window.location.search) return;

    const url = new URL(window.location.href);
    url.search = '';
    window.location.replace(url.href);
})();
