# Checks whether any source document or stored response could display a "6"
# the user may have read as "6 extractos".
import json
import re
import sqlite3

con = sqlite3.connect("users.db")
con.row_factory = sqlite3.Row

print("documents with parent/child counts involving 6:")
for r in con.execute(
    "SELECT title, total_parents, total_children FROM documents "
    "WHERE total_parents = 6 OR total_children = 6"
):
    print("  -", dict(r))

print("\nall document counts:")
for r in con.execute("SELECT title, total_parents, total_children FROM documents ORDER BY created_at DESC"):
    print("  -", dict(r))

print("\noccurrences of standalone '6' in aviso/observaciones/intro fields:")
for r in con.execute("SELECT id, response_json FROM contenidos WHERE response_json IS NOT NULL"):
    data = json.loads(r["response_json"])
    meta = data.get("metadatos") or {}
    ev = data.get("evaluacion_calidad") or {}
    intro = (data.get("contenido_adaptado") or {}).get("introduccion_contextualizada") or ""
    fields = {
        "aviso_cantidad": meta.get("aviso_cantidad"),
        "observaciones": ev.get("observaciones"),
        "intro": intro,
        "items_solicitados": meta.get("items_solicitados"),
        "items_generados": meta.get("items_generados"),
    }
    for key, val in fields.items():
        if isinstance(val, str) and re.search(r"\b6\b", val):
            print(f"  {r['id']} [{key}]: {val[:180]}")
