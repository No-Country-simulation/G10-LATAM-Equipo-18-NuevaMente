# Prints the quality signals of the latest stored adaptation responses so the
# reported inconsistencies (0% anclaje, "6 extractos", mixed language) can be traced.
import json
import sqlite3

con = sqlite3.connect("users.db")
con.row_factory = sqlite3.Row

rows = con.execute(
    "SELECT id, title, output_format, status, created_at, response_json "
    "FROM contenidos ORDER BY created_at DESC LIMIT 5"
).fetchall()

for r in rows:
    print("=" * 80)
    print(r["id"], "|", r["title"], "|", r["output_format"], "|", r["created_at"], "|", r["status"])
    if not r["response_json"]:
        print("  (sin response_json)")
        continue
    data = json.loads(r["response_json"])
    ev = data.get("evaluacion_calidad") or {}
    meta = data.get("metadatos") or {}
    contenido = data.get("contenido_adaptado") or {}

    print("  anclaje_fuente_score:", ev.get("anclaje_fuente_score") or ev.get("source_grounding_score"))
    print("  claridad:", ev.get("claridad_pedagogica"))
    print("  observaciones:", ev.get("observaciones"))
    per_item = ev.get("per_item") or []
    verified = sum(1 for p in per_item if p.get("origen_verificado"))
    print(f"  per_item: {len(per_item)} elems, verificados(lexico AND revisor): {verified}")
    for p in per_item:
        print("    -", p.get("index"), "lex:", p.get("verificado_lexico"), "rev:", p.get("verificado_revisor"), "issues:", p.get("issues"))
    print("  items_solicitados:", meta.get("items_solicitados"), "items_generados:", meta.get("items_generados"))
    print("  aviso_cantidad:", meta.get("aviso_cantidad"))
    items = contenido.get("items") or []
    print("  contenido items:", len(items))
    resumen = contenido.get("resumen_ejecutivo") or ""
    print("  resumen_ejecutivo parrafos:", resumen.count("\n\n") + 1 if resumen else 0)
    print("  resumen primeros 300:", resumen[:300].replace("\n", " | "))
    if items:
        first = items[0]
        print("  item[0] punto_clave:", str(first.get("punto_clave"))[:160])
        print("  item[0] impacto:", str(first.get("impacto_negocio"))[:160])
        fuentes = first.get("fuentes") or []
        if fuentes:
            print("  item[0] fuente[0] breadcrumb:", fuentes[0].get("breadcrumb"), "| seccion:", fuentes[0].get("seccion"))
    print("  intro:", (contenido.get("introduccion_contextualizada") or "")[:200])
