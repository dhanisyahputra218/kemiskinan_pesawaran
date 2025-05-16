// Register ChartJS plugins
Chart.register(ChartDataLabels);

// Global chart options
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        datalabels: {
            color: '#1e293b',
            font: {
                weight: '500'
            },
            formatter: function(value) {
                if (typeof value === 'number') {
                    return value.toLocaleString('id-ID');
                }
                return value;
            }
        },
        legend: {
            position: 'bottom',
            labels: {
                usePointStyle: true,
                padding: 20
            }
        }
    }
};

// Initialize map
const map = L.map('map').setView([-5.4981, 105.1733], 10);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: ' OpenStreetMap contributors'
}).addTo(map);

// Global state
let currentFilters = {
    year: '',
    kecamatan: '',
    desa: ''
};

let markers = []; // Store markers for cleanup

// Kecamatan name mapping
const kecamatanMapping = {
    'Gedung Tataan': 'Gedong Tataan',
    'Way Lima': 'Way Lima',
    'Kedondong': 'Kedondong',
    'Negeri Katon': 'Negeri Katon',
    'Tegineneng': 'Tegineneng',
    'Padang Cermin': 'Padang Cermin',
    'Punduh Pidada': 'Punduh Pidada',
    'Way Khilau': 'Way Khilau',
    'Way Ratai': 'Way Ratai',
    'Teluk Pandan': 'Teluk Pandan',
    'Marga Punduh': 'Marga Punduh'
};

// Initialize filters
async function initializeFilters() {
    try {
        const response = await fetch('/api/filters');
        const data = await response.json();
        
        const yearSelect = document.getElementById('year');
        const kecamatanSelect = document.getElementById('kecamatan');
        
        // Clear existing options
        yearSelect.innerHTML = '<option value="">Pilih Tahun</option>';
        kecamatanSelect.innerHTML = '<option value="">Semua Kecamatan</option>';
        
        // Populate year filter
        data.tahun.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        });
        
        // Populate kecamatan filter
        data.kecamatan.forEach(kec => {
            const option = document.createElement('option');
            option.value = kec.id;
            option.textContent = kec.nama;
            kecamatanSelect.appendChild(option);
        });
        
        // Set event listeners
        yearSelect.addEventListener('change', handleFilterChange);
        kecamatanSelect.addEventListener('change', handleKecamatanChange);
        document.getElementById('desa').addEventListener('change', handleFilterChange);
        
        // Initialize with latest data
        if (data.tahun.length > 0) {
            yearSelect.value = data.tahun[data.tahun.length - 1];
            handleFilterChange();
        }
    } catch (error) {
        console.error('Error initializing filters:', error);
    }
}

// Handle kecamatan change
async function handleKecamatanChange(event) {
    const kecamatanId = event.target.value;
    const desaSelect = document.getElementById('desa');
    
    // Reset desa dropdown
    desaSelect.disabled = !kecamatanId;
    desaSelect.innerHTML = '<option value="">Semua Desa</option>';
    
    if (kecamatanId) {
        try {
            const response = await fetch(`/api/desa/${kecamatanId}`);
            const desas = await response.json();
            
            desas.forEach(desa => {
                const option = document.createElement('option');
                option.value = desa;
                option.textContent = desa;
                desaSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading desas:', error);
        }
    }
    
    handleFilterChange();
}

// Handle filter changes
async function handleFilterChange() {
    currentFilters = {
        year: document.getElementById('year').value,
        kecamatan: document.getElementById('kecamatan').value,
        desa: document.getElementById('desa').value
    };
    
    await updateDashboard();
}

// Update dashboard data
async function updateDashboard() {
    try {
        console.log('Updating dashboard with filters:', currentFilters);
        
        // Show loading state
        document.querySelectorAll('.stat-box, .chart-box').forEach(el => {
            el.classList.add('loading');
        });
        
        // Fetch updated data
        const queryString = createQueryString();
        console.log('Query string:', queryString);
        
        // Fetch data for map
        const mapResponse = await fetch('/api/map-data' + queryString);
        console.log('Map response status:', mapResponse.status);
        if (!mapResponse.ok) throw new Error('Failed to fetch map data');
        const mapData = await mapResponse.json();
        console.log('Map data received:', mapData);
        
        // Update visualizations
        await updateMap(mapData);
        await updateStatistics();
        await updatePovertyDistribution();
        await updatePovertyTrend();
        await updateIncomeExpense();
        await updateIPM();
        
        // Remove loading state
        document.querySelectorAll('.stat-box, .chart-box').forEach(el => {
            el.classList.remove('loading');
        });
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// Update statistics
async function updateStatistics() {
    try {
        const response = await fetch('/api/statistics' + createQueryString());
        if (!response.ok) throw new Error('Failed to fetch statistics');
        const stats = await response.json();

        // Update the statistics display
        const elements = {
            'total-pendapatan': stats.total_pendapatan,
            'total-pengeluaran': stats.total_pengeluaran,
            'bpk-umkm': stats.bpk_umkm,
            'persentase-pengangguran': stats.persentase_pengangguran,
            'persentase-kemiskinan': stats.persentase_kemiskinan
        };

        // Update each element with proper formatting
        for (const [id, value] of Object.entries(elements)) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = id.includes('persentase') ? 
                    formatPercentage(value) : 
                    formatCurrency(value);
            }
        }

        console.log('Updated statistics:', stats);
    } catch (error) {
        console.error('Error updating statistics:', error);
    }
}

// Format functions
function formatCurrency(value) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

function formatPercentage(value) {
    return value.toLocaleString('id-ID', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).replace('.', ',') + '%';
}

async function updateMap(data) {
    try {
        // Clear existing layers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];

        // Process data to match CSV format
        const processedData = Array.isArray(data) ? data.map(item => {
            return {
                Kecamatan: item.kecamatan,
                'Jum Penduduk': item.total_population / 1000,
                'Persentase Pen Miskin': item.poverty_percentage,
                'Jumlah Pen Miskin': item.poor_population,
                'IPM(indeks pembangunan manusia)': item.ipm,
                'Persentase Pengangguran': item.pengangguran
            };
        }) : [];

        // Add GeoJSON layer
        const geoJsonLayer = L.geoJSON(kecamatan_kab_pesawaran, {
            style: function(feature) {
                try {
                    const kecamatanName = feature.properties.kecamatan || feature.properties.name || feature.properties.NAME_3;
                    const mappedName = kecamatanMapping[kecamatanName] || kecamatanName;
                    
                    // Find matching data
                    const kecamatanData = processedData.find(d => 
                        d.Kecamatan && d.Kecamatan.toLowerCase() === mappedName.toLowerCase()
                    );

                    // Get poverty percentage
                    let persentaseKemiskinan = 0;
                    if (kecamatanData) {
                        persentaseKemiskinan = parseFloat(kecamatanData['Persentase Pen Miskin']);
                    }
                    
                    // Color based on poverty percentage
                    const color = persentaseKemiskinan > 35 ? '#ef4444' :  // Merah untuk >35%
                                persentaseKemiskinan > 25 ? '#f97316' :  // Oranye untuk 25-35%
                                persentaseKemiskinan > 15 ? '#eab308' :  // Kuning untuk 15-25%
                                persentaseKemiskinan > 5 ? '#84cc16' :  // Hijau muda untuk 5-15%
                                '#22c55e';  // Hijau tua untuk <5%

                    return {
                        fillColor: color,
                        weight: 2,
                        opacity: 1,
                        color: 'white',
                        dashArray: '3',
                        fillOpacity: 0.7
                    };
                } catch (error) {
                    console.error('Error in style function:', error);
                    return defaultStyle;
                }
            },
            onEachFeature: function(feature, layer) {
                try {
                    const kecamatanName = feature.properties.kecamatan || feature.properties.name || feature.properties.NAME_3;
                    const mappedName = kecamatanMapping[kecamatanName] || kecamatanName;
                    
                    // Find matching data
                    const kecamatanData = processedData.find(d => 
                        d.Kecamatan && d.Kecamatan.toLowerCase() === mappedName.toLowerCase()
                    );

                    // Create popup content
                    let popupContent = `<div class="popup-content">
                        <h4>${mappedName}</h4>`;
                    
                    if (kecamatanData) {
                        popupContent += `
                        <p><strong>Jumlah Penduduk:</strong> ${formatNumber(kecamatanData['Jum Penduduk'] * 1000)}</p>
                        <p><strong>Persentase Kemiskinan:</strong> ${formatPercentage(kecamatanData['Persentase Pen Miskin'])}</p>
                        <p><strong>Jumlah Penduduk Miskin:</strong> ${formatNumber(kecamatanData['Jumlah Pen Miskin'])}</p>
                        <p><strong>IPM:</strong> ${kecamatanData['IPM(indeks pembangunan manusia)'].toFixed(2)}</p>
                        <p><strong>Persentase Pengangguran:</strong> ${formatPercentage(kecamatanData['Persentase Pengangguran'])}</p>`;
                    } else {
                        popupContent += `<p class="no-data">Data tidak tersedia untuk kecamatan ini</p>`;
                    }

                    popupContent += `</div>`;
                    layer.bindPopup(popupContent);
                } catch (error) {
                    console.error('Error in popup creation:', error);
                    layer.bindPopup(`<div class="popup-content"><p class="no-data">Error loading data</p></div>`);
                }
            }
        }).addTo(map);

        markers.push(geoJsonLayer);
        
        console.log('Map updated with data:', processedData);
    } catch (error) {
        console.error('Error updating map:', error);
    }
}

// Chart update functions
async function updatePovertyDistribution() {
    try {
        const response = await fetch('/api/poverty-distribution' + createQueryString());
        if (!response.ok) throw new Error('Failed to fetch poverty distribution data');
        const data = await response.json();
        
        const ctx = document.getElementById('povertyDistributionChart');
        if (ctx.chart) ctx.chart.destroy();
        
        ctx.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Jumlah Penduduk Miskin',
                    data: data.data,
                    backgroundColor: '#2563eb'
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error updating poverty distribution chart:', error);
    }
}

async function updatePovertyTrend() {
    try {
        const response = await fetch('/api/poverty-trend' + createQueryString());
        if (!response.ok) throw new Error('Failed to fetch poverty trend data');
        const data = await response.json();
        
        const ctx = document.getElementById('povertyTrendChart');
        if (ctx.chart) ctx.chart.destroy();
        
        ctx.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Persentase Kemiskinan',
                    data: data.data,
                    borderColor: '#2563eb',
                    tension: 0.1
                }]
            },
            options: chartOptions
        });
    } catch (error) {
        console.error('Error updating poverty trend chart:', error);
    }
}

async function updateIncomeExpense() {
    try {
        const response = await fetch('/api/income-expense' + createQueryString());
        if (!response.ok) throw new Error('Failed to fetch income/expense data');
        const data = await response.json();
        
        const ctx = document.getElementById('incomeExpenseChart');
        if (ctx.chart) ctx.chart.destroy();
        
        ctx.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Pendapatan',
                        data: data.income,
                        backgroundColor: '#22c55e'
                    },
                    {
                        label: 'Pengeluaran',
                        data: data.expense,
                        backgroundColor: '#ef4444'
                    }
                ]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error updating income/expense chart:', error);
    }
}

async function updateIPM() {
    try {
        const response = await fetch('/api/ipm' + createQueryString());
        if (!response.ok) throw new Error('Failed to fetch IPM data');
        const data = await response.json();
        
        const ctx = document.getElementById('ipmChart');
        if (ctx.chart) ctx.chart.destroy();
        
        ctx.chart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'IPM',
                    data: data.data,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.2)'
                }]
            },
            options: chartOptions
        });
    } catch (error) {
        console.error('Error updating IPM chart:', error);
    }
}

// Utility functions
function createQueryString() {
    const params = new URLSearchParams();
    if (currentFilters.year) params.append('year', currentFilters.year);
    if (currentFilters.kecamatan) params.append('kecamatan', currentFilters.kecamatan);
    if (currentFilters.desa) params.append('desa', currentFilters.desa);
    return params.toString() ? `?${params.toString()}` : '';
}

// Format number with thousand separator
function formatNumber(value) {
    return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeFilters();
});
