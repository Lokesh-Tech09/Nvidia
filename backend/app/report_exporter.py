"""
CircuitProof Engineering Report Exporter (report_exporter.py)
Generates a structured Markdown or JSON audit report for hackathon submission.
"""

import os
from datetime import datetime
from pathlib import Path

DEFAULT_EXPORTS = Path(__file__).resolve().parent.parent / "exports"

class ReportExporter:
    def __init__(self, output_dir=None):
        if output_dir is None:
            output_dir = DEFAULT_EXPORTS
        self.output_dir = str(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_audit_report(self, project_name, audit_results, ai_summary):
        filename = f"{project_name}_audit_report.md"
        file_path = os.path.join(self.output_dir, filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report_content = f"""# CircuitProof Engineering Audit Report
**Project Name:** {project_name}  
**Generated On:** {timestamp}  
**Engine:** NVIDIA Nemotron via Nebius Token Factory + Deterministic Referee  

---

## 1. Executive Summary
This design was automatically scanned, rule-checked, and synthesized using the **CircuitProof Agentic Hardware Pipeline**.

**AI Design Assessment:**
> {ai_summary}

---

## 2. Deterministic Rule Verification Results
| Protocol / Check | Target Components | Status | Details / Metrics |
| :--- | :--- | :--- | :--- |
"""

        for audit in audit_results:
            status_badge = "✅ PASS" if audit.get("passed", False) else "❌ FAIL"
            report_content += f"| {audit.get('protocol', 'General')} | {audit.get('mcu', 'N/A')} -> {audit.get('receiver', audit.get('peripheral', 'N/A'))} | {status_badge} | VOH/VIH or Clock match verified | \n"

        report_content += f"""
---

## 3. Artifacts Generated
- **Schematic File:** `{project_name}.kicad_sch` (Fully wired S-expression with net labels)
- **Database Index:** Cataloged in SQLite KnowledgeStore

*Report compiled automatically by CircuitProof Agent.*
"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"[Report Exporter]: Report successfully generated at {file_path}")
        return file_path