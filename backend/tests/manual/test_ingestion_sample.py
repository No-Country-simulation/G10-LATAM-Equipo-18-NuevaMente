"""
test_ingestion_sample.py

Propósito:
    Prueba visual y automática del pipeline de ingesta (limpieza de texto,
    filtro de ruido y chunking) usando un manual de muestra que contiene los
    casos que se deben limpiar o descartar: portada y página legal, historial
    de revisiones, índices con puntos guía, separadores de capítulo, páginas
    en blanco, apéndices normativos, ligaduras, palabras cortadas, numeración
    de página y marcas de Markdown. También incluye contenido que debe
    conservarse (advertencias cortas, tablas, identificadores técnicos).

Entrada:
    - tests/manual/sample_docs/sample_manual.md, o la ruta de otro archivo
      pasada como argumento (en ese caso solo se muestran los chunks, sin
      verificaciones).

Salida:
    Por pantalla: resumen del documento, reporte de ruido (si existe),
    secciones resultantes, 10 chunks de muestra y el resultado de cada
    verificación. Con pytest, el test falla si alguna verificación no se cumple.

Uso:
    python tests/manual/test_ingestion_sample.py [archivo]
    pytest tests/manual/test_ingestion_sample.py -s
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Busca hacia arriba la carpeta que contiene el paquete app (backend) y la agrega al path
CARPETA_BACKEND = next(p for p in Path(__file__).resolve().parents if (p / "app").is_dir())
sys.path.insert(0, str(CARPETA_BACKEND))

from app.services.ingester_service import IngesterService  # noqa: E402

RUTA_MUESTRA = Path(__file__).resolve().parent / "sample_docs" / "sample_manual.md"
CANTIDAD_MUESTRA = 19
LINEA = "=" * 78

# Cada verificación es (descripción, texto buscado, debe_aparecer).
# Las que tienen debe_aparecer=False comprueban que el ruido fue eliminado;
# las que tienen True comprueban que el contenido técnico se conservó.
VERIFICACIONES = [
    # Ruido que debe desaparecer
    ("Copyright en inglés eliminado", "All rights reserved", False),
    ("Derechos reservados en español eliminado", "Todos los derechos reservados", False),
    ("Aviso legal eliminado", "sin garantía expresa", False),
    ("Historial de revisiones eliminado", "Corrección de erratas", False),
    ("Índice general con puntos guía eliminado", ". . . . .", False),
    ("Lista de tablas con puntos guía eliminada", ".......", False),
    ("Índice de figuras eliminado", "Vista explosionada", False),
    ("Página en blanco eliminada", "Página en blanco", False),
    ("Separador de capítulo eliminado", "INTRODUCCIÓN", False),
    ("Apéndice de conformidad CE eliminado", "declara bajo su exclusiva responsabilidad", False),
    ("Apéndice ambiental eliminado", "Reglamento REACH", False),
    # Limpieza de texto
    ("Numeración 'Página N de M' eliminada", "Página 5 de 100", False),
    ("Numeración '- N -' eliminada", "- 13 -", False),
    ("Ligadura reemplazada por letras", "\ufb01", False),
    ("Espacio no separable reemplazado", "\u00a0", False),
    ("Guion blando eliminado", "\u00ad", False),
    ("Palabra 'proce-' unida", "proce-", False),
    ("Palabra 'cavi-' unida", "cavi-", False),
    ("Negrita de Markdown eliminada", "**", False),
    # Contenido que debe conservarse
    ("Ligadura convertida en 'eficiente'", "eficiente", True),
    ("Palabra unida 'procedimiento de arranque'", "El procedimiento de arranque comienza", True),
    ("Palabra unida 'cavitación'", "cavitación", True),
    ("Advertencia corta conservada", "PELIGRO: desconecte la corriente", True),
    ("Identificador con guion bajo intacto", "PART_NUMBER_A1", True),
    ("Comparación 'temp > 80°C' intacta", "temp > 80°C", True),
    ("Bloque de código conservado", "PARAM_TEMP_MAX", True),
    ("Texto técnico con 'ISO 9001' y 'Copyright' conservado", "Los rodamientos cumplen ISO 9001", True),
    ("Tabla de datos técnicos conservada", "Caudal máximo", True),
    ("Tabla de solución de problemas conservada", "Alarma E-14", True),
    ("Pasos de arranque conservados", "purgue el aire", True),
    ("Pruebas de aislamiento conservadas", "megóhmetro", True),
    ("Ajuste del sello conservado", "par de apriete de 25 Nm", True),
    ("Almacenamiento y transporte conservado", "cáncamos de elevación", True),
    ("Contexto jerárquico de capítulo conservado", "Capítulo 1 > 1.1 Descripción general", True),
]


def procesar_documento(ruta: Path) -> tuple:
    """Ejecuta la ingesta y arma los chunks padre/hijo; devuelve (documento, payload)."""
    ingester = IngesterService()
    documento = ingester.process_document(ruta, title="Manual de muestra", document_id="muestra-test")
    payload = ingester.build_rag_chunks(documento)
    return documento, payload


def seleccionar_muestra(chunks: List[Dict[str, Any]], cantidad: int) -> List[Dict[str, Any]]:
    """Elige `cantidad` chunks equiespaciados para cubrir todo el documento."""
    if len(chunks) <= cantidad:
        return list(chunks)
    pasos = cantidad - 1
    indices = sorted({round(i * (len(chunks) - 1) / pasos) for i in range(cantidad)})
    return [chunks[i] for i in indices]


def imprimir_resumen(documento: Any, payload: Dict[str, Any]) -> None:
    """Muestra cuántos caracteres y chunks quedaron frente al texto original."""
    caracteres_originales = len(documento.raw_text)
    caracteres_conservados = sum(len(p["content"]) for p in payload["parent_chunks"])
    print(f"\n{LINEA}\nRESUMEN\n{LINEA}")
    print(f"Archivo:                {documento.source_filename}")
    print(f"Caracteres originales:  {caracteres_originales}")
    print(f"Caracteres conservados: {caracteres_conservados}")
    print(f"Secciones (padres):     {payload['total_parents']}")
    print(f"Fragmentos (hijos):     {payload['total_children']}")


def imprimir_reporte_ruido(documento: Any) -> None:
    """Muestra qué secciones descartó el filtro de ruido y por qué, si hay reporte."""
    print(f"\n{LINEA}\nREPORTE DE RUIDO\n{LINEA}")
    reporte = getattr(documento, "noise_report", None)
    if reporte is None:
        print("Sin reporte (el filtro de ruido no está integrado o está desactivado).")
        return

    print(f"Modo de prueba (dry run): {'sí' if reporte.dry_run else 'no'}")
    print(f"Ruido detectado: {reporte.discarded_chars} de {reporte.total_chars} caracteres "
          f"({reporte.discard_ratio:.0%})")
    if reporte.skipped_reason:
        print(f"Filtro omitido: {reporte.skipped_reason}")
    for entrada in reporte.entries:
        estado = "DESCARTADA" if entrada.discarded else "detectada"
        print(f"  [{estado}] {entrada.category} | {entrada.section_title!r} | "
              f"{entrada.char_count} caracteres | {entrada.reason}")


def imprimir_secciones(payload: Dict[str, Any]) -> None:
    """Lista las secciones que sobrevivieron, con su tamaño."""
    print(f"\n{LINEA}\nSECCIONES CONSERVADAS\n{LINEA}")
    for padre in payload["parent_chunks"]:
        print(f"  {padre['id']:<12} {len(padre['content']):>5} caracteres | {padre['title']}")


def imprimir_muestra(payload: Dict[str, Any]) -> None:
    """Imprime una muestra equiespaciada de chunks hijo (los que se envían a embedding)."""
    hijos = payload["child_chunks"]
    muestra = seleccionar_muestra(hijos, CANTIDAD_MUESTRA)
    print(f"\n{LINEA}\nMUESTRA DE {len(muestra)} CHUNKS (de {len(hijos)} en total)\n{LINEA}")
    for numero, hijo in enumerate(muestra, start=1):
        print(f"\n--- Chunk {numero} de {len(muestra)} | id: {hijo['id']} | "
              f"{len(hijo['content'])} caracteres ---")
        print(f"Ruta: {hijo['breadcrumb']}")
        print(hijo["content"])


def ejecutar_verificaciones(payload: Dict[str, Any]) -> List[str]:
    """Comprueba cada verificación contra el texto de todas las secciones;
    imprime el resultado y devuelve la lista de las que fallaron."""
    texto = "\n".join(f"{p['title']}\n{p['content']}" for p in payload["parent_chunks"])
    fallas: List[str] = []

    print(f"\n{LINEA}\nVERIFICACIONES\n{LINEA}")
    for descripcion, buscado, debe_aparecer in VERIFICACIONES:
        aparece = buscado in texto
        cumple = aparece == debe_aparecer
        marca = "[OK]   " if cumple else "[FALLA]"
        detalle = "" if cumple else (" (sigue presente)" if aparece else " (no se encontró)")
        print(f"{marca} {descripcion}{detalle}")
        if not cumple:
            fallas.append(descripcion)

    print(f"\nResultado: {len(VERIFICACIONES) - len(fallas)} de {len(VERIFICACIONES)} verificaciones correctas.")
    return fallas


def ejecutar(ruta: Path, verificar: bool = True) -> List[str]:
    """Procesa el archivo, imprime todos los reportes y devuelve las verificaciones fallidas."""
    # Evita errores de codificación al imprimir en consolas de Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    documento, payload = procesar_documento(ruta)
    imprimir_resumen(documento, payload)
    imprimir_reporte_ruido(documento)
    imprimir_secciones(payload)
    imprimir_muestra(payload)

    return ejecutar_verificaciones(payload) if verificar else []


def test_ingesta_manual_de_muestra() -> None:
    """Procesa el manual de muestra, muestra 10 chunks y falla si alguna verificación no se cumple."""
    fallas = ejecutar(RUTA_MUESTRA)
    assert not fallas, "Verificaciones fallidas: " + "; ".join(fallas)


if __name__ == "__main__":
    ruta_argumento: Optional[Path] = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    resultado = ejecutar(ruta_argumento or RUTA_MUESTRA, verificar=ruta_argumento is None)
    sys.exit(1 if resultado else 0)