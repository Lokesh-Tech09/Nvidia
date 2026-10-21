# CircuitProof

> **Autonomous Agentic Hardware Design, Verification & Schematic Synthesis Studio**

CircuitProof is an AI-powered electronic design automation (EDA) platform. It translates natural language circuit requirements into bounded, verified KiCad schematics using LLM reasoning (NVIDIA Nemotron via Nebius Studio / local Ollama) combined with deterministic hardware engineering rule validation and an indexed SQLite database of 40,000+ electronic parts.

---

## 📁 Clean Architecture & Project Structure

The project is cleanly divided into **Frontend** and **Backend** directories:

```
circuitproof/
├── backend/                        # Backend Application & Engines
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI REST API & Static Serving
│   │   ├── circuitproof_core.py    # Deterministic Referee Rule Engine
│   │   ├── cloud_reviewer.py       # NVIDIA Nemotron / Ollama AI Reviewer
│   │   ├── generator.py            # Bounded KiCad S-Expression Synthesizer
│   │   ├── knowledge_store.py      # SQLite Knowledge Base Layer
│   │   ├── load_components.py      # Component Ingestion Script
│   │   ├── report_exporter.py      # Markdown Engineering Audit Exporter
│   │   └── scan_project.py         # Recursive KiCad Project Scanner
│   ├── data/
│   │   └── circuitproof_notebook.db# SQLite Database (40,000+ Components)
│   ├── exports/                    # Generated .kicad_sch & Audit Reports
│   └── requirements.txt            # Backend Python Dependencies
│
├── frontend/                       # Web Studio Frontend Application
│   ├── index.html                  # Main Interactive Circuit Lab Studio
│   └── public/                     # Public Web Assets (SEO & Branding)
│       ├── favicon.svg             # Vector IC Circuit Favicon
│       ├── og-image.jpg            # High-Resolution Open Graph Banner
│       ├── robots.txt              # Search Engine Crawler Directives
│       └── sitemap.xml             # Search Indexation Sitemap
│
├── run.py                          # Single-Command Application Launcher
├── .gitignore                      # Git Ignore Configuration
└── README.md                       # Documentation
```

---

## ⚡ Core Engine Flow

```
                  +-----------------------------------+
                  |   User Natural Language Prompt    |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |          Cloud Reviewer           |
                  |  (NVIDIA Nemotron / Nebius /      |
                  |        Ollama Fallback)           |
                  +-----------------+-----------------+
                                    |
                          (Components & Nets JSON)
                                    |
                                    v
     +------------------------------+------------------------------+
     |                                                             |
     v                                                             v
+-----------------------------+               +-----------------------------+
|    Schematic Synthesizer    |               |   Circuit Referee Engine    |
| - Bounded A4 Grid Geometry  |               | - Logic Level (VOH >= VIH)  |
| - Auto Wire & Net Routing   |               | - SPI Clock Margin Rules    |
| - KiCad S-Expression Output |               | - Mistake Memory Logging    |
+--------------+--------------+               +--------------+--------------+
               |                                             |
               v                                             v
     +--------------------+                       +--------------------+
     | backend/exports/   |                       | backend/exports/   |
     | *.kicad_sch File   |                       | *_audit_report.md  |
     +--------------------+                       +--------------------+
                                    ^
                                    |
                     +--------------+--------------+
                     |  Knowledge Store (SQLite)   |
                     | - 40,000+ Components Facts  |
                     | - Electrical Rail Limits    |
                     | - Verified Design Recipes   |
                     +-----------------------------+
```

---

## 🛠️ Modules Breakdown

### 🖥️ Frontend (`frontend/`)
- **[frontend/index.html](frontend/index.html)**: The modern dark-mode hardware design studio.
  - Interactive SVG schematic canvas with drag, zoom, fit, grid toggle, net highlight.
  - Real-time generation pipeline (`Understand` → `Plan` → `Verify` → `Synthesize` → `Deliver`).
  - Verification Center with live severity badges, calculated deltas, and recommended fixes.
  - Component Library browser with instant search and pagination.
  - Design Recipes and continuous learning mistake memory.
  - Thank-You modal upon successful synthesis with one-click `.kicad_sch` export.
- **[frontend/public/](frontend/public/)**:
  - `favicon.svg`: Custom circuit chip favicon.
  - `og-image.jpg`: 16:9 high-resolution social preview image.
  - `robots.txt`: Search crawler directives.
  - `sitemap.xml`: Sitemap indexation.

### ⚙️ Backend (`backend/`)
- **[backend/app/main.py](backend/app/main.py)**: FastAPI REST backend serving API routes, security headers, custom 404 page, and static frontend assets.
- **[backend/app/circuitproof_core.py](backend/app/circuitproof_core.py)**: Deterministic hardware referee validating electrical logic levels and timing.
- **[backend/app/cloud_reviewer.py](backend/app/cloud_reviewer.py)**: NVIDIA Nemotron-4-34B-Instruct via Nebius Studio with local Ollama fallback.
- **[backend/app/generator.py](backend/app/generator.py)**: Bounded KiCad 7/8 schematic synthesizer writing to `backend/exports/`.
- **[backend/app/knowledge_store.py](backend/app/knowledge_store.py)**: SQLite data access layer for component facts, recipes, and mistake memory.
- **[backend/app/scan_project.py](backend/app/scan_project.py)**: Recursive project scanner parsing `.kicad_sch` files with `sexpdata`.
- **[backend/data/circuitproof_notebook.db](backend/data/circuitproof_notebook.db)**: SQLite database containing 40,000+ components.
- **[backend/exports/](backend/exports/)**: Destination directory for all synthesized `.kicad_sch` and `.md` reports.

---

## 🚀 Getting Started & Running Guide

### 📋 Prerequisites
- **Python**: Version `3.10` or higher (`python --version`)
- **Git**: Installed and configured on your system
- **KiCad (Optional)**: Version 7 or 8 to open, edit, and fabricate generated `.kicad_sch` files
- **Hardware Acceleration / LLM (Optional)**:
  - **NVIDIA Cloud (Nebius Studio)**: For NVIDIA Nemotron-4-34B cloud reasoning (`NEBIUS_API_KEY`)
  - **Ollama (Local Offline)**: For running local LLMs offline (`ollama run nemotron-mini` or `ollama run llama3`)
  *(Note: Even without any API keys or local LLM running, CircuitProof features an intelligent built-in hardware synthesis fallback that produces valid, verified KiCad schematics).*

---

### 📥 1. Clone & Setup Repository

```bash
git clone https://github.com/Lokesh-Tech09/Nvidia.git
cd Nvidia
```

---

### 🐍 2. Create & Activate a Virtual Environment

It is recommended to run the project inside an isolated virtual environment:

- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(If script execution is restricted, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **Windows (Command Prompt / CMD)**:
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```

- **Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

### 📦 3. Install Dependencies

Install all required backend and parsing packages:

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

Verified dependencies installed:
- `fastapi` & `uvicorn` (Asynchronous REST API and static file web server)
- `pydantic` (Data schema validation)
- `openai` (Nebius Studio / NVIDIA Nemotron API client)
- `sexpdata` (KiCad S-Expression parser and AST walker)
- `python-multipart` (Form data parsing)
- `ollama` (Local LLM inference client)

---

### 🔑 4. Environment Configuration (Optional)

If you have access to Nebius Studio for **NVIDIA Nemotron-4-34B-Instruct** inference, set your API key:

- **Windows (PowerShell)**:
  ```powershell
  $env:NEBIUS_API_KEY="your-nebius-api-key-here"
  ```

- **Windows (CMD)**:
  ```cmd
  set NEBIUS_API_KEY=your-nebius-api-key-here
  ```

- **Linux / macOS**:
  ```bash
  export NEBIUS_API_KEY="your-nebius-api-key-here"
  ```

Alternatively, create a `.env` file in the project root:
```env
NEBIUS_API_KEY=your-nebius-api-key-here
```

*(If no key is present, CircuitProof smoothly falls back to local Ollama or the internal deterministic rule engine).*

---

### ⚡ 5. Launch the Application

#### Option A: Single-Command Full Stack (Recommended)
Run the master launcher from the root directory:
```bash
python run.py
```
This automatically boots the FastAPI backend and serves the high-aesthetic dark-mode Web Studio on port `8000`.

#### Option B: Developer Mode with Auto-Reload
If you are developing or modifying backend code:
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### 🖥️ 6. Access Points & Direct URLs

Once running, access the studio and documentation at:

| Service / View | URL | Description |
| :--- | :--- | :--- |
| **Interactive Web Studio** | **[http://127.0.0.1:8000](http://127.0.0.1:8000)** | Full dark-mode EDA design studio and canvas |
| **Interactive API Docs (Swagger)** | **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** | Live OpenAPI test runner for all endpoints |
| **Alternative API Docs (ReDoc)** | **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)** | Comprehensive offline-friendly API specification |
| **System Diagnostics & Health** | **[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)** | JSON health status, version, and component count |
| **Hardware Lab & Support** | **[http://127.0.0.1:8000/contact](http://127.0.0.1:8000/contact)** | Engineering lab headquarters directory |
| **Privacy Policy** | **[http://127.0.0.1:8000/privacy](http://127.0.0.1:8000/privacy)** | Data security and local-first compliance |
| **Terms of Service** | **[http://127.0.0.1:8000/terms](http://127.0.0.1:8000/terms)** | Hardware engineering verification terms |

---

### 🧪 7. Quick Verification & Testing

#### Health Check
Verify the server and SQLite knowledge base (40,500+ parts) are online:
```bash
curl http://127.0.0.1:8000/api/health
```
Expected output:
```json
{
  "status": "healthy",
  "service": "CircuitProof API",
  "version": "2.0.0",
  "database": "circuitproof_notebook.db",
  "total_components": 40502
}
```

#### End-to-End Synthesis Flow in Studio:
1. Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in Chrome, Edge, Firefox, or Safari.
2. In the **Requirements & Copilot** prompt box, try a prompt like:
   > *"Design an STM32F103 sensor interface with a BNO085 IMU over I2C, a 3.3V supply, and SPI flash memory"*
3. Click **Synthesize Circuit**.
4. Observe the live 5-stage agent pipeline:
   - `01 UNDERSTAND` (Prompt normalization)
   - `02 PLAN` (Component & netlist extraction)
   - `03 VERIFY` (Deterministic electrical rule referee)
   - `04 SYNTHESIZE` (Bounded KiCad A4 geometric placement & routing)
   - `05 DELIVER` (Audit report and KiCad schematic generation)
5. Pan and zoom around the interactive SVG schematic canvas, inspect pin connections, toggle the millimeter grid, and click **Download .kicad_sch** to open directly in KiCad!

---

### 🔧 8. Troubleshooting FAQ

- **Port 8000 Already in Use**:
  Run on a different port:
  ```bash
  uvicorn backend.app.main:app --host 127.0.0.1 --port 8080
  ```
- **ModuleNotFoundError: No module named 'backend'**:
  Ensure you are running commands from the root directory (`d:/AIML Stuff/ALL IN` or `Nvidia`). `run.py` handles this automatically.
- **Ollama Connection Refused**:
  If using local Ollama, ensure the Ollama service is active via `ollama serve`. If Ollama is not installed or running, the system will seamlessly use deterministic rule templates.
- **KiCad Schematic Viewing**:
  The synthesized `.kicad_sch` file in `backend/exports/` is 100% compliant with KiCad 7.x and 8.x. Open KiCad, select *File → Open Schematic*, and choose the downloaded file.

---

## 🌐 Endpoints & Features

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the interactive Web Studio (`frontend/index.html`) |
| `/api/health` | `GET` | Server health check and component statistics |
| `/api/generate-from-prompt` | `POST` | Agentic prompt-to-schematic synthesis |
| `/api/verify` | `POST` | Run deterministic electrical rule referee |
| `/api/components` | `GET` | Paginated search across 40k+ SQLite components |
| `/api/components/categories` | `GET` | List distinct component categories |
| `/api/recipes` | `GET` | Retrieve verified interface design recipes |
| `/api/mistakes` | `GET` / `POST` | Query or log engineering mistake memory |
| `/api/scan-directory` | `POST` | Recursively scan folders for KiCad schematics |
| `/api/schematic/{filename}` | `GET` | Download or view generated `.kicad_sch` file |
| `/api/report/{filename}` | `GET` | Download or view generated audit `.md` report |
| `/api/analytics` | `GET` / `POST` | Lightweight privacy-friendly telemetry |
| `/privacy` | `GET` | Dedicated Privacy Policy page |
| `/terms` | `GET` | Dedicated Terms of Service page |
| `/contact` | `GET` | Hardware Lab & Headquarters support directory |
| `/robots.txt` | `GET` | Crawler directives |
| `/sitemap.xml` | `GET` | XML Sitemap |
| `/404` | `GET` | Custom branded dark-mode 404 page |
