# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 1 | **Caracteres Total:** 7509 | **Fecha:** 2026-10-13 11:33:14

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 10/10 | `0.813` | `3eccad59db...` | 193.55s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 70/70 | `0.819` | `145a550897...` | 968.42s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 12/12 | `0.802` | `ddeb48dfd8...` | 136.39s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 6/6 | `0.818` | `1e6cc37716...` | 236.79s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 25/25 | `0.811` | `b51b72f6b2...` | 426.0s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-lite-latest) | `False` | gemini | `semantico` | 15/15 | `0.813` | `88b90a7fd1...` | 64.04s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0205s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `3.58%`
- **Similitud Máxima entre Salidas:** `7.58%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿Dónde se encuentra la clave principal para gestionar los módulos al construir una aplicación que actúa como un monolito?",
  "dorso": "La clave la tenemos a nivel de la gestión de módulos.",
  "pista_didactica": "Piensa en el nivel de organización donde se administran los componentes o partes de la aplicación.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.781
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Cuál es la clave arquitectónica principal mencionada para la construcción del monolito base en Spring Boot?",
  "dorso": "La clave se encuentra a nivel de la gestión de módulos dentro de la aplicación.",
  "pista_didactica": "Piensa en cómo se organizan los componentes lógicamente dentro de la misma aplicación.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.797
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "paso": 1,
  "titulo": "Fundamento de la gestión de módulos en monolitos",
  "instruccion": "Comprender que la clave estructural en el desarrollo de este tipo de arquitecturas se centra estrictamente en la gestión de módulos dentro de una aplicación unificada.",
  "ejemplo": "Aplicar el principio de gestión de módulos para organizar lógicamente el código base.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos",
      "pagina": null,
      "similitud_score": 0.832
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "punto_clave": "Gestión de módulos para monolitos",
  "impacto_negocio": "Permite estructurar una aplicación bajo un enfoque centralizado y simplificado en Spring Boot.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "La clave la tenemos a nivel de la gestión de módulos , vamos a construir una aplicación de Spring Boot que actue como si fuera un monolito .",
      "pagina": null,
      "similitud_score": 0.779
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.