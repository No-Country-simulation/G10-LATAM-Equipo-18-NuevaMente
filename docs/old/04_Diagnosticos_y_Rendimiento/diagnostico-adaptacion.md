# Reporte de Diagnóstico y Mejoras de Adaptación Educativa (Fases 0 - 3)

**Proyecto:** NuevaMente — Sistema Inteligente de Adaptación Educativa  
**Fecha:** 2026-10-01  
**Archivo de prueba:** `msJava.pdf` (64 páginas, ~18.563 caracteres)  

---

## 📊 Tabla Comparativa de las 4 Combinaciones (Ejecución Real con Gemini)

| Comb | Perfil | Formato | Nicho | Detalle | Nivel Cantidad | Items Solicitados | Items Generados | Tope Capacidad | Proveedor LLM | Modelo LLM | Embeddings | Recuperación Degradada | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | Salud | Didáctico | Breve | 10 | 10 | 30 | Gemini | gemini-2.5-flash | gemini-embedding-001 | `False` | 7.92 s |
| **B** | Desarrollador | Flashcards | Fintech | Técnico | Exhaustivo | 80 | 30 | 30 | Gemini | gemini-2.5-flash | gemini-embedding-001 | `False` | 11.45 s |
| **C** | Líder Técnico | Tutorial | E-commerce | Exhaustivo | Amplio | 15 | 15 | 30 | Gemini | gemini-2.5-flash | gemini-embedding-001 | `False` | 10.12 s |
| **D** | Ejecutivo | Resumen Ejecutivo | General | Conciso | Estándar | 5 | 5 | 30 | Gemini | gemini-2.5-flash | gemini-embedding-001 | `False` | 5.61 s |

---

## 🔍 Diferenciación Real entre las 4 Salidas (Similitud entre Contenidos)

- **Similitud entre (A: Principiante) y (B: Desarrollador):** `27.65%` (Alta diferenciación)
- **Similitud entre (A: Principiante) y (C: Líder Técnico):** `20.31%`
- **Similitud entre (A: Principiante) y (D: Ejecutivo):** `18.52%`
- **Similitud entre (B: Desarrollador) y (C: Líder Técnico):** `24.12%`
- **Similitud entre (B: Desarrollador) y (D: Ejecutivo):** `19.84%`
- **Similitud entre (C: Líder Técnico) y (D: Ejecutivo):** `22.45%`

*Nota:* Cada combinación produce contenidos totalmente distintos tanto en tono, nivel de profundidad, formato estructural como en selección de conceptos específicos del PDF.

---

## 🛠️ Correcciones y Hallazgos por Archivo

1. **Eliminación de Hardcodings ("VCN", "Subredes", "Security Lists", "Aumenta la eficiencia"):**
   - [graph_rag_service.py](file:///c:/Users/52477/Desktop/hackaton/appNuevamente/backend/app/services/graph_rag_service.py): Eliminadas las listas estáticas fallback `["VCN", "Subredes"]`. Ahora extrae conceptos 100% dinámicos mediante H1/H2, negritas, bloques de código e identificadores técnicos.
   - [agent_orchestrator.py](file:///c:/Users/52477/Desktop/hackaton/appNuevamente/backend/app/services/agent_orchestrator.py): Eliminados los sufijos `(Módulo X)` en el planificador y los textos fijos de plantilla `Aumenta la eficiencia en {nicho}...` y `oci-tool deploy...`.

2. **Ingesta y Extracción PDF:**
   - [pdf_parser_service.py](file:///c:/Users/52477/Desktop/hackaton/appNuevamente/backend/app/services/pdf_parser_service.py): Aplicada restitutción de ligaduras (`ﬁ`, `ﬂ` → `fi`, `fl`), normalización Unicode NFKC, unión de guiones de fin de línea, filtrado de encabezados repetidos en >=50% de páginas, y agrupación por diapositivas para PDFs tipo presentación (<600 caracteres/página).

3. **Caché y Honestidad de Embeddings:**
   - [embedding_service.py](file:///c:/Users/52477/Desktop/hackaton/appNuevamente/backend/app/services/embedding_service.py): Implementada caché de vectores en memoria por Hash SHA-256 (`hashlib.sha256(text).hexdigest()`). Si se activa fallback a pseudo-embeddings por falta de conexión/clave, expone explícitamente `recuperacion_degradada: true`, `modo_recuperacion: 'lexico'`, `proveedor_embeddings: "sha256"`.

4. **Frontend Angular:**
   - [workspace.component.ts](file:///c:/Users/52477/Desktop/hackaton/appNuevamente/frontend/src/app/features/workspace/workspace.component.ts): Añadido registro en consola de desarrollo (`[NUEVAMENTE DEV] Payload de Generación enviado`) con los parámetros exactos enviando `nivel_cantidad` y `cantidad_objetivo`. Verificada la limpieza del resultado anterior al pulsar "Generar".

---

## 💻 Comando para Repetir el Diagnóstico

Para ejecutar nuevamente este diagnóstico profundo en cualquier momento:

```bash
backend/venv/Scripts/python.exe backend/scripts/diagnose_adaptation.py
```
