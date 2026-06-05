import os
import time
import math
import logging
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from kubernetes import client, config
from google import genai

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("command-center")

app = FastAPI(title="AIOps Command Center Backend", version="1.0.0")

# Service URLs from environment variables (with in-cluster DNS defaults)
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-operator-kube-p-prometheus.observability.svc.cluster.local:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://loki.observability.svc.cluster.local:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://tempo.observability.svc.cluster.local:3200")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Initialize Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
TARGET_SERVICE_URL = os.getenv("TARGET_SERVICE_URL", "http://payment-api-service.default.svc.cluster.local:5000")

# Load Kubernetes client configuration
try:
    if "KUBERNETES_SERVICE_HOST" in os.environ:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config.")
    else:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig.")
except Exception as e:
    logger.warning(f"Could not load Kubernetes client config: {e}. Event fetching will fall back.")

class AnalysisQuery(BaseModel):
    query: str
    namespace: str = "default"
    service: str = "payment-api"

def sanitize_float(val, default=0.0):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default

# Helper: Fetch Prometheus Metrics
def get_metrics(service_name: str):
    logger.info(f"Querying Prometheus metrics for service {service_name}...")
    metrics = {}
    now = time.time()
    
    # 1. Error Rate (5xx / Total) over last 5m
    q_err = f'sum(rate(payment_api_requests_total{{status=~"5.."}}[5m])) / sum(rate(payment_api_requests_total[5m]))'
    # 2. Avg Latency
    q_lat = f'sum(rate(payment_api_request_duration_seconds_sum[5m])) / sum(rate(payment_api_request_duration_seconds_count[5m]))'
    # 3. Request Rate
    q_req = f'sum(rate(payment_api_requests_total[5m]))'
    # 4. Memory Usage (Container working set bytes)
    q_mem = f'sum(container_memory_working_set_bytes{{container="{service_name}"}})'
    # 5. CPU Usage (rate over 5m)
    q_cpu = f'sum(rate(container_cpu_usage_seconds_total{{container="{service_name}"}}[5m]))'
    
    queries = {
        "error_rate": (q_err, lambda v: sanitize_float(v, 0.0)),
        "latency": (q_lat, lambda v: sanitize_float(v, 0.05)),
        "request_rate": (q_req, lambda v: sanitize_float(v, 0.0)),
        "memory_mb": (q_mem, lambda v: round(sanitize_float(v, 15.0 * 1024 * 1024) / (1024*1024), 2)),
        "cpu_cores": (q_cpu, lambda v: round(sanitize_float(v, 0.005), 3))
    }
    
    for key, (query_expr, parser) in queries.items():
        try:
            r = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query_expr, "time": now}, timeout=2)
            if r.status_code == 200:
                res = r.json()
                data = res.get("data", {}).get("result", [])
                if data:
                    val = data[0]["value"][1]
                    metrics[key] = parser(val)
                else:
                    metrics[key] = parser(None)
            else:
                metrics[key] = parser(None)
        except Exception as e:
            logger.warning(f"Error querying Prometheus metric '{key}': {e}")
            metrics[key] = parser(None)
            
    return metrics

# Helper: Fetch Loki Logs
def get_logs(service_name: str, limit: int = 50):
    logger.info(f"Querying Loki logs for service {service_name}...")
    try:
        # Query logs from payment-api container
        query_expr = f'{{container="{service_name}"}}'
        r = requests.get(
            f"{LOKI_URL}/loki/api/v1/query_range", 
            params={"query": query_expr, "limit": limit, "direction": "BACKWARD"}, 
            timeout=2
        )
        if r.status_code == 200:
            res = r.json()
            results = res.get("data", {}).get("result", [])
            logs_list = []
            for item in results:
                values = item.get("values", [])
                for val in values:
                    # Loki returns [timestamp_ns, log_line]
                    logs_list.append(val[1])
            # Reverse to maintain chronological order
            logs_list.reverse()
            return logs_list
        else:
            logger.warning(f"Loki responded with status {r.status_code}")
            return ["Error: Loki returned status code " + str(r.status_code)]
    except Exception as e:
        logger.warning(f"Error querying Loki: {e}")
        return [f"Error querying Loki logs: {e}"]

# Helper: Fetch Tempo Traces
def get_traces(service_name: str):
    logger.info(f"Querying Tempo traces for service {service_name}...")
    try:
        # Search recent traces in Tempo
        r = requests.get(f"{TEMPO_URL}/api/search?tags=service.name={service_name}", timeout=2)
        if r.status_code == 200:
            return r.json().get("traces", [])
        else:
            return []
    except Exception as e:
        logger.warning(f"Error querying Tempo: {e}")
        return []

# Helper: Fetch Kubernetes Events
def get_k8s_events(namespace: str, service_name: str):
    logger.info(f"Querying Kubernetes Events for {service_name} in {namespace}...")
    events_summary = []
    try:
        v1 = client.CoreV1Api()
        # Fetch events in namespace
        events = v1.list_namespaced_event(namespace, limit=100)
        for event in events.items:
            # Check if event is related to payment-api
            name_lower = event.metadata.name.lower() if event.metadata.name else ""
            msg_lower = event.message.lower() if event.message else ""
            obj_lower = event.involved_object.name.lower() if event.involved_object.name else ""
            
            if service_name in name_lower or service_name in msg_lower or service_name in obj_lower:
                events_summary.append({
                    "reason": event.reason,
                    "message": event.message,
                    "type": event.type,
                    "object": event.involved_object.kind,
                    "count": event.count,
                    "last_timestamp": str(event.last_timestamp) if event.last_timestamp else "N/A"
                })
        return events_summary
    except Exception as e:
        logger.warning(f"Error querying K8s Events: {e}")
        # Return fallback mock events if running in cluster is fails or permissions missing
        return [{"reason": "API_ERROR", "message": f"K8s API connection failed: {e}", "type": "Warning", "object": "Cluster", "count": 1, "last_timestamp": "N/A"}]

# Get current simulation mode of target app
def get_target_mode():
    try:
        r = requests.get(f"{TARGET_SERVICE_URL}/health", timeout=1)
        if r.status_code == 200:
            return r.json().get("mode", "healthy")
        elif r.status_code == 503:
            return "crash"
    except Exception:
        pass
    return "unknown"

# API: Trigger failure simulations on target service
@app.post("/api/simulate/{mode}")
def trigger_simulation(mode: str):
    logger.info(f"Forwarding simulation request for mode {mode}...")
    try:
        r = requests.post(f"{TARGET_SERVICE_URL}/api/simulate/{mode}", timeout=3)
        return r.json()
    except Exception as e:
        logger.error(f"Failed to set simulation mode on target service: {e}")
        if mode == "crash":
            # In case of crash, target service might be offline, which is expected
            return {"status": "OK", "message": "Simulated crash mode triggered. Pod is exiting."}
        raise HTTPException(status_code=502, detail=f"Failed to communicate with target service: {e}")

# API: System status check
@app.get("/api/system-status")
def system_status():
    target_mode = get_target_mode()
    
    # Get active pod stats
    pod_status = "Unknown"
    restarts = 0
    try:
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod("default", label_selector="app=payment-api")
        if pods.items:
            pod = pods.items[0]
            pod_status = pod.status.phase
            if pod.status.container_statuses:
                restarts = pod.status.container_statuses[0].restart_count
        else:
            pod_status = "Not Found"
    except Exception:
        # Fallback if Kubernetes API fails
        if target_mode == "crash":
            pod_status = "Failed"
            restarts = 1
        elif target_mode == "unknown":
            pod_status = "Offline"
        else:
            pod_status = "Running"
            
    # Fetch real telemetry to send to frontend dashboard
    metrics = get_metrics("payment-api")
    logs = get_logs("payment-api", limit=15)
    events = get_k8s_events("default", "payment-api")
    
    return {
        "status": "UP",
        "target_mode": target_mode,
        "pod_status": pod_status,
        "pod_restarts": restarts,
        "metrics": metrics,
        "logs": logs,
        "events": events
    }

# API: Remediate service
@app.post("/api/remediate")
def remediate_service():
    logger.info("Executing remediation task...")
    try:
        # Force set simulation mode back to healthy
        try:
            requests.post(f"{TARGET_SERVICE_URL}/api/simulate/healthy", timeout=2)
        except Exception:
            pass
            
        # Perform rolling restart of payment-api deployment using K8s client
        v1 = client.AppsV1Api()
        deployment = v1.read_namespaced_deployment("payment-api", "default")
        
        # Update annotations to trigger a rolling restart
        if deployment.spec.template.metadata.annotations is None:
            deployment.spec.template.metadata.annotations = {}
        deployment.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = str(time.time())
        
        v1.patch_namespaced_deployment("payment-api", "default", deployment)
        logger.info("Remediation successful: Rolled restart payment-api deployment.")
        return {"status": "SUCCESS", "message": "Initiated rolling restart of payment-api deployment and reset state to healthy."}
    except Exception as e:
        logger.error(f"Remediation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute remediation: {e}")

# API: AIOps Root Cause Analysis
@app.post("/api/analyze")
async def analyze_incident(data: AnalysisQuery):
    logger.info(f"Performing AIOps analysis for query: '{data.query}'...")
    
    # 1. Fetch all telemetry details
    metrics = get_metrics(data.service)
    logs = get_logs(data.service, limit=15)
    events = get_k8s_events(data.namespace, data.service)
    
    # Format logs for LLM prompt
    logs_formatted = "\n".join(logs) if logs else "No logs available."
    
    # Format events for LLM prompt
    events_formatted = ""
    if events:
        for ev in events[:5]:
            events_formatted += f"- [{ev['type']}] {ev['reason']} on {ev['object']}: {ev['message']} (Count: {ev['count']}, Time: {ev['last_timestamp']})\n"
    else:
        events_formatted = "No relevant Kubernetes events."
        
    # Format metrics for LLM prompt
    metrics_formatted = f"""
    - Request Rate: {metrics.get('request_rate')} req/s
    - Error Rate: {metrics.get('error_rate', 0.0) * 100:.1f}%
    - Average Request Latency: {metrics.get('latency', 0.0) * 1000:.1f} ms
    - Container Memory Usage: {metrics.get('memory_mb')} MB
    - Container CPU Usage: {metrics.get('cpu_cores')} cores
    """
    
    # 2. Build Prompt for Gemini Model
    prompt = f"""You are Antigravity AIOps SRE Agent, a senior Site Reliability Engineer assistant.
You are diagnosing an incident in the microservice '{data.service}' in namespace '{data.namespace}'.

The operator asked: "{data.query}"

Here is the collected telemetry data for '{data.service}':

=== METRICS (Prometheus) ===
{metrics_formatted}

=== RECENT LOGS (Loki) ===
{logs_formatted}

=== KUBERNETES EVENTS (kubectl get events) ===
{events_formatted}

=== ANALYSIS INSTRUCTIONS ===
Analyze the telemetry data carefully:
1. Identify if the service is experiencing high latency, 5xx errors, memory leaks (OOM), or crash/restarts.
2. Cross-reference the Loki logs and K8s Events to find the exact root cause (e.g. database connection failures, thread delays, out-of-memory container killings, process crashes).
3. Be concise and precise.
4. Output your analysis in clean Markdown with the following sections:
   - **Diagnosis**: A brief summary of what is wrong.
   - **Root Cause Analysis**: The detailed explanation linking metrics, logs, and events.
   - **Remediation Steps**: Practical steps the SRE should take (e.g. roll restart, scale replicas, resolve database connection).

Keep the tone professional and expert. Do not mention that you are a language model or make up telemetry that is not provided.
"""
    
    # 3. Request LLM Completion from Google Gemini API
    response_text = ""
    llm_error = None
    try:
        if not gemini_client:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Cannot call Gemini API.")
        
        logger.info(f"Calling Gemini API using model '{GEMINI_MODEL}'...")
        
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction="You are a expert AIOps SRE assistant.",
                max_output_tokens=1500,
            ),
        )
        
        content = response.text or ""
        
        if content.strip():
            response_text = content
        else:
            response_text = "### ⚠️ Model generated empty response.\nHeuristics indicate active simulation state: " + get_target_mode()
            
        logger.info("Successfully received Gemini analysis.")
    except Exception as e:
        llm_error = f"Failed to get analysis from Gemini API: {e}"
        logger.error(llm_error)
        
    if llm_error:
        # Graceful fallback response if Gemini API fails
        response_text = f"""### ⚠️ Gemini API Error

The AIOps Agent could not get analysis from the Gemini 3.1 Flash Lite model.
*Error details: {llm_error}*

**However, raw telemetry was collected and analyzed by rule-based heuristic:**
* **Active Mode**: {get_target_mode()}
* **Metrics**: {metrics_formatted}
* **Logs Analysis**: Detected {len([l for l in logs if "error" in l.lower() or "fail" in l.lower() or "timeout" in l.lower()])} potential warning/error lines.
"""

    # 4. Return combined analysis and raw telemetry data
    return {
        "query": data.query,
        "analysis": response_text,
        "telemetry": {
            "metrics": metrics,
            "logs": logs,
            "events": events
        }
    }

# Mount static files folder
app.mount("/", StaticFiles(directory="static", html=True), name="static")
