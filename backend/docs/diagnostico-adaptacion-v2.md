# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 64 | **Caracteres Total:** 21488 | **Fecha:** 2026-10-02 12:37:03

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 10/10 | `0.923` | `b22b890099...` | 0.47s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 80/40 | `0.943` | `3395dc5854...` | 0.71s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.896` | `2b70e2be69...` | 0.15s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/5 | `0.905` | `aa4c90be94...` | 0.12s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/25 | `0.897` | `90f2badcf4...` | 0.41s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.929` | `41d07455f1...` | 0.24s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0001s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `2.70%`
- **Similitud Máxima entre Salidas:** `6.70%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿En qué consiste el principio de 'Generado proporciona bases' en Estructura del Proyecto Generado?",
  "dorso": "Para un perfil de nivel principiante (Generado proporciona bases), Estructura del Proyecto Generado proporciona las bases operativas de msJava. Garantiza el cumplimiento regulatorio (HIPAA/HL7) y la privacidad de datos clínicos en el sector de la salud.",
  "pista_didactica": "Pista: Enfócate en el impacto de Generado proporciona bases sobre la operatividad del sistema.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "1",
      "pagina": 2,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Cómo se implementa y configura 'aplicaciones stand-alone Tomcat/Jetty/Undertow' en el módulo de Estructura del Proyecto Generado?",
  "dorso": "Desde la perspectiva de desarrollo (tecnico - aplicaciones stand-alone Tomcat/Jetty/Undertow), Tomcat/Jetty/Undertow incluido - aplicaciones stand-alone Asegura la integridad transaccional (PCI-DSS), cero latencia y auditoría estricta en servicios financieros.",
  "pista_didactica": "Pista: Enfócate en el impacto de aplicaciones stand-alone Tomcat/Jetty/Undertow sobre la operatividad del sistema.",
  "fuentes": [
    {
      "chunk_id": "parent_11",
      "extracto": "Tomcat/Jetty/Undertow incluido - aplicaciones stand-alone",
      "pagina": 2,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "paso": 1,
  "titulo": "Módulo 1: Integración de Conguración server.port datasource",
  "instruccion": "Configura y valida Conguración server.port datasource según la especificidad técnica: Conguración: server.port, datasource, logging levels",
  "ejemplo": "// Aplicar Conguración server.port datasource en ¿Qué es Spring Boot?\n// Entorno: E-commerce (Líder Técnico)\nval status = process_con_guraci_n_server_()",
  "advertencia": "Asegúrate de validar la compatibilidad de Conguración server.port datasource antes de desplegar en producción.",
  "fuentes": [
    {
      "chunk_id": "parent_20",
      "extracto": "Conguración: server.port, datasource, logging levels",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "punto_clave": "Impacto Ejecutivo y ROI (3): Convenciones conguración desarrollo",
  "impacto_negocio": "Desde una visión gerencial y estratégica en general (Convenciones conguración desarrollo), Convenciones sobre conguración para desarrollo rápido Aporta eficiencia operativa, mantenibilidad y excelencia en el ecosistema de General.",
  "fuentes": [
    {
      "chunk_id": "parent_9",
      "extracto": "Convenciones sobre conguración para desarrollo rápido",
      "pagina": 2,
      "similitud_score": 0.95
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.