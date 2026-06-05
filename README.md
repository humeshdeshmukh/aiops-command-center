# Aegis AIOps Command Center

A production-grade AI-powered Kubernetes operations dashboard that detects incidents, performs root cause analysis using **Google Gemini 3.1 Flash Lite**, and auto-remediates failures — all from a single interface.

> **Portfolio Project by [Humesh Deshmukh](https://github.com/humeshdeshmukh)**
> Built to demonstrate end-to-end DevOps, SRE, and AI/ML integration skills.

![Dashboard Preview](docs/images/dashboard-preview.png)

---

## Why I Built This

Modern SRE teams drown in alerts, dashboards, and runbooks. I wanted to build a system that doesn't just *show* you what's broken — it *tells* you why and *fixes* it automatically.

This project brings together everything I've learned about Kubernetes, observability, and AI:

- Designing a **full observability pipeline** (metrics, logs, traces) from scratch
- Building a **real-time dashboard** with glassmorphism UI and live data polling
- Integrating **Google Gemini** as an AI SRE agent that reasons over telemetry
- Implementing **chaos engineering** with controlled failure simulations
- Automating **incident remediation** via the Kubernetes API

---

## Skills Demonstrated

| Area | Technologies & Concepts |
|---|---|
| **Kubernetes** | Deployments, Services, RBAC, ServiceAccounts, Secrets, Rolling Restarts, ServiceMonitor CRDs |
| **Observability** | Prometheus metrics, Grafana Loki log aggregation, Grafana Tempo distributed tracing |
| **OpenTelemetry** | SDK instrumentation, OTLP exporter, span creation, trace context propagation |
| **AI/LLM Integration** | Google Gemini API, prompt engineering, structured context injection, fallback handling |
| **Backend** | FastAPI, async Python, REST API design, Kubernetes Python client |
| **Frontend** | Vanilla HTML/CSS/JS, Chart.js, Marked.js, glassmorphism dark theme, real-time polling |
| **DevOps** | Docker multi-stage builds, Helm chart deployment, shell scripting, `.env` secret management |
| **Chaos Engineering** | Latency injection, connection pool exhaustion, memory leak simulation, crash loop triggers |
| **SRE Practices** | Error budgets, golden signals (latency, traffic, errors, saturation), auto-remediation |

---

## Architecture

![Architecture Diagram](docs/images/architecture-diagram.png)

**How it works:**

1. **Simulate** — Trigger a failure on the `payment-api` service from the dashboard
2. **Collect** — Command Center scrapes Prometheus, Loki, Tempo, and K8s events
3. **Analyze** — All telemetry is bundled into a prompt and sent to Gemini 3.1 Flash Lite
4. **Display** — AI returns a markdown diagnosis with root cause and remediation steps
5. **Remediate** — One-click rolling restart and state reset via the Kubernetes API

---

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS (glassmorphism), JavaScript, Chart.js, Marked.js |
| Backend | FastAPI (Python 3.10) |
| AI Model | Google Gemini 3.1 Flash Lite via `google-genai` SDK |
| Metrics | Prometheus + ServiceMonitor |
| Logs | Grafana Loki |
| Traces | Grafana Tempo + OpenTelemetry |
| Orchestration | Kubernetes on Minikube |
| Target Service | `payment-api` — FastAPI with Prometheus client and OTel instrumentation |

---

## Demo: Incident Simulations

The dashboard includes five chaos scenarios to showcase AI-driven diagnosis:

| Mode | What Happens | What AI Detects |
|---|---|---|
| **Healthy** | Normal operation, ~50ms latency | Confirms healthy state |
| **Slowdown** | 4.5s sleep injected into requests | Identifies thread pool blocking, recommends DB optimization |
| **DB Error** | All requests return 500 | Correlates Loki stack traces with Prometheus error spike |
| **Memory Leak** | Background thread allocates 15MB/s | Predicts OOM kill, recommends memory limits |
| **Crash** | Process exits, pod enters CrashLoopBackOff | Links K8s restart events with crash logs |

Each simulation auto-triggers AI analysis. You can also type custom questions like *"Why is payment-api slow?"*

---

## Running Locally

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (20+)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) (1.30+)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/) (3.0+)
- [Gemini API Key](https://aistudio.google.com/apikey) (free tier works)

### Step 1 — Clone and configure

```bash
git clone https://github.com/humeshdeshmukh/aiops-command-center.git
cd 09-aiops-command-center
```

Edit `.env` with your Gemini API key:

```env
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-3.1-flash-lite
```

### Step 2 — Start Minikube

```bash
minikube start --driver=docker --memory=4096 --cpus=2
```

### Step 3 — Install observability stack

```bash
kubectl create namespace observability

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus-operator prometheus-community/kube-prometheus-stack \
  -n observability \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack -n observability
helm install tempo grafana/tempo -n observability
```

### Step 4 — Create secret and deploy

```bash
kubectl create secret generic gemini-api-secret \
  --from-literal=api-key="$(grep '^GEMINI_API_KEY=' .env | cut -d '=' -f2)"

chmod +x deploy.sh
./deploy.sh
```

### Step 5 — Open the dashboard

```bash
kubectl port-forward svc/command-center-service 8000:8000
# Open http://localhost:8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/system-status` | Returns pod status, metrics, logs, and K8s events |
| POST | `/api/simulate/{mode}` | Triggers a failure simulation (`healthy`, `slowdown`, `db_error`, `memory_leak`, `crash`) |
| POST | `/api/analyze` | Runs AI root cause analysis with telemetry context |
| POST | `/api/remediate` | Resets state and triggers rolling restart |

```bash
# Example: trigger AI analysis
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Why is payment-api failing?", "service": "payment-api", "namespace": "default"}'
```

---

## Project Structure

```
09-aiops-command-center/
├── .env                     # API keys (gitignored)
├── .gitignore
├── README.md
├── deploy.sh                # Build and deploy script
├── kubernetes.yaml          # K8s manifests (RBAC, Deployments, Services)
│
├── command-center/          # AIOps dashboard + backend
│   ├── Dockerfile
│   ├── main.py              # FastAPI — telemetry aggregation + Gemini AI
│   ├── requirements.txt
│   └── static/
│       ├── index.html
│       ├── style.css        # Dark glassmorphism theme
│       └── script.js        # Charts, polling, API calls
│
├── payment-api/             # Target service (chaos simulation)
│   ├── Dockerfile
│   ├── main.py              # FastAPI + Prometheus metrics + OTel tracing
│   └── requirements.txt
│
└── docs/images/
```

---

## Environment Variables

| Variable | Required | Default |
|---|:---:|---|
| `GEMINI_API_KEY` | Yes | — |
| `GEMINI_MODEL` | No | `gemini-3.1-flash-lite` |
| `PROMETHEUS_URL` | No | In-cluster default |
| `LOKI_URL` | No | In-cluster default |
| `TEMPO_URL` | No | In-cluster default |
| `TARGET_SERVICE_URL` | No | In-cluster default |

---

## What I'd Add Next

- **Slack/PagerDuty integration** for alert forwarding
- **Multi-service support** to monitor more than one microservice
- **Anomaly detection** using Prometheus recording rules
- **RAG pipeline** to include runbook context in AI prompts
- **Grafana dashboard export** for team-level observability

---

## Author

**Humesh Deshmukh**

- GitHub: [@humeshdeshmukh](https://github.com/humeshdeshmukh)

---

## License

MIT — free to use, modify, and distribute.
