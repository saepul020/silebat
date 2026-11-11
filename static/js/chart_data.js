/* Shared institution classification and ordering for dashboard and TV charts. */
function getBalaiType(label) {
    const name = (Array.isArray(label) ? label.join(' ') : String(label || '')).trim();
    if (/^BBWS\b|^Balai\s+Besar\s+Wilayah\s+Sungai\b/i.test(name)) {
        return 'BBWS';
    }
    if (/^BWS\b|^Balai\s+Wilayah\s+Sungai\b/i.test(name)) {
        return 'BWS';
    }
    return '';
}

function sortInstansiCategories(categories, totals, key) {
    const prioritizeBalai = key === 'instansi-internal';

    return categories.slice().sort(function (left, right) {
        if (prioritizeBalai) {
            const leftPriority = Boolean(getBalaiType(left.label));
            const rightPriority = Boolean(getBalaiType(right.label));
            if (leftPriority !== rightPriority) {
                return leftPriority ? -1 : 1;
            }
        }

        const difference = Number(totals.get(right.id) || 0) - Number(totals.get(left.id) || 0);
        return difference || left.label.localeCompare(right.label, 'id', { sensitivity: 'base', numeric: true });
    });
}
