// State Management
let currentMode = 'healthy';
let systemLogs = [];
let charts = {};

// DOM Elements
const clusterPulse = document.getElementById('cluster-pulse');
const clusterStatusText = document.getElementById('cluster-status-text');
const globalRemediateBtn = document.getElementById('global-remediate-btn');
const queryForm = document.getElementById('ai-query-form');
const queryInput = document.getElementById('query-input');
const querySubmitBtn = document.getElementById('query-submit-btn');
const analysisOutput = document.getElementById('analysis-output');
const analysisLoader = document.getElementById('analysis-loader');
const logsContainer = document.getElementById('logs-container');
const logFilter = document.getElementById('log-filter');
const traceContainer = document.getElementById('trace-container');
const eventsContainer = document.getElementById('events-container');

// Gauge elements
const gPodStatus = document.getElementById('gauge-pod-status');
const gRestarts = document.getElementById('gauge-restarts');
const gActiveMode = document.getElementById('gauge-active-mode');
const gLatency = document.getElementById('gauge-latency');
const gErrorRate = document.getElementById('gauge-error-rate');
const gMemory = document.getElementById('gauge-memory');

// Initialize Charts
function initCharts() {
    // Chart 1: Requests & Errors
    const ctxReq = document.getElementById('chart-requests').getContext('2d');
    charts.requests = new Chart(ctxReq, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Request Rate (req/s)',
                    borderColor: '#00d2ff',
                    backgroundColor: 'rgba(0, 210, 255, 0.05)',
                    data: [],
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Error Rate (%)',
                    borderColor: '#ff1744',
                    backgroundColor: 'rgba(255, 23, 68, 0.05)',
                    data: [],
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#ff1744', font: { size: 9 } },
                    min: 0,
                    max: 100
                }
            },
            plugins: {
                legend: { labels: { color: '#cbd5e1', font: { size: 10 } } }
            }
        }
    });

    // Chart 2: Resources (CPU/Memory)
    const ctxRes = document.getElementById('chart-resources').getContext('2d');
    charts.resources = new Chart(ctxRes, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Memory (MB)',
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    data: [],
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'CPU Usage (Cores)',
                    borderColor: '#00e676',
                    backgroundColor: 'rgba(0, 230, 118, 0.05)',
                    data: [],
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#94a3b8', font: { size: 9 } }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#00e676', font: { size: 9 } }
                }
            },
            plugins: {
                legend: { labels: { color: '#cbd5e1', font: { size: 10 } } }
            }
        }
    });
}

// Update Chart Data
function updateCharts(metrics) {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    // Slide labels
    for (let key in charts) {
        const chart = charts[key];
        chart.data.labels.push(timestamp);
        if (chart.data.labels.length > 15) {
            chart.data.labels.shift();
        }
    }

    // Update Requests & Errors
    const reqData = charts.requests.data.datasets;
    reqData[0].data.push(metrics.request_rate || 0.0);
    reqData[1].data.push((metrics.error_rate || 0.0) * 100);
    if (reqData[0].data.length > 15) {
        reqData[0].data.shift();
        reqData[1].data.shift();
    }
    charts.requests.update();

    // Update Resources
    const resData = charts.resources.data.datasets;
    resData[0].data.push(metrics.memory_mb || 15.0);
    resData[1].data.push(metrics.cpu_cores || 0.005);
    if (resData[0].data.length > 15) {
        resData[0].data.shift();
        resData[1].data.shift();
    }
    charts.resources.update();
}

// Render Traces (Gantt View representation of telemetry)
function renderTraces(mode, metrics) {
    traceContainer.innerHTML = '';
    
    let spans = [];
    if (mode === 'healthy') {
        const duration = Math.round((metrics.latency || 0.05) * 1000);
        spans = [
            { name: 'GET /api/pay', duration: `${duration}ms`, pct: 100, type: 'http', statement: 'payment-api - Request received successfully' },
            { name: 'db_verify_payment', duration: `${Math.round(duration * 0.8)}ms`, pct: 80, type: 'db', statement: 'SELECT * FROM accounts WHERE id = 87834' }
        ];
    } else if (mode === 'slowdown') {
        const totalDuration = Math.round((metrics.latency || 4.5) * 1000);
        const dbDuration = totalDuration - 200;
        spans = [
            { name: 'GET /api/pay', duration: `${totalDuration}ms`, pct: 100, type: 'http_slow', statement: 'payment-api - Execution blocked by DB thread pool' },
            { name: 'simulated_db_query', duration: `${dbDuration}ms`, pct: 90, type: 'db_slow', statement: 'SELECT * FROM payments WHERE status = \'pending\'' }
        ];
    } else if (mode === 'db_error') {
        spans = [
            { name: 'GET /api/pay', duration: '3000ms', pct: 100, type: 'failed', statement: 'payment-api - 500 Internal Server Error' },
            { name: 'simulated_db_connection', duration: '3000ms', pct: 100, type: 'failed', statement: 'Exception: Connection pool exhausted (max_connections=100)' }
        ];
    } else if (mode === 'memory_leak') {
        spans = [
            { name: 'GET /api/pay', duration: '45ms', pct: 100, type: 'http', statement: 'payment-api - Execution processing normally (RAM leak active)' },
            { name: 'db_verify_payment', duration: '35ms', pct: 75, type: 'db', statement: 'SELECT * FROM accounts WHERE id = 87834' }
        ];
    } else {
        // Crash or offline
        spans = [
            { name: 'GET /api/pay', duration: 'N/A', pct: 100, type: 'failed', statement: 'Connection Timeout / Service Offline' }
        ];
    }

    spans.forEach(span => {
        const item = document.createElement('div');
        item.className = 'trace-bar';
        
        let pClass = 'trace-progress-bar';
        if (span.type.includes('slow')) pClass += ' slow';
        if (span.type === 'failed') pClass += ' failed';

        item.innerHTML = `
            <div class="trace-header-info">
                <span class="trace-name">${span.name}</span>
                <span class="trace-duration">${span.duration}</span>
            </div>
            <div class="trace-progress-bg">
                <div class="${pClass}" style="width: ${span.pct}%;"></div>
            </div>
            <div class="trace-statement">${span.statement}</div>
        `;
        traceContainer.appendChild(item);
    });
}

// Fetch System Status & Update Dashboards
async function fetchSystemStatus() {
    try {
        const response = await fetch('/api/system-status');
        if (!response.ok) throw new Error('API unreachable');
        
        const data = await response.json();
        
        // Update cluster status indicator
        clusterPulse.className = 'pulse-dot green';
        clusterStatusText.textContent = 'Connected to minikube';
        
        // Update Active Mode state and buttons
        currentMode = data.target_mode;
        updateActiveModeUI(data.target_mode);
        
        // Update Gauges
        gPodStatus.textContent = data.pod_status;
        gPodStatus.className = 'gauge-value ' + (data.pod_status === 'Running' ? 'healthy' : (data.pod_status.includes('Found') || data.pod_status.includes('Offline') ? 'danger' : 'warning'));
        
        gRestarts.textContent = data.pod_restarts;
        gRestarts.className = 'gauge-value ' + (data.pod_restarts > 0 ? 'warning' : 'healthy');
        
        gActiveMode.textContent = data.target_mode.toUpperCase();
        gActiveMode.className = 'gauge-value ' + (data.target_mode === 'healthy' ? 'healthy' : (data.target_mode === 'slowdown' ? 'warning' : 'danger'));
        
        const latencyMs = Math.round((data.metrics.latency || 0.0) * 1000);
        gLatency.textContent = `${latencyMs} ms`;
        gLatency.className = 'gauge-value ' + (latencyMs > 1000 ? 'danger' : (latencyMs > 200 ? 'warning' : 'healthy'));
        
        const errPct = Math.round((data.metrics.error_rate || 0.0) * 100);
        gErrorRate.textContent = `${errPct}%`;
        gErrorRate.className = 'gauge-value ' + (errPct > 10 ? 'danger' : (errPct > 0 ? 'warning' : 'healthy'));
        
        gMemory.textContent = `${data.metrics.memory_mb} MB`;
        gMemory.className = 'gauge-value ' + (data.metrics.memory_mb > 150 ? 'danger' : (data.metrics.memory_mb > 80 ? 'warning' : 'healthy'));
        
        // Update Charts
        updateCharts(data.metrics);
        
        // Render logs
        systemLogs = data.logs || [];
        renderLogs();
        
        // Render traces Gantt
        renderTraces(data.target_mode, data.metrics);
        
        // Render Events
        renderEvents(data.events || []);

    } catch (error) {
        console.error('Status fetch failed:', error);
        clusterPulse.className = 'pulse-dot red';
        clusterStatusText.textContent = 'Cluster connection lost!';
    }
}

// Update Active Button in Controls UI
function updateActiveModeUI(mode) {
    document.querySelectorAll('.sim-btn').forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Trigger simulation change
async function setSimulationMode(mode) {
    try {
        showToast(`Triggering simulated incident: ${mode.toUpperCase()}...`);
        const response = await fetch(`/api/simulate/${mode}`, { method: 'POST' });
        if (!response.ok) throw new Error('Simulation API error');
        
        const data = await response.json();
        showToast(`Incident mode successfully set to: ${mode}`, 'success');
        
        // Query AI immediately for active simulation
        let aiQuery = '';
        if (mode === 'slowdown') aiQuery = 'Why is payment-api service slow?';
        else if (mode === 'db_error') aiQuery = 'Why is payment-api failing with 500 errors?';
        else if (mode === 'memory_leak') aiQuery = 'Why is payment-api memory spikes?';
        else if (mode === 'crash') aiQuery = 'Why is payment-api service down?';
        
        if (aiQuery) {
            queryInput.value = aiQuery;
            runAIAnalysis(aiQuery);
        }
        
        fetchSystemStatus();
    } catch (error) {
        console.error('Trigger simulation failed:', error);
        showToast('Failed to trigger simulation mode.', 'error');
    }
}

// Render Loki Logs with filtering
function renderLogs() {
    const filterText = logFilter.value.toLowerCase();
    logsContainer.innerHTML = '';
    
    const filtered = systemLogs.filter(line => line.toLowerCase().includes(filterText));
    
    if (filtered.length === 0) {
        logsContainer.textContent = 'No matching logs scraped.';
        return;
    }
    
    filtered.forEach(line => {
        const span = document.createElement('span');
        // Highlight terms
        let styledLine = line;
        if (line.toLowerCase().includes('error') || line.toLowerCase().includes('fail') || line.toLowerCase().includes('timeout')) {
            span.style.color = '#ff1744';
            span.style.fontWeight = '500';
        } else if (line.toLowerCase().includes('warning') || line.toLowerCase().includes('warn')) {
            span.style.color = '#ffa000';
        } else if (line.toLowerCase().includes('success') || line.toLowerCase().includes('healthy')) {
            span.style.color = '#00e676';
        }
        
        span.textContent = styledLine + '\n';
        logsContainer.appendChild(span);
    });
    
    // Auto scroll logs console to bottom
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Render Events Table
function renderEvents(events) {
    eventsContainer.innerHTML = '';
    if (events.length === 0) {
        eventsContainer.innerHTML = '<tr><td colspan="6" class="text-center">No recent events.</td></tr>';
        return;
    }

    events.forEach(ev => {
        const tr = document.createElement('tr');
        const badgeClass = ev.type.toLowerCase() === 'warning' ? 'badge-event-type warning' : 'badge-event-type normal';
        
        tr.innerHTML = `
            <td><span class="${badgeClass}">${ev.type}</span></td>
            <td><strong>${ev.reason}</strong></td>
            <td>${ev.object}</td>
            <td>${ev.message}</td>
            <td>${ev.count}</td>
            <td style="white-space: nowrap;">${ev.last_timestamp}</td>
        `;
        eventsContainer.appendChild(tr);
    });
}

// Execute Auto Remediation
async function executeRemediation() {
    try {
        showToast('Initiating automated remediation rollback...');
        const response = await fetch('/api/remediate', { method: 'POST' });
        if (!response.ok) throw new Error('Remediation error');
        
        const data = await response.json();
        showToast(data.message, 'success');
        
        // Reset query text
        analysisOutput.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-circle-check" style="color: var(--color-success); font-size: 36px; margin-bottom: 12px;"></i>
                <p><strong>Remediation Dispatched!</strong></p>
                <p>System state has been reset to healthy, and rolling deployment is restarting the pods.</p>
            </div>
        `;
        
        fetchSystemStatus();
    } catch (error) {
        console.error('Remediation failed:', error);
        showToast('Automation failure: Remediation failed to run.', 'error');
    }
}

// Call Gemini 3.1 Flash Lite model for SRE analysis
async function runAIAnalysis(query) {
    analysisOutput.style.display = 'none';
    analysisLoader.style.display = 'flex';
    querySubmitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, service: 'payment-api', namespace: 'default' })
        });
        
        if (!response.ok) throw new Error('Analysis request failed');
        
        const data = await response.json();
        
        // Render markdown content using marked.js
        analysisOutput.innerHTML = marked.parse(data.analysis);
        showToast('AIOps diagnosis ready', 'success');
        
    } catch (error) {
        console.error('Analysis failed:', error);
        analysisOutput.innerHTML = `
            <div class="empty-state" style="color: var(--color-danger)">
                <i class="fa-solid fa-triangle-exclamation empty-icon"></i>
                <p>Failed to run SRE Analysis: ${error.message}</p>
            </div>
        `;
        showToast('AIOps analysis failed.', 'error');
    } finally {
        analysisLoader.style.display = 'none';
        analysisOutput.style.display = 'block';
        querySubmitBtn.disabled = false;
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 4000);
}

// Tab Switching
document.querySelectorAll('.tab-link').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all
        document.querySelectorAll('.tab-link').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        // Add active class
        button.classList.add('active');
        const tabId = button.dataset.tab;
        document.getElementById(tabId).classList.add('active');
    });
});

// Event Listeners
document.querySelectorAll('.sim-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        setSimulationMode(mode);
    });
});

document.querySelectorAll('.preset-tag').forEach(tag => {
    tag.addEventListener('click', () => {
        const text = tag.textContent;
        queryInput.value = text;
        runAIAnalysis(text);
    });
});

queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (query) {
        runAIAnalysis(query);
    }
});

globalRemediateBtn.addEventListener('click', () => {
    executeRemediation();
});

logFilter.addEventListener('input', () => {
    renderLogs();
});

// Setup Page
window.addEventListener('load', () => {
    initCharts();
    fetchSystemStatus();
    
    // Poll system status every 3.5 seconds
    setInterval(fetchSystemStatus, 3500);
});
