# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 1 | **Caracteres Total:** 7509 | **Fecha:** 2026-10-12 19:57:40

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 10/10 | `0.818` | `3eccad59db...` | 180.66s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 70/70 | `0.816` | `145a550897...` | 25.9s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 12/12 | `0.803` | `ddeb48dfd8...` | 4.62s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 6/6 | `0.81` | `1e6cc37716...` | 2.97s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 25/25 | `0.809` | `b51b72f6b2...` | 10.58s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 15/15 | `0.811` | `88b90a7fd1...` | 7.56s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0033s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `2.52%`
- **Similitud Máxima entre Salidas:** `5.60%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿Dónde se encuentra la clave para entender la estructura inicial mencionada en el documento?",
  "dorso": "La clave se encuentra a nivel de la gestión de módulos.",
  "pista_didactica": "Piensa en cómo se organizan las partes o secciones dentro del sistema.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.789
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Cuál es la clave arquitectónica principal mencionada para estructurar la aplicación monolítica?",
  "dorso": "La clave se encuentra a nivel de la gestión de módulos dentro de la aplicación.",
  "pista_didactica": "Piensa en cómo se organizan los componentes lógicos dentro del mismo proyecto antes de hablar de microservicios.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.787
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "paso": 1,
  "titulo": "Fundamentación de la gestión de módulos",
  "instruccion": "Comprenda el nivel en el cual se establece la clave principal para estructurar nuestra aplicación según las directrices técnicas iniciales.",
  "ejemplo": "La clave la tenemos a nivel de la gestión de módulos.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.86
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "punto_clave": "Gestión de módulos para monolitos",
  "impacto_negocio": "Permite estructurar una aplicación bajo un enfoque centralizado y simplificado.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.799
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.