# 🧠 Aegis AIOps Command Center

An AI-powered Kubernetes operations dashboard that combines real-time observability (Prometheus, Loki, Tempo) with **Google Gemini 3.1 Flash Lite** for automated root cause analysis and incident remediation.

![AIOps Command Center](https://img.shields.io/badge/AIOps-Command_Center-blue?style=for-the-badge)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Minikube-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini_3.1_Flash_Lite-4285F4?style=for-the-badge&logo=google&logoColor=white)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Overview

Aegis AIOps Command Center is a full-stack observability and incident management platform designed for Kubernetes environments. It aggregates telemetry data from multiple sources and uses **Google Gemini 3.1 Flash Lite** to perform intelligent root cause analysis on production incidents.

### Key Capabilities

- **Real-time telemetry dashboards** — Live metrics (Prometheus), logs (Loki), traces (Tempo), and Kubernetes events
- **AI-powered diagnosis** — Gemini 3.1 Flash Lite analyzes collected telemetry to identify root causes
- **Incident simulation** — Trigger controlled failure scenarios (slowdown, DB errors, memory leaks, crashes)
- **Automated remediation** — One-click rolling restart and state reset via Kubernetes API

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    Aegis AIOps Command Center                      │
│                                                                    │
│  ┌──────────────────────┐     ┌──────────────────────────────┐    │
│  │   Frontend (HTML/JS) │────▶│   FastAPI Backend (Python)    │    │
│  │   - Dashboard UI     │◀────│   - Telemetry Aggregation     │    │
│  │   - Charts (Chart.js)│     │   - AI Analysis Orchestration │    │
│  │   - Simulation Panel │     │   - K8s Operations            │    │
│  └──────────────────────┘     └──────────┬───────────────────┘    │
│                                          │                         │
└──────────────────────────────────────────┼─────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
             ┌──────▼──────┐    ┌─────────▼────────┐   ┌────────▼────────┐
             │  Prometheus  │    │      Loki        │   │     Tempo       │
             │  (Metrics)   │    │   (Log Agg.)     │   │   (Traces)      │
             └──────────────┘    └──────────────────┘   └─────────────────┘
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │   payment-api   │
                                  │ (Target Service)│
                                  └─────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  Gemini 3.1     │
                                  │  Flash Lite API │
                                  └─────────────────┘
```

---

## Features

| Feature | Description |
|---|---|
| 📊 **Live Metrics** | Request rate, error rate, latency, CPU, and memory from Prometheus |
| 📝 **Log Streaming** | Real-time Loki log aggregation with keyword filtering |
| 🔗 **Distributed Traces** | Tempo trace visualization with Gantt-style spans |
| ⚡ **K8s Events** | Live Kubernetes event monitoring for the target service |
| 🤖 **AI Root Cause Analysis** | Gemini 3.1 Flash Lite powered incident diagnosis |
| 🎭 **Incident Simulation** | Trigger slowdown, DB errors, memory leaks, and crash loops |
| 🔧 **Auto-Remediation** | Rolling restart + state reset via Kubernetes API |

---

## Prerequisites

- **Minikube** — Local Kubernetes cluster
- **Docker** — Container runtime (Minikube's built-in docker)
- **kubectl** — Kubernetes CLI
- **Helm** — Package manager for Kubernetes
- **Google Gemini API Key** — [Get one from Google AI Studio](https://aistudio.google.com/apikey)

### Observability Stack (deployed via Helm)

- Prometheus (kube-prometheus-stack)
- Grafana Loki
- Grafana Tempo
- OpenTelemetry Collector

---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd 09-aiops-command-center
```

### 2. Configure Environment Variables

Copy the example `.env` file and add your Gemini API key:

```bash
cp .env .env.local   # or just edit .env directly
```

Edit the `.env` file:

```env
# Required: Your Google Gemini API Key
GEMINI_API_KEY=your-actual-gemini-api-key-here

# Optional: Override the model (default: gemini-3.1-flash-lite)
GEMINI_MODEL=gemini-3.1-flash-lite
```

### 3. Create Kubernetes Secret for API Key

```bash
kubectl create secret generic gemini-api-secret \
  --from-literal=api-key="$(grep GEMINI_API_KEY .env | cut -d '=' -f2)"
```

### 4. Build & Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
1. Configure Minikube's Docker environment
2. Build `payment-api` and `command-center` Docker images
3. Deploy all resources to the Kubernetes cluster
4. Wait for rollout completion and print the access URL

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(required)* | Google Gemini API key for AI analysis |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Gemini model to use |
| `PROMETHEUS_URL` | `http://prometheus-operator-kube-p-prometheus.observability.svc.cluster.local:9090` | Prometheus server URL |
| `LOKI_URL` | `http://loki.observability.svc.cluster.local:3100` | Loki log aggregator URL |
| `TEMPO_URL` | `http://tempo.observability.svc.cluster.local:3200` | Tempo trace backend URL |
| `TARGET_SERVICE_URL` | `http://payment-api-service.default.svc.cluster.local:5000` | Target microservice URL |

---

## Deployment

### Access the Dashboard

After running `deploy.sh`, access the dashboard at:

```
http://<minikube-ip>:32009
```

Or use port-forwarding:

```bash
kubectl port-forward svc/command-center-service 8000:8000
# Visit http://localhost:8000
```

---

## Usage

### 1. Monitor System Health
The dashboard auto-refreshes every 3.5 seconds with live telemetry gauges, charts, logs, traces, and Kubernetes events.

### 2. Simulate Incidents
Use the **Incident Simulation Panel** to trigger controlled failures:
- **Slowdown** — Introduces artificial latency (simulates slow DB queries)
- **DB Conn Timeout** — Simulates database connection pool exhaustion
- **Memory Leak (OOM)** — Triggers memory growth leading to OOM kills
- **Pod Crash Loop** — Forces the pod to exit and enter CrashLoopBackOff

### 3. AI Root Cause Analysis
When an incident is triggered, the AI agent automatically:
1. Collects metrics, logs, traces, and K8s events
2. Sends telemetry context to Gemini 3.1 Flash Lite
3. Returns a structured diagnosis with **root cause** and **remediation steps**

You can also type custom queries in the console (e.g., *"Why is payment-api service slow?"*).

### 4. Auto-Remediate
Click the **Auto-Remediate** button to:
- Reset the simulation state to healthy
- Trigger a rolling restart of the payment-api deployment

---

## Project Structure

```
09-aiops-command-center/
├── .env                          # Environment variables (API keys)
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
├── deploy.sh                     # Build & deploy automation script
├── kubernetes.yaml               # All Kubernetes manifests (RBAC, Deployments, Services)
│
├── command-center/               # AIOps Command Center (FastAPI + Frontend)
│   ├── Dockerfile                # Container image definition
│   ├── main.py                   # FastAPI backend (telemetry aggregation + Gemini AI)
│   ├── requirements.txt          # Python dependencies
│   └── static/                   # Frontend assets
│       ├── index.html            # Dashboard HTML
│       ├── style.css             # UI styling
│       └── script.js             # Dashboard interactivity & API calls
│
└── payment-api/                  # Target microservice (failure simulation)
    ├── Dockerfile                # Container image definition
    ├── main.py                   # Flask app with simulation endpoints
    └── requirements.txt          # Python dependencies
```

---

## API Reference

### `GET /api/system-status`
Returns the current system health including pod status, metrics, logs, and events.

### `POST /api/simulate/{mode}`
Trigger a failure simulation. Modes: `healthy`, `slowdown`, `db_error`, `memory_leak`, `crash`.

### `POST /api/analyze`
Run AI root cause analysis.

**Request Body:**
```json
{
  "query": "Why is payment-api service down?",
  "namespace": "default",
  "service": "payment-api"
}
```

**Response:**
```json
{
  "query": "Why is payment-api service down?",
  "analysis": "### Diagnosis\n...",
  "telemetry": {
    "metrics": { ... },
    "logs": [ ... ],
    "events": [ ... ]
  }
}
```

### `POST /api/remediate`
Execute automated remediation (rolling restart + state reset).

---

## Troubleshooting

### Gemini API errors
- Verify your `GEMINI_API_KEY` is set correctly in `.env`
- Check API key permissions at [Google AI Studio](https://aistudio.google.com/apikey)
- The app will fall back to rule-based heuristics if the API is unreachable

### Pod not starting
```bash
kubectl logs deployment/command-center
kubectl describe pod -l app=command-center
```

### Metrics not showing
- Ensure the Prometheus ServiceMonitor is active: `kubectl get servicemonitor`
- Verify Prometheus is scraping: `kubectl port-forward svc/prometheus-operator-kube-p-prometheus 9090:9090 -n observability`

### Observability stack not deployed
Make sure you have Prometheus, Loki, Tempo, and OTel Collector installed in the `observability` namespace via Helm.

---

## License

This project is for educational and demonstration purposes.
