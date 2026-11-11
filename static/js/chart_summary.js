/* Totals follow the values currently visible in each chart. */
function getChartTotal(chart) {
    const horizontal = chart.options?.indexAxis === 'y';
    return (chart.data?.datasets || []).reduce((total, dataset, datasetIndex) => {
        if (chart.isDatasetVisible && !chart.isDatasetVisible(datasetIndex)) {
            return total;
        }
        return total + (dataset.data || []).reduce((sum, point, index) => {
            if (chart.getDataVisibility && !chart.getDataVisibility(index)) {
                return sum;
            }
            const raw = point && typeof point === 'object' ? point[horizontal ? 'x' : 'y'] : point;
            const value = Number(raw);
            return sum + (Number.isFinite(value) ? value : 0);
        }, 0);
    }, 0);
}

function getChartTotalText(chart) {
    return 'Total: ' + getChartTotal(chart).toLocaleString('id-ID', { maximumFractionDigits: 6 });
}

function getChartNihilLines(chart) {
    if (!['grafik-instansi-internal', 'tv-instansi-internal'].includes(chart.canvas?.id)) {
        return [];
    }
    const counts = { BWS: 0, BBWS: 0 };
    (chart.data?.labels || []).forEach((label, index) => {
        const type = getBalaiType(label);
        // Legend visibility does not turn existing transactions into nihil.
        const hasTransaction = (chart.data.datasets || []).some(dataset => Number(dataset.data?.[index] || 0) > 0);
        if (type && !hasTransaction) {
            counts[type] += 1;
        }
    });
    return ['BWS', 'BBWS'].map(type => `${type} Nihil : ${counts[type].toLocaleString('id-ID')} Instansi`);
}

function showChartTotal(canvas, text) {
    const card = canvas?.closest('.dashboard-chart, [data-asset-chart-card], .chart-card');
    if (!card) {
        return;
    }
    let node = card.querySelector('.chart-total');
    if (!node) {
        let row = card.querySelector('.dashboard-chart__filters, .asset-chart-filter, .chart-header');
        if (!row) {
            const header = card.querySelector('.dashboard-chart__header');
            if (!header) {
                return;
            }
            row = document.createElement('div');
            header.appendChild(row);
        }
        row.classList.add('chart-meta');
        node = document.createElement('span');
        node.className = 'chart-total';
        node.setAttribute('aria-live', 'polite');
        row.appendChild(node);
    }
    if (node.textContent !== text) {
        node.textContent = text;
    }
    node.hidden = false;
}

function showChartNihil(canvas, lines) {
    const card = canvas?.closest('.dashboard-chart');
    if (!card) {
        return;
    }
    let footer = card.querySelector('.chart-nihil');
    if (!lines.length) {
        if (footer) footer.hidden = true;
        return;
    }
    if (!footer) {
        footer = document.createElement('div');
        footer.className = 'chart-nihil';
        footer.setAttribute('aria-live', 'polite');
        card.appendChild(footer);
    }
    if (footer.textContent !== lines.join('')) {
        footer.replaceChildren(...lines.map(line => {
            const badge = document.createElement('span');
            badge.className = 'chart-nihil__item';
            badge.textContent = line;
            return badge;
        }));
    }
    footer.hidden = false;
}

function syncChartTotal(chart) {
    const slide = chart.canvas?.closest('[data-tv-slide]');
    if (!slide || slide.classList.contains('is-active')) {
        showChartTotal(chart.canvas, getChartTotalText(chart));
        showChartNihil(chart.canvas, getChartNihilLines(chart));
    }
}

function registerChartSummary() {
    Chart.register({ id: 'chartSummary', afterUpdate: syncChartTotal });
}
