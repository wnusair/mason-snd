document.addEventListener('DOMContentLoaded', function() {
    // Chart.js integration for data visualization
    const ctx = document.getElementById('performanceChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Event 1', 'Event 2', 'Event 3', 'Event 4', 'Event 5'],
                datasets: [{
                    label: 'Performance Score',
                    data: [12, 19, 3, 5, 2],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.2)',
                        'rgba(54, 162, 235, 0.2)',
                        'rgba(255, 206, 86, 0.2)',
                        'rgba(75, 192, 192, 0.2)',
                        'rgba(153, 102, 255, 0.2)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // CSV file upload handling
    const csvUploadForm = document.getElementById('csvUploadForm');
    if (csvUploadForm) {
        csvUploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('csvFile');
            if (fileInput.files.length === 0) {
                e.preventDefault();
                alert('Please select a CSV file to upload.');
            }
        });
    }
});
