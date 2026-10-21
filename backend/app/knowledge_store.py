"""
Knowledge Store (knowledge_store.py)
Manages the SQLite database (`circuitproof_notebook.db`) for component facts and historical mistakes.
"""

import os
import sqlite3
import json
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "circuitproof_notebook.db"

class KnowledgeStore:
    def __init__(self, db_name=None):
        if db_name is None or db_name == "circuitproof_notebook.db":
            if DEFAULT_DB.exists():
                db_name = str(DEFAULT_DB)
            elif Path("circuitproof_notebook.db").exists():
                db_name = "circuitproof_notebook.db"
            else:
                db_name = str(DEFAULT_DB)
        self.db_path = str(db_name)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components (
                component_id TEXT PRIMARY KEY,
                category TEXT,
                facts_json TEXT,
                verified INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_text TEXT,
                fix_text TEXT,
                occurrence_count INTEGER
            )
        ''')
        self.conn.commit()

    def save_component(self, component_id, category, facts_dict, verified=1):
        cursor = self.conn.cursor()
        facts_str = json.dumps(facts_dict)
        cursor.execute('''
            INSERT OR REPLACE INTO components (component_id, category, facts_json, verified_by_human)
            VALUES (?, ?, ?, ?)
        ''', (component_id, category, facts_str, verified))
        self.conn.commit()
        print(f"[KnowledgeStore]: Saved component '{component_id}' (Verified: {verified})")

    def get_component(self, component_id):
        """Retrieves and decodes component facts from SQLite."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT facts_json FROM components WHERE component_id = ?", (component_id,))
        row = cursor.fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return None

    def log_mistake(self, violation_text, fix_text):
        cursor = self.conn.cursor()
        cursor.execute("SELECT mistake_id, occurrence_count FROM mistakes WHERE violation_text = ?", (violation_text,))
        row = cursor.fetchone()
        if row:
            new_count = row[1] + 1
            cursor.execute("UPDATE mistakes SET occurrence_count = ? WHERE mistake_id = ?", (new_count, row[0]))
        else:
            cursor.execute("INSERT INTO mistakes (violation_text, fix_text, occurrence_count) VALUES (?, ?, 1)", (violation_text, fix_text))
        self.conn.commit()

    def get_components_paginated(self, search="", category="", limit=50, offset=0):
        cursor = self.conn.cursor()
        query = "SELECT component_id, category, facts_json, verified_by_human FROM components WHERE 1=1"
        params = []
        if search:
            query += " AND (component_id LIKE ? OR facts_json LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term])
        if category:
            query += " AND category = ?"
            params.append(category)

        count_query = "SELECT COUNT(*) FROM (" + query + ")"
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        query += " ORDER BY component_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for cid, cat, facts_str, ver in rows:
            facts = {}
            if facts_str:
                try:
                    facts = json.loads(facts_str)
                except Exception:
                    facts = {"raw": facts_str}
            results.append({
                "component_id": cid,
                "category": cat,
                "facts": facts,
                "verified": ver
            })
        return {"total": total, "components": results}

    def get_categories(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM components WHERE category IS NOT NULL AND category != '' ORDER BY category ASC")
        return [r[0] for r in cursor.fetchall()]

    def get_recipes(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT recipe_id, interface_type, design_summary, circuit_json FROM recipes")
            rows = cursor.fetchall()
            recipes = []
            for rid, itype, summary, c_json in rows:
                c_data = {}
                try:
                    c_data = json.loads(c_json) if c_json else {}
                except Exception:
                    c_data = {"raw": c_json}
                recipes.append({
                    "recipe_id": rid,
                    "interface_type": itype,
                    "design_summary": summary,
                    "circuit": c_data
                })
            return recipes
        except Exception:
            return []

    def get_mistakes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT mistake_id, violation_text, fix_text, occurrence_count FROM mistakes ORDER BY occurrence_count DESC, mistake_id DESC")
        rows = cursor.fetchall()
        return [{
            "id": r[0],
            "violation_text": r[1],
            "fix_text": r[2],
            "occurrence_count": r[3]
        } for r in rows]

    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        comp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mistakes")
        mistake_count = cursor.fetchone()[0]
        recipe_count = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM recipes")
            recipe_count = cursor.fetchone()[0]
        except Exception:
            pass
        return {
            "total_components": comp_count,
            "total_mistakes": mistake_count,
            "total_recipes": recipe_count
        }

    def close(self):
        self.conn.close()