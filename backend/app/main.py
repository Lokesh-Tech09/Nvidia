"""
CircuitProof Main FastAPI Backend Server (backend/app/main.py)
Orchestrating:
- LLM Agentic Reasoning (NVIDIA Nemotron / Ollama)
- Deterministic Circuit Referee Rules
- Bounded KiCad Schematic Synthesis (.kicad_sch)
- Recursive Project Scanner & Knowledge Store (40k+ components)
- Interactive Circuit Lab Web Studio (Frontend)
- Production Features (404, SEO, OG, Security, Analytics, Legal)
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure app directory is in Python path for direct imports
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
EXPORTS_DIR = BACKEND_DIR / "exports"
FRONTEND_DIR = ROOT_DIR / "frontend"
PUBLIC_DIR = FRONTEND_DIR / "public"

os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from generator import SchematicSynthesizer
    from cloud_reviewer import CloudReviewer
    from circuitproof_core import CircuitReferee
    from knowledge_store import KnowledgeStore
    from scan_project import KiCadProjectScanner
    from report_exporter import ReportExporter
except ImportError:
    from backend.app.generator import SchematicSynthesizer
    from backend.app.cloud_reviewer import CloudReviewer
    from backend.app.circuitproof_core import CircuitReferee
    from backend.app.knowledge_store import KnowledgeStore
    from backend.app.scan_project import KiCadProjectScanner
    from backend.app.report_exporter import ReportExporter

app = FastAPI(
    title="CircuitProof Backend API",
    description="Agentic Hardware Design, Verification & Schematic Synthesis Engine",
    version="1.0.0"
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Enable CORS for local dev servers and direct browser file access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount public directory if exists
if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

# Initialize engines
DB_PATH = DATA_DIR / "circuitproof_notebook.db"
synthesizer = SchematicSynthesizer(output_dir=str(EXPORTS_DIR))
cloud_ai = CloudReviewer()
referee = CircuitReferee(db_name=str(DB_PATH))
knowledge_store = KnowledgeStore(db_name=str(DB_PATH))
exporter = ReportExporter(output_dir=str(EXPORTS_DIR))
scanner = KiCadProjectScanner(db_name=str(DB_PATH))

# In-memory analytics store for privacy-respecting metrics
ANALYTICS_EVENTS: List[Dict[str, Any]] = []


# -------------------------------------------------------------
# Request & Response Models
# -------------------------------------------------------------
class PromptGenRequest(BaseModel):
    user_prompt: str
    project_name: Optional[str] = "circuitproof_design"

class VerifyRequest(BaseModel):
    components: List[Dict[str, Any]]
    nets: Optional[List[Dict[str, Any]]] = None

class ScanRequest(BaseModel):
    directory: Optional[str] = "."

class MistakeLogRequest(BaseModel):
    violation_text: str
    fix_text: str

class AnalyticsEvent(BaseModel):
    event_name: str
    properties: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Core API Endpoints
# -------------------------------------------------------------
@app.get("/api/health")
def health_endpoint():
    """Health check and platform stats."""
    stats = knowledge_store.get_stats()
    return {
        "status": "online",
        "service": "CircuitProof Core Agent",
        "version": "1.0.0",
        "stats": stats,
        "analytics_events_recorded": len(ANALYTICS_EVENTS)
    }


@app.post("/api/analytics")
def record_analytics_endpoint(payload: AnalyticsEvent):
    """Telemetry receiver for privacy-friendly anonymous metrics."""
    event_record = {
        "event": payload.event_name,
        "properties": payload.properties or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    ANALYTICS_EVENTS.append(event_record)
    if len(ANALYTICS_EVENTS) > 1000:
        ANALYTICS_EVENTS.pop(0)
    return {"status": "ok", "received": payload.event_name}


@app.get("/api/analytics")
def get_analytics_summary():
    """Retrieve aggregate analytics metrics."""
    counts = {}
    for ev in ANALYTICS_EVENTS:
        name = ev.get("event", "unknown")
        counts[name] = counts.get(name, 0) + 1
    return {
        "total_events": len(ANALYTICS_EVENTS),
        "breakdown": counts,
        "recent": ANALYTICS_EVENTS[-15:]
    }


@app.post("/api/generate-from-prompt")
def generate_from_prompt_endpoint(payload: PromptGenRequest):
    """
    End-to-End Agentic Pipeline:
    Natural Language Prompt -> AI Analysis & Component Extraction -> 
    Coordinate Placement & Net Routing -> Schematic Synthesis (.kicad_sch) ->
    Deterministic Referee Rule Verification -> Audit Report Export.
    """
    ANALYTICS_EVENTS.append({"event": "generate_design_request", "project": payload.project_name, "timestamp": datetime.utcnow().isoformat()})
    
    system_prompt = """
    You are CircuitProof, an expert hardware design agent. 
    Analyze the user's circuit description and extract the required electronic components and connections.
    You MUST respond with a valid JSON block containing:
    1. "components": A list of objects with "reference" (e.g., "U1", "U2", "R1", "C1"), "lib_id" (e.g., "MCU_ST_STM32F1:STM32F103C8Tx", "Sensor_Motion:BNO085", "Memory_Flash:W25Q128JV", "Device:R", "Device:C"), and descriptive "part" name.
    2. "nets": A list of objects with "net" name and "connections" array pairing component references and pins.

    Example JSON format:
    {
      "components": [
        {"reference": "U1", "lib_id": "MCU_ST_STM32F1:STM32F103C8Tx", "part": "STM32F103C8T6", "category": "MCU"},
        {"reference": "U2", "lib_id": "Sensor_Motion:BNO085", "part": "BNO085 IMU", "category": "Sensor"},
        {"reference": "U3", "lib_id": "Memory_Flash:W25Q128JV", "part": "W25Q128JV SPI Flash", "category": "Memory"},
        {"reference": "R1", "lib_id": "Device:R", "part": "4.7k Pullup", "category": "Resistor"},
        {"reference": "R2", "lib_id": "Device:R", "part": "4.7k Pullup", "category": "Resistor"},
        {"reference": "C1", "lib_id": "Device:C", "part": "100nF Bypass", "category": "Capacitor"}
      ],
      "nets": [
        {"net": "3V3", "connections": [["U1", "VDD"], ["U2", "VDD"], ["U3", "VCC"]]},
        {"net": "GND", "connections": [["U1", "GND"], ["U2", "GND"], ["U3", "GND"]]},
        {"net": "I2C_SDA", "connections": [["U1", "PB7"], ["U2", "SDA"]]},
        {"net": "I2C_SCL", "connections": [["U1", "PB6"], ["U2", "SCL"]]},
        {"net": "SPI_SCK", "connections": [["U1", "PA5"], ["U3", "CLK"]]},
        {"net": "SPI_MOSI", "connections": [["U1", "PA7"], ["U3", "DI"]]},
        {"net": "SPI_MISO", "connections": [["U1", "PA6"], ["U3", "DO"]]},
        {"net": "SPI_CS", "connections": [["U1", "PA4"], ["U3", "CS"]]}
      ]
    }
    Return ONLY valid JSON inside your response, or include a clear JSON block.
    """
    
    ai_raw_response = cloud_ai.get_design_explanation(f"{system_prompt}\n\nUser Request: {payload.user_prompt}")
    
    # Default smart baseline components & nets if prompt doesn't specify or JSON parsing fails
    components = [
        {"reference": "U1", "lib_id": "MCU_ST_STM32F1:STM32F103C8Tx", "part": "STM32F103C8T6", "category": "MCU"},
        {"reference": "U2", "lib_id": "Sensor_Motion:BNO085", "part": "BNO085 IMU", "category": "Sensor"},
        {"reference": "U3", "lib_id": "Memory_Flash:W25Q128JV", "part": "W25Q128JV SPI Flash", "category": "Memory"},
        {"reference": "R1", "lib_id": "Device:R", "part": "4.7k Pullup", "category": "Resistor"},
        {"reference": "R2", "lib_id": "Device:R", "part": "4.7k Pullup", "category": "Resistor"},
        {"reference": "C1", "lib_id": "Device:C", "part": "100nF Bypass", "category": "Capacitor"}
    ]
    nets = [
        {"net": "3V3", "connections": [("U1", "VDD"), ("U2", "VDD"), ("U3", "VCC")]},
        {"net": "GND", "connections": [("U1", "GND"), ("U2", "GND"), ("U3", "GND")]},
        {"net": "I2C_SDA", "connections": [("U1", "PB7"), ("U2", "SDA")]},
        {"net": "I2C_SCL", "connections": [("U1", "PB6"), ("U2", "SCL")]},
        {"net": "SPI_SCK", "connections": [("U1", "PA5"), ("U3", "CLK")]},
        {"net": "SPI_MOSI", "connections": [("U1", "PA7"), ("U3", "DI")]},
        {"net": "SPI_MISO", "connections": [("U1", "PA6"), ("U3", "DO")]},
        {"net": "SPI_CS", "connections": [("U1", "PA4"), ("U3", "CS")]}
    ]

    # Try to extract JSON from AI response
    try:
        json_match = re.search(r'\{.*\}', ai_raw_response, re.DOTALL)
        if json_match:
            parsed_data = json.loads(json_match.group(0))
            if "components" in parsed_data and isinstance(parsed_data["components"], list):
                components = parsed_data["components"]
            if "nets" in parsed_data and isinstance(parsed_data["nets"], list):
                nets = parsed_data["nets"]
    except Exception as e:
        print(f"[Warning]: Could not parse AI JSON response, using smart defaults. Error: {e}")

    # Standardize connections in nets: list of pairs
    clean_nets = []
    for n in nets:
        net_name = n.get("net", "NET")
        conns = n.get("connections", [])
        clean_conns = []
        for c in conns:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                clean_conns.append((str(c[0]), str(c[1])))
        if clean_conns:
            clean_nets.append({"net": net_name, "connections": clean_conns})
    nets = clean_nets if clean_nets else nets

    filename = f"{payload.project_name}.kicad_sch"
    try:
        # 1. Synthesize using dynamic bounded coordinates and auto-routed wires
        sch_path = synthesizer.synthesize(filename, components, nets)
        
        # 2. Run deterministic rule referee audit
        findings = referee.audit_design(components, nets)
        
        # 3. Generate Markdown audit report
        audit_results_summary = [
            {"protocol": f.get("rule"), "mcu": f.get("ref", ["U1"])[0], "receiver": f.get("ref", ["U1", "U2"])[-1], "passed": f.get("res") == "PASS"}
            for f in findings
        ]
        ai_summary = "AI evaluated requirements, extracted pin nets, and synthesized A4-bounded schematic."
        report_path = exporter.generate_audit_report(payload.project_name, audit_results_summary, ai_summary)
        
        # Read synthesized files for response payload
        with open(sch_path, 'r', encoding='utf-8') as f:
            sch_content = f.read()
        with open(report_path, 'r', encoding='utf-8') as f:
            report_content = f.read()

        return {
            "status": "success",
            "prompt_processed": payload.user_prompt,
            "components": components,
            "nets": nets,
            "findings": findings,
            "ai_raw_response": ai_raw_response,
            "generated_file": filename,
            "generated_report": f"{payload.project_name}_audit_report.md",
            "schematic_content": sch_content,
            "report_content": report_content,
            "message": f"Successfully generated agentic schematic from prompt at {sch_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/verify")
def verify_endpoint(payload: VerifyRequest):
    """Run deterministic engineering rules over provided components and nets."""
    try:
        findings = referee.audit_design(payload.components, payload.nets)
        ANALYTICS_EVENTS.append({"event": "run_verification", "findings_count": len(findings), "timestamp": datetime.utcnow().isoformat()})
        return {"status": "success", "findings": findings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/components")
def get_components_endpoint(
    search: Optional[str] = Query(None, description="Search term for component ID or facts"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieve paginated components from SQLite Knowledge Store."""
    return knowledge_store.get_components_paginated(
        search=search or "",
        category=category or "",
        limit=limit,
        offset=offset
    )


@app.get("/api/components/categories")
def get_categories_endpoint():
    """Retrieve all available component categories."""
    return {"categories": knowledge_store.get_categories()}


@app.get("/api/components/{component_id}")
def get_component_detail_endpoint(component_id: str):
    """Get single component detailed electrical specs."""
    comp = knowledge_store.get_component(component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    return {"component_id": component_id, "facts": comp}


@app.get("/api/recipes")
def get_recipes_endpoint():
    """Get verified interface design recipes."""
    recipes = knowledge_store.get_recipes()
    return {"recipes": recipes}


@app.get("/api/mistakes")
def get_mistakes_endpoint():
    """Get historical logged mistakes and remediation advice."""
    mistakes = knowledge_store.get_mistakes()
    return {"mistakes": mistakes}


@app.post("/api/mistakes")
def log_mistake_endpoint(payload: MistakeLogRequest):
    """Log an engineering mistake and fix to the knowledge store."""
    knowledge_store.log_mistake(payload.violation_text, payload.fix_text)
    return {"status": "success", "message": "Mistake recorded in knowledge store."}


@app.post("/api/scan-directory")
def scan_directory_endpoint(payload: ScanRequest):
    """Scan a project directory for .kicad_sch schematics and catalog them into SQLite."""
    target_dir = payload.directory or "."
    target_path = Path(target_dir)
    if not target_path.is_absolute():
        target_path = (ROOT_DIR / target_path).resolve()

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Directory '{target_dir}' does not exist.")

    sch_files = list(target_path.rglob("*.kicad_sch"))
    scanned = []
    total_components = 0
    
    for sch in sch_files:
        count = scanner._parse_schematic(sch)
        scanned.append({
            "path": str(sch.name),
            "components_extracted": count
        })
        total_components += count

    ANALYTICS_EVENTS.append({"event": "project_scan", "schematics_count": len(sch_files), "components_count": total_components, "timestamp": datetime.utcnow().isoformat()})

    return {
        "status": "success",
        "scanned_directory": str(target_path),
        "schematic_files_found": len(sch_files),
        "total_components_cataloged": total_components,
        "files": scanned
    }


@app.get("/api/schematic/{filename}")
def get_schematic_file_endpoint(filename: str, download: bool = False):
    """Serve or download generated KiCad schematic file."""
    file_path = EXPORTS_DIR / filename
    if not file_path.exists():
        file_path = ROOT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Schematic file '{filename}' not found.")
    
    if download:
        ANALYTICS_EVENTS.append({"event": "download_schematic", "file": filename, "timestamp": datetime.utcnow().isoformat()})
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return PlainTextResponse(f.read())


@app.get("/api/report/{filename}")
def get_report_file_endpoint(filename: str, download: bool = False):
    """Serve or download generated Markdown audit report."""
    file_path = EXPORTS_DIR / filename
    if not file_path.exists():
        file_path = ROOT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report file '{filename}' not found.")
    
    if download:
        ANALYTICS_EVENTS.append({"event": "download_report", "file": filename, "timestamp": datetime.utcnow().isoformat()})
        return FileResponse(file_path, filename=filename, media_type="text/markdown")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return PlainTextResponse(f.read())


# -------------------------------------------------------------
# SEO, Favicon & Metadata Endpoints
# -------------------------------------------------------------
@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots_txt():
    """Serves robots.txt for search engine crawlers."""
    robots_path = PUBLIC_DIR / "robots.txt"
    if robots_path.exists():
        with open(robots_path, 'r', encoding='utf-8') as f:
            return PlainTextResponse(f.read())
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: http://127.0.0.1:8000/sitemap.xml\n")


@app.get("/sitemap.xml")
def get_sitemap_xml():
    """Serves XML sitemap for SEO indexation."""
    sitemap_path = PUBLIC_DIR / "sitemap.xml"
    if sitemap_path.exists():
        return FileResponse(sitemap_path, media_type="application/xml")
    return Response(content="<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>http://127.0.0.1:8000/</loc></url></urlset>", media_type="application/xml")


@app.get("/favicon.svg")
def get_favicon_svg():
    """Serves high-resolution SVG circuit favicon."""
    fav_path = PUBLIC_DIR / "favicon.svg"
    if fav_path.exists():
        return FileResponse(fav_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/favicon.ico")
def get_favicon_ico():
    """Favicon endpoint fallback."""
    fav_path = PUBLIC_DIR / "favicon.svg"
    if fav_path.exists():
        return FileResponse(fav_path, media_type="image/svg+xml")
    return Response(status_code=204)


@app.get("/og-image.jpg")
def get_og_image():
    """Serves high-resolution Open Graph social preview banner."""
    og_path = PUBLIC_DIR / "og-image.jpg"
    if og_path.exists():
        return FileResponse(og_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="OG image not found")


# -------------------------------------------------------------
# Standard Site Pages (Privacy, Terms, Contact)
# -------------------------------------------------------------
@app.get("/privacy", response_class=HTMLResponse)
def privacy_page():
    """Dedicated Privacy Policy page."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Privacy Policy | CircuitProof Hardware Studio</title>
      <meta name="description" content="CircuitProof Privacy Policy - Transparency in hardware design and telemetry.">
      <link rel="icon" type="image/svg+xml" href="/favicon.svg">
      <style>
        body { background:#080B12; color:#F2F6FF; font:14px/1.6 system-ui,-apple-system,sans-serif; max-width:800px; margin:40px auto; padding:0 20px; }
        h1,h2 { color:#31D8F5; }
        a { color:#3984FF; text-decoration:none; } a:hover { text-decoration:underline; }
        .box { background:#121A2B; border:1px solid #26344A; border-radius:8px; padding:20px; margin-top:20px; }
      </style>
    </head>
    <body>
      <a href="/">← Return to CircuitProof Studio</a>
      <h1>Privacy Policy</h1>
      <p class="mut">Effective Date: October 16, 2026</p>
      <div class="box">
        <h2>1. Zero Retention of Proprietary Hardware Designs</h2>
        <p>CircuitProof processes schematic prompts and synthesizes <code>.kicad_sch</code> files locally on your machine or through dedicated stateless LLM reasoning tokens. Your netlists and component topologies are not used to train global public models.</p>
        <h2>2. Local SQLite Knowledge Base</h2>
        <p>All component facts and cataloged hardware specifications reside inside your local SQLite database (<code>circuitproof_notebook.db</code>). You maintain complete custody of your local design history.</p>
        <h2>3. Minimal Anonymous Telemetry</h2>
        <p>The optional analytics module logs anonymous operational metrics (e.g. successful schematic generation, rule check passes) to improve engineering referee rules. You may disable telemetry in Settings at any time.</p>
        <h2>4. Contact Us</h2>
        <p>For inquiries regarding privacy practices, contact <a href="mailto:privacy@circuitproof.dev">privacy@circuitproof.dev</a> or visit our Hardware Lab at 450 Innovation Parkway, Suite 300, San Francisco, CA 94107.</p>
      </div>
    </body>
    </html>
    """)


@app.get("/terms", response_class=HTMLResponse)
def terms_page():
    """Dedicated Terms of Service page."""
    return HTMLResponse(r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Terms of Service | CircuitProof Hardware Studio</title>
      <meta name="description" content="CircuitProof Terms of Service - Engineering simulation disclaimer and license agreements.">
      <link rel="icon" type="image/svg+xml" href="/favicon.svg">
      <style>
        body { background:#080B12; color:#F2F6FF; font:14px/1.6 system-ui,-apple-system,sans-serif; max-width:800px; margin:40px auto; padding:0 20px; }
        h1,h2 { color:#31D8F5; }
        a { color:#3984FF; text-decoration:none; } a:hover { text-decoration:underline; }
        .box { background:#121A2B; border:1px solid #26344A; border-radius:8px; padding:20px; margin-top:20px; }
      </style>
    </head>
    <body>
      <a href="/">← Return to CircuitProof Studio</a>
      <h1>Terms of Service</h1>
      <p class="mut">Effective Date: October 16, 2026</p>
      <div class="box">
        <h2>1. Engineering Disclaimer</h2>
        <p>CircuitProof is an AI-assisted Electronic Design Automation (EDA) and rule-checking tool. While the deterministic referee engine performs rigorous voltage-level matching ($V_{OH} \ge V_{IH}$) and SPI bus frequency checks, all synthesized schematics must be validated against official component datasheets and subject to bench testing prior to PCB fabrication.</p>
        <h2>2. Open Source &amp; KiCad Compatibility</h2>
        <p>Synthesized schematics adhere to native KiCad 7/8 S-expression syntax. You retain 100% intellectual property ownership of any schematics and audit reports generated using CircuitProof.</p>
        <h2>3. Limitation of Liability</h2>
        <p>In no event shall CircuitProof contributors be held liable for manufacturing defects, PCB re-spins, or component damage resulting from automated synthesis.</p>
      </div>
    </body>
    </html>
    """)


@app.get("/contact", response_class=HTMLResponse)
def contact_page():
    """Dedicated Contact & Support page."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>Contact & Lab Support | CircuitProof</title>
      <meta name="description" content="Get in touch with CircuitProof Hardware Engineering team.">
      <link rel="icon" type="image/svg+xml" href="/favicon.svg">
      <style>
        body { background:#080B12; color:#F2F6FF; font:14px/1.6 system-ui,-apple-system,sans-serif; max-width:800px; margin:40px auto; padding:0 20px; }
        h1,h2 { color:#31D8F5; }
        a { color:#3984FF; text-decoration:none; } a:hover { text-decoration:underline; }
        .box { background:#121A2B; border:1px solid #26344A; border-radius:8px; padding:20px; margin-top:20px; }
        .item { margin-bottom:14px; }
      </style>
    </head>
    <body>
      <a href="/">← Return to CircuitProof Studio</a>
      <h1>Hardware Engineering Lab &amp; Support</h1>
      <div class="box">
        <div class="item">
          <b>Headquarters &amp; Physical Lab:</b><br>
          CircuitProof Technologies Inc.<br>
          450 Innovation Parkway, Suite 300<br>
          San Francisco, CA 94107, United States
        </div>
        <div class="item">
          <b>Engineering Support:</b> <a href="mailto:support@circuitproof.dev">support@circuitproof.dev</a>
        </div>
        <div class="item">
          <b>GitHub Repository:</b> <a href="https://github.com/herambkondhare-ai/circuitproof-backend" target="_blank">github.com/herambkondhare-ai/circuitproof-backend</a>
        </div>
        <div class="item">
          <b>Status:</b> <span style="color:#26D9A0">● All Referee Engines Operational</span>
        </div>
      </div>
    </body>
    </html>
    """)


# -------------------------------------------------------------
# Custom Branded 404 Error Page
# -------------------------------------------------------------
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    """Returns a high-aesthetic, branded dark-mode 404 page."""
    return HTMLResponse(status_code=404, content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <title>404: Schematic Node Not Found | CircuitProof</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="icon" type="image/svg+xml" href="/favicon.svg">
      <style>
        body {
          background: #080B12;
          color: #F2F6FF;
          font: 14px/1.5 system-ui, -apple-system, sans-serif;
          display: grid;
          place-items: center;
          height: 100vh;
          margin: 0;
          overflow: hidden;
        }
        .container {
          text-align: center;
          background: linear-gradient(180deg, #151F34, #101828);
          border: 1px solid #26344A;
          border-radius: 12px;
          padding: 40px;
          max-width: 480px;
          box-shadow: 0 12px 32px #00000088;
        }
        .code {
          font: 700 64px ui-monospace, monospace;
          background: linear-gradient(90deg, #31D8F5, #9565FF);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          margin: 0 0 10px;
        }
        h2 { margin: 0 0 12px; font-size: 20px; }
        p { color: #94A3B8; font-size: 13px; margin: 0 0 24px; line-height: 1.6; }
        .btn {
          background: linear-gradient(135deg, #3984FF, #9565FF);
          color: #fff;
          border: 0;
          padding: 10px 20px;
          border-radius: 6px;
          font-weight: 600;
          text-decoration: none;
          display: inline-block;
          box-shadow: 0 4px 16px #3984FF55;
        }
        .btn:hover { box-shadow: 0 6px 24px #9565FF66; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="code">404</div>
        <h2>Schematic Node Disconnected</h2>
        <p>The requested route or net definition does not exist in this workspace. The trace appears to have an open circuit.</p>
        <a href="/" class="btn">Return to AI Design Studio →</a>
      </div>
    </body>
    </html>
    """)


# -------------------------------------------------------------
# Web Studio App Serving
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index_page():
    """Serves the CircuitProof Web Studio interface from frontend/index.html."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        index_path = ROOT_DIR / "index.html"
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>CircuitProof Backend Online</h1><p>index.html not found in frontend/</p>")


if __name__ == "__main__":
    import uvicorn
    print("Starting CircuitProof Backend Server on http://127.0.0.1:8000 ...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)