import sys
import os
import uuid
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure root directory is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.router import route_request
from src.tools import TOOL_REGISTRY
from src.config import Config

app = FastAPI(
    title="AI Function-Calling Router API",
    description="Production-grade AI Function-Calling Router with Pydantic v2 strict typing, deterministic fault injection, and targeted 4-tier recovery policies.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def normalize_vercel_rewrites(request: Request, call_next):
    path = request.scope.get("path", "")
    for prefix in ("/api/index.py", "/api/index"):
        if path.startswith(prefix):
            remainder = path[len(prefix):]
            if not remainder.startswith("/"):
                remainder = "/" + remainder
            request.scope["path"] = remainder
            break
    return await call_next(request)

class RouteRequestPayload(BaseModel):
    request: str = Field(..., description="Natural language request string", example="Book flight from SFO to JFK on 2025-05-15")
    expected_tool: Optional[str] = Field(None, description="Optional target tool name hint", example="FlightSearch")
    correct_args: Optional[Dict[str, Any]] = Field(None, description="Optional ground truth arguments for simulation", example={"origin": "SFO", "destination": "JFK", "date": "2025-05-15"})
    initial_argument_fault: Optional[str] = Field(None, description="Optional extraction fault: 'missing_field' or 'type_error'")
    injected_fault_type: Optional[str] = Field("NONE", description="Fault directive: 'NONE', 'TIMEOUT', or 'MALFORMED_RESPONSE'")
    injected_fault_persistence: Optional[str] = Field("once", description="Fault persistence: 'once' or 'always'")
    recovery_enabled: bool = Field(True, description="Whether targeted recovery policies are enabled")

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI-Function-Calling-Router",
        "provider_mode": Config.PROVIDER_MODE,
        "available_tools": list(TOOL_REGISTRY.keys())
    }

@app.get("/tools")
@app.get("/api/tools")
def list_registered_tools():
    tools_info = {}
    for name, tool in TOOL_REGISTRY.items():
        tools_info[name] = {
            "description": tool["description"],
            "input_schema": tool["input_model"].model_json_schema(),
            "output_schema": tool["output_model"].model_json_schema()
        }
    return tools_info

@app.get("/metrics")
@app.get("/api/metrics")
def get_evaluation_metrics():
    metrics_path = os.path.join(ROOT_DIR, "output", "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "baseline": {"completion_rate": 0.5833, "silent_wrong_rate": 0.0, "mean_recovery_attempts": 0.0},
        "recovery_active": {"completion_rate": 0.9000, "silent_wrong_rate": 0.0, "mean_recovery_attempts": 0.3833}
    }

@app.get("/dataset")
@app.get("/api/dataset")
def get_dataset_coverage():
    cov_path = os.path.join(ROOT_DIR, "output", "dataset_coverage.json")
    if os.path.exists(cov_path):
        with open(cov_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "dataset_coverage_not_generated"}

@app.post("/route")
@app.post("/api/route")
def route_nl_request(payload: RouteRequestPayload):
    req_id = f"web-{uuid.uuid4().hex[:8]}"
    dataset_id = "live-playground"
    
    # Infer expected tool if not provided
    expected_tool = payload.expected_tool
    if not expected_tool:
        text_lower = payload.request.lower()
        if "flight" in text_lower:
            expected_tool = "FlightSearch"
        elif "calendar" in text_lower or "book" in text_lower or "schedule" in text_lower or "sync" in text_lower:
            expected_tool = "CalendarBooking"
        elif "weather" in text_lower or "temperature" in text_lower:
            expected_tool = "WeatherLookup"
        elif "convert" in text_lower or "meters" in text_lower or "feet" in text_lower or "celsius" in text_lower:
            expected_tool = "UnitConversion"
        else:
            expected_tool = "Unknown"

    default_args = {}
    if expected_tool == "FlightSearch":
        default_args = {"origin": "SFO", "destination": "JFK", "date": "2025-05-15"}
    elif expected_tool == "CalendarBooking":
        default_args = {"event_title": "Project Sync", "start_time": "2025-05-16T14:00:00", "duration_minutes": 45}
    elif expected_tool == "WeatherLookup":
        default_args = {"location": "Tokyo", "unit": "C"}
    elif expected_tool == "UnitConversion":
        default_args = {"value": 100.0, "from_unit": "meters", "to_unit": "feet"}

    correct_args = payload.correct_args if payload.correct_args else default_args

    fixture = {
        "expected_tool": expected_tool,
        "correct_args": correct_args,
        "initial_argument_fault": payload.initial_argument_fault,
        "injected_fault": {
            "type": payload.injected_fault_type or "NONE",
            "persistence": payload.injected_fault_persistence or "once"
        },
        "schema_repair_unrecoverable": False
    }

    result, trace = route_request(
        request_id=req_id,
        dataset_case_id=dataset_id,
        request=payload.request,
        fixture=fixture,
        recovery_enabled=payload.recovery_enabled
    )

    trace_dict = {
        "request_id": trace.request_id,
        "dataset_case_id": trace.dataset_case_id,
        "selected_tool": trace.selected_tool,
        "provider_mode": trace.provider_mode,
        "validation_result": trace.validation_result,
        "failure_class": trace.failure_class,
        "recovery_policy": trace.recovery_policy,
        "recovery_attempts": trace.recovery_attempts,
        "tool_execution_attempts": trace.tool_execution_attempts,
        "provider_call_count": trace.provider_call_count,
        "final_status": trace.final_status,
        "final_failure_reason": trace.final_failure_reason,
        "output_validation_passed": trace.output_validation_passed,
        "duration_ms": round(trace.duration_ms, 2)
    }

    return {
        "result": result,
        "trace": trace_dict,
        "fixture_applied": fixture
    }

@app.get("/", response_class=HTMLResponse)
def index_playground():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Function-Calling Router | Live Playground</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #090d16;
      --card-bg: rgba(17, 24, 39, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-blue: #3b82f6;
      --accent-purple: #8b5cf6;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --font-sans: 'Plus Jakarta Sans', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      padding: 2rem 1rem;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    header {
      text-align: center;
      margin-bottom: 2.5rem;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
      margin-bottom: 1rem;
    }
    .badge-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }
    h1 {
      font-size: 2.5rem;
      font-weight: 800;
      letter-spacing: -0.025em;
      background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.75rem;
    }
    .subtitle {
      color: var(--text-muted);
      font-size: 1.05rem;
      max-width: 650px;
      margin: 0 auto 1.5rem;
      line-height: 1.6;
    }
    .header-links {
      display: flex;
      justify-content: center;
      gap: 1rem;
    }
    .btn-link {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      color: #93c5fd;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--card-border);
      transition: all 0.2s;
    }
    .btn-link:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.2);
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.75rem;
      margin-bottom: 2rem;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.5rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 1.25rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .presets {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }
    .btn-preset {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 0.6rem 0.75rem;
      color: #cbd5e1;
      font-size: 0.8rem;
      font-weight: 500;
      text-align: left;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-preset:hover {
      background: rgba(59, 130, 246, 0.1);
      border-color: rgba(59, 130, 246, 0.4);
      color: #ffffff;
    }
    .form-group {
      margin-bottom: 1.25rem;
    }
    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    textarea, select, input {
      width: 100%;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 0.75rem 1rem;
      color: #ffffff;
      font-family: var(--font-sans);
      font-size: 0.95rem;
      transition: border-color 0.2s;
    }
    textarea:focus, select:focus, input:focus {
      outline: none;
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.85rem 1rem;
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      margin-bottom: 1.25rem;
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 48px;
      height: 26px;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #374151;
      transition: .3s;
      border-radius: 26px;
    }
    .slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 4px;
      bottom: 4px;
      background-color: white;
      transition: .3s;
      border-radius: 50%;
    }
    input:checked + .slider { background-color: var(--accent-blue); }
    input:checked + .slider:before { transform: translateX(22px); }
    .btn-submit {
      width: 100%;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: white;
      font-weight: 700;
      font-size: 1rem;
      padding: 0.85rem;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: transform 0.15s, box-shadow 0.15s;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }
    .btn-submit:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6);
    }
    .trace-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }
    .pill {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
    }
    .pill-success { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
    .pill-error { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
    .pill-warn { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
    pre {
      background: #030712;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      color: #e5e7eb;
      overflow-x: auto;
      max-height: 400px;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-top: 1.5rem;
    }
    @media (max-width: 800px) {
      .metrics-grid { grid-template-columns: repeat(2, 1fr); }
    }
    .metric-box {
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
      text-align: center;
    }
    .metric-val {
      font-size: 1.75rem;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 0.25rem;
    }
    .metric-lbl {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge">
        <span class="badge-dot"></span> Production Engine Active
      </div>
      <h1>AI Function-Calling Router</h1>
      <p class="subtitle">
        Strict Pydantic v2 type boundaries, deterministic fault injection, and bounded multi-tier recovery policies for resilient natural language tool routing.
      </p>
      <div class="header-links">
        <a class="btn-link" href="/docs" target="_blank">⚡ Swagger API (/docs)</a>
        <a class="btn-link" href="/redoc" target="_blank">📖 ReDoc UI (/redoc)</a>
        <a class="btn-link" href="https://github.com/Manirider/Ai-Function-Calling-Router" target="_blank">🐙 GitHub Repository</a>
      </div>
    </header>

    <div class="grid">
      <!-- Input Console -->
      <div class="card">
        <div class="card-title">
          <span>🎮 Interactive Request Console</span>
        </div>
        
        <label>Quick Presets</label>
        <div class="presets">
          <button class="btn-preset" onclick="loadPreset('flight_happy')">✈️ Flight Search (Nominal)</button>
          <button class="btn-preset" onclick="loadPreset('calendar_happy')">📅 Calendar Booking (Nominal)</button>
          <button class="btn-preset" onclick="loadPreset('weather_happy')">🌤️ Weather Lookup (Nominal)</button>
          <button class="btn-preset" onclick="loadPreset('unit_happy')">📏 Unit Conversion (Nominal)</button>
          <button class="btn-preset" onclick="loadPreset('missing_field')">⚠️ Fault: Missing Destination</button>
          <button class="btn-preset" onclick="loadPreset('type_error')">⚠️ Fault: Non-ISO Date</button>
          <button class="btn-preset" onclick="loadPreset('timeout_once')">⏱️ Fault: Transient Timeout</button>
          <button class="btn-preset" onclick="loadPreset('malformed_once')">💥 Fault: Malformed Payload</button>
        </div>

        <form id="routeForm" onsubmit="executeRoute(event)">
          <div class="form-group">
            <label>Natural Language Query</label>
            <textarea id="requestText" rows="3" required placeholder="Describe what tool to execute..."></textarea>
          </div>

          <div class="row">
            <div class="form-group">
              <label>Target Tool Hint</label>
              <select id="expectedTool">
                <option value="FlightSearch">FlightSearch</option>
                <option value="CalendarBooking">CalendarBooking</option>
                <option value="WeatherLookup">WeatherLookup</option>
                <option value="UnitConversion">UnitConversion</option>
                <option value="Unknown">Unknown Tool</option>
              </select>
            </div>
            <div class="form-group">
              <label>Injected Extraction Fault</label>
              <select id="initialFault">
                <option value="">None (Nominal)</option>
                <option value="missing_field">Missing Required Field</option>
                <option value="type_error">Type Validation Error</option>
              </select>
            </div>
          </div>

          <div class="row">
            <div class="form-group">
              <label>Fault Injection Directive</label>
              <select id="faultType">
                <option value="NONE">NONE</option>
                <option value="TIMEOUT">TIMEOUT</option>
                <option value="MALFORMED_RESPONSE">MALFORMED_RESPONSE</option>
              </select>
            </div>
            <div class="form-group">
              <label>Fault Persistence</label>
              <select id="faultPersistence">
                <option value="once">Once (Transient)</option>
                <option value="always">Always (Persistent)</option>
              </select>
            </div>
          </div>

          <div class="toggle-row">
            <div>
              <div style="font-weight: 600; font-size: 0.9rem;">Targeted Recovery Engine</div>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Enables missing field, type error, timeout, and schema repair</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="recoveryToggle" checked>
              <span class="slider"></span>
            </label>
          </div>

          <button type="submit" class="btn-submit" id="submitBtn">Route & Execute Query</button>
        </form>
      </div>

      <!-- Execution Telemetry & Results -->
      <div class="card">
        <div class="card-title">
          <span>📊 Live Execution Trace & Response</span>
        </div>

        <div class="trace-pills" id="tracePills">
          <span class="pill">Status: Idle</span>
          <span class="pill">Validation: Pending</span>
          <span class="pill">Latency: 0 ms</span>
        </div>

        <label>Response Envelope</label>
        <pre id="responseJson">// Execute a query to see the standardized response envelope...</pre>

        <label style="margin-top: 1rem;">Telemetry Metadata</label>
        <pre id="traceJson">// Trace metadata will appear here...</pre>
      </div>
    </div>

    <!-- Benchmark Metrics Overview -->
    <div class="card">
      <div class="card-title">
        <span>📈 Evaluation Benchmark Summary (60 Scenarios)</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-box">
          <div class="metric-val" style="color: #60a5fa;">58.3%</div>
          <div class="metric-lbl">Baseline Completion</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" style="color: #34d399;">90.0%</div>
          <div class="metric-lbl">Recovery Completion</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" style="color: #a78bfa;">0.0%</div>
          <div class="metric-lbl">Silent Wrong Rate</div>
        </div>
        <div class="metric-box">
          <div class="metric-val" style="color: #fbbf24;">0.38</div>
          <div class="metric-lbl">Mean Recovery Passes</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const presets = {
      flight_happy: {
        text: "Search for available round-trip flights from SFO to JFK on 2025-05-15",
        tool: "FlightSearch",
        fault: "",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      calendar_happy: {
        text: "Schedule an architecture team review tomorrow at 2:00 PM for 45 minutes",
        tool: "CalendarBooking",
        fault: "",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      weather_happy: {
        text: "What is the current meteorological temperature in Tokyo in Celsius?",
        tool: "WeatherLookup",
        fault: "",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      unit_happy: {
        text: "Convert 100 meters into imperial feet measurement",
        tool: "UnitConversion",
        fault: "",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      missing_field: {
        text: "Find flights departing from SFO (omitted destination parameter)",
        tool: "FlightSearch",
        fault: "missing_field",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      type_error: {
        text: "Find flights from SFO to JFK with corrupt date format",
        tool: "FlightSearch",
        fault: "type_error",
        faultType: "NONE",
        persistence: "once",
        recovery: true
      },
      timeout_once: {
        text: "Check weather in Tokyo in Celsius under transient upstream timeout",
        tool: "WeatherLookup",
        fault: "",
        faultType: "TIMEOUT",
        persistence: "once",
        recovery: true
      },
      malformed_once: {
        text: "Schedule team sync under malformed tool output payload",
        tool: "CalendarBooking",
        fault: "",
        faultType: "MALFORMED_RESPONSE",
        persistence: "once",
        recovery: true
      }
    };

    function loadPreset(key) {
      const p = presets[key];
      if (!p) return;
      document.getElementById('requestText').value = p.text;
      document.getElementById('expectedTool').value = p.tool;
      document.getElementById('initialFault').value = p.fault;
      document.getElementById('faultType').value = p.faultType;
      document.getElementById('faultPersistence').value = p.persistence;
      document.getElementById('recoveryToggle').checked = p.recovery;
    }

    async function executeRoute(e) {
      e.preventDefault();
      const btn = document.getElementById('submitBtn');
      btn.innerText = "Routing Request...";
      btn.disabled = true;

      const payload = {
        request: document.getElementById('requestText').value,
        expected_tool: document.getElementById('expectedTool').value,
        initial_argument_fault: document.getElementById('initialFault').value || null,
        injected_fault_type: document.getElementById('faultType').value,
        injected_fault_persistence: document.getElementById('faultPersistence').value,
        recovery_enabled: document.getElementById('recoveryToggle').checked
      };

      try {
        const resp = await fetch('/api/route', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await resp.json();

        // Render pills
        const pills = document.getElementById('tracePills');
        const trace = data.trace;
        const isSuccess = trace.final_status === 'success';
        const isRecovered = trace.recovery_attempts > 0 && isSuccess;

        pills.innerHTML = `
          <span class="pill ${isSuccess ? 'pill-success' : 'pill-error'}">Status: ${trace.final_status.toUpperCase()}</span>
          <span class="pill ${trace.validation_result === 'passed' ? 'pill-success' : 'pill-warn'}">Validation: ${trace.validation_result}</span>
          ${isRecovered ? `<span class="pill pill-warn">Policy: ${trace.recovery_policy} (${trace.recovery_attempts} attempt)</span>` : ''}
          <span class="pill">Tool: ${trace.selected_tool}</span>
          <span class="pill">Latency: ${trace.duration_ms} ms</span>
        `;

        document.getElementById('responseJson').textContent = JSON.stringify(data.result, null, 2);
        document.getElementById('traceJson').textContent = JSON.stringify(data.trace, null, 2);
      } catch (err) {
        document.getElementById('responseJson').textContent = JSON.stringify({ error: err.message }, null, 2);
      } finally {
        btn.innerText = "Route & Execute Query";
        btn.disabled = false;
      }
    }

    // Default load
    loadPreset('flight_happy');
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
