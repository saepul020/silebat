/* Shared ordering for dashboard and TV institution charts. */
function sortInstansiCategories(categories, totals, key) {
    const prioritizeBalai = key === 'instansi-internal';
    const balaiPattern = /^(?:BBWS|BWS)\b|^Balai\s+(?:Besar\s+)?Wilayah\s+Sungai\b/i;

    return categories.slice().sort(function (left, right) {
        if (prioritizeBalai) {
            const leftPriority = balaiPattern.test(left.label.trim());
            const rightPriority = balaiPattern.test(right.label.trim());
            if (leftPriority !== rightPriority) {
                return leftPriority ? -1 : 1;
            }
        }

        const difference = Number(totals.get(right.id) || 0) - Number(totals.get(left.id) || 0);
        return difference || left.label.localeCompare(right.label, 'id', { sensitivity: 'base', numeric: true });
    });
}
