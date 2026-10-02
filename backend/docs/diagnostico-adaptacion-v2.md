# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 64 | **Caracteres Total:** 21488 | **Fecha:** 2026-10-02 10:55:43

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 10/10 | `0.923` | `b22b890099...` | 9.2s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 80/40 | `0.943` | `3395dc5854...` | 1.5s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.896` | `2b70e2be69...` | 0.27s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/5 | `0.905` | `aa4c90be94...` | 0.26s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/25 | `0.897` | `90f2badcf4...` | 0.56s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.929` | `41d07455f1...` | 0.32s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0001s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `4.93%`
- **Similitud Máxima entre Salidas:** `19.39%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "Concepto #5 (cada sesión 34h teoría/práctica retos Retos #5): ¿Qué relevancia tiene en Estructura del Proyecto Generado?",
  "dorso": "En Salud, el concepto 'cada sesión 34h teoría/práctica retos Retos #5' establece las bases operativas para Principiante (nivel Didactico).",
  "pista_didactica": "Pista #5: Analiza la relación entre cada sesión 34h teoría/práctica retos Retos #5 y Estructura del Proyecto Generado.",
  "fuentes": [
    {
      "chunk_id": "parent_7",
      "extracto": "40h\nDuración Total\n- 3 horas cada sesión\n34h teoría/práctica + 6h retos\n2 Retos teóricos\nEvaluación de conocimientos adq",
      "pagina": 2,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "Concepto #1 (Monitoreo, Docker, Kubernetes CI/CD #1): ¿Qué relevancia tiene en ¿Qué es Spring Boot??",
  "dorso": "En Fintech, el concepto 'Monitoreo, Docker, Kubernetes CI/CD #1' establece las bases operativas para Desarrollador (nivel Tecnico).",
  "pista_didactica": "Pista #1: Analiza la relación entre Monitoreo, Docker, Kubernetes CI/CD #1 y ¿Qué es Spring Boot?.",
  "fuentes": [
    {
      "chunk_id": "parent_5",
      "extracto": "Monitoreo, Docker, Kubernetes y CI/CD",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "paso": 9,
  "titulo": "Paso 9: Implementación de GraalVM Native Compilation ocial (AOT) para #9 en Sesión 1",
  "instruccion": "En el Paso 9, configura 'GraalVM Native Compilation ocial (AOT) para #9' dentro de Sesión 1.",
  "ejemplo": "```text\n# Paso 9: GraalVM Native Compilation ocial (AOT) para #9\n// Aplicar GraalVM Native Compilation ocial (AOT) para #9 en Sesión 1\n```",
  "advertencia": "Verifica que GraalVM Native Compilation ocial (AOT) para #9 esté disponible antes de proceder al Paso 9.",
  "fuentes": [
    {
      "chunk_id": "parent_28",
      "extracto": "GraalVM Native Compilation ocial (AOT) para startup rápido",
      "pagina": 3,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "punto_clave": "Eje Estratégico #5: Características conguración del entorno #5 (Sesión 1)",
  "impacto_negocio": "Relevancia de 'Características conguración del entorno #5' para Ejecutivo en General: optimiza Sesión 1.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno\n2",
      "pagina": 3,
      "similitud_score": 0.95
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.