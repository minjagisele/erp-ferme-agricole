document.addEventListener('DOMContentLoaded', function() {
    // Configuration commune
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } }
    };

    // Graphique Linéaire (Ventes)
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        new Chart(salesCtx, {
            type: 'line',
            data: {
                labels: DASHBOARD_DATA.salesLabels,
                datasets: [{
                    data: DASHBOARD_DATA.salesValues,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.05)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: chartOptions
        });
    }

    // Graphique Barres (Opérations)
    const opsCtx = document.getElementById('opsChart');
    if (opsCtx) {
        new Chart(opsCtx, {
            type: 'bar',
            data: {
                labels: DASHBOARD_DATA.opsLabels,
                datasets: [{
                    data: DASHBOARD_DATA.opsValues,
                    backgroundColor: '#198754',
                    borderRadius: 5
                }]
            },
            options: chartOptions
        });
    }
});