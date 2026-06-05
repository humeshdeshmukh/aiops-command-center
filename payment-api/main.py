import os
import sys
import time
import logging
import threading
from fastapi import FastAPI, Response, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Setup logging to stdout so Promtail/Loki can scrape it
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("payment-api")

# Initialize OpenTelemetry Tracing
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://opentelemetry-collector.observability.svc.cluster.local:4318/v1/traces")
logger.info(f"Initializing OpenTelemetry tracing exporting to {OTEL_EXPORTER_OTLP_ENDPOINT}")

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("payment-api-tracer")

# Initialize FastAPI app
app = FastAPI(title="Payment API", version="1.0.0")

# Setup Prometheus Custom Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "payment_api_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"]
)
HTTP_REQUEST_DURATION = Histogram(
    "payment_api_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Simulated Incident State
# Modes: "healthy", "slowdown", "db_error", "memory_leak", "crash"
sim_mode = "healthy"
memory_leak_holder = []
leak_thread = None

@app.middleware("http")
async def monitor_requests(request, call_next):
    method = request.method
    endpoint = request.url.path
    
    # Exclude prometheus metrics and health check from latency histograms to avoid pollution
    if endpoint in ["/metrics", "/health"]:
        return await call_next(request)
        
    start_time = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response
    except Exception as e:
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=500).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        raise e

@app.get("/health")
def health():
    if sim_mode == "crash":
        # Simulate unhealthiness
        raise HTTPException(status_code=503, detail="Service Unhealthy (Simulated Crash Mode)")
    return {"status": "UP", "mode": sim_mode}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

def memory_leaker():
    global memory_leak_holder
    logger.warning("Memory leaker thread started!")
    chunk_count = 0
    while sim_mode == "memory_leak":
        # Append 15MB chunks of strings to leak RAM
        try:
            large_chunk = "X" * (15 * 1024 * 1024)
            memory_leak_holder.append(large_chunk)
            chunk_count += 1
            logger.warning(f"Allocated memory chunk {chunk_count}. Total leaked: {chunk_count * 15}MB")
        except MemoryError:
            logger.error("Out of memory in python leaker!")
            break
        time.sleep(1.5)

@app.post("/api/simulate/{mode}")
def set_simulate_mode(mode: str):
    global sim_mode, memory_leak_holder, leak_thread
    valid_modes = ["healthy", "slowdown", "db_error", "memory_leak", "crash"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid simulation mode: {mode}")
    
    sim_mode = mode
    logger.info(f"Simulation mode changed to: {mode}")
    
    # Cleanup memory leak if turning off
    if mode != "memory_leak":
        memory_leak_holder.clear()
        
    # Handle specific modes
    if mode == "memory_leak":
        # Start memory leaker in a separate thread
        leak_thread = threading.Thread(target=memory_leaker, daemon=True)
        leak_thread.start()
    elif mode == "crash":
        # Schedule self-destruction after 2 seconds to allow response delivery
        def self_destruct():
            time.sleep(2)
            logger.critical("Simulated crash triggered! Exiting process with code 1.")
            os._exit(1)
        threading.Thread(target=self_destruct, daemon=True).start()
        
    return {"status": "OK", "message": f"Simulation mode set to {mode}"}

@app.get("/api/pay")
def process_payment():
    current_span = trace.get_current_span()
    current_span.set_attribute("service.name", "payment-api")
    
    logger.info("Processing payment request...")
    
    # Mode behavior simulations
    if sim_mode == "slowdown":
        logger.warning("Simulated SLOWDOWN active. Sleeping for 4.5 seconds...")
        with tracer.start_as_current_span("simulated_db_query") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", "SELECT * FROM payments WHERE status = 'pending'")
            time.sleep(4.5)
        logger.info("Payment request completed after slowdown.")
        return {"status": "SUCCESS", "message": "Payment processed (slow)"}
        
    elif sim_mode == "db_error":
        logger.error("Simulated DATABASE CONNECTION ERROR active. Connection timeout!")
        with tracer.start_as_current_span("simulated_db_connection") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.record_exception(Exception("Connection timeout: Connection pool exhausted (max_connections=100)"))
            db_span.set_status(trace.StatusCode.ERROR, "Database Connection Failed")
            
            # Log standard stack trace for Loki scraping
            logger.error("ConnectionRefusedError: [Errno 111] Connection refused in pg_connect")
            logger.error("Traceback (most recent call last):")
            logger.error("  File \"/app/main.py\", line 112, in process_payment")
            logger.error("    db.connect(timeout=3.0)")
            logger.error("TimeoutError: Database connection timeout after 3000ms")
            
        raise HTTPException(
            status_code=500,
            detail="Database Connection Failure: Connection pool exhausted"
        )
        
    elif sim_mode == "memory_leak":
        logger.info("Normal request execution during memory leak.")
        return {"status": "SUCCESS", "message": "Payment processed, but system memory is leaking!"}
        
    elif sim_mode == "crash":
        logger.error("Simulated CRASH mode active. Returing failure.")
        raise HTTPException(status_code=503, detail="Service Unavailable (Simulating Crash)")
        
    else:
        # Healthy behavior
        with tracer.start_as_current_span("db_verify_payment") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            time.sleep(0.05) # normal fast DB query
        logger.info("Payment processed successfully.")
        return {"status": "SUCCESS", "message": "Payment processed successfully."}

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
