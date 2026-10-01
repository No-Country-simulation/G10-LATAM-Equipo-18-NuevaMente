# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 64 | **Caracteres Total:** 21488 | **Fecha:** 2026-10-01 17:02:41

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/3 | `0.923` | `b22b890099...` | 7.86s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/3 | `0.943` | `3395dc5854...` | 1.13s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/3 | `0.896` | `2b70e2be69...` | 1.0s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/3 | `0.905` | `aa4c90be94...` | 3.86s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/5 | `0.897` | `90f2badcf4...` | 74.22s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/4 | `0.929` | `41d07455f1...` | 58.25s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0001s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `18.93%`
- **Similitud Máxima entre Salidas:** `74.90%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "Tarjeta #1: ¿Qué principio define ¿Qué es Spring Boot? en msJava?",
  "dorso": "En Salud, este concepto establece: Características y conguración del entorno\n2. Diseñado para el nivel Didactico de Principiante.",
  "pista_didactica": "Pista #1: Enfócate en las buenas prácticas operativas.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno\n2",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "Tarjeta #1: ¿Qué principio define ¿Qué es Spring Boot? en msJava?",
  "dorso": "En Fintech, este concepto establece: Características y conguración del entorno\n2. Diseñado para el nivel Tecnico de Desarrollador.",
  "pista_didactica": "Pista #1: Enfócate en las buenas prácticas operativas.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno\n2",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "paso": 1,
  "titulo": "Paso 1: ¿Qué es Spring Boot?",
  "instruccion": "En el Paso 1, comprende ¿Qué es Spring Boot?. 1.",
  "ejemplo": "```text\n# Paso 1: ¿Qué es Spring Boot?\n1\n```",
  "advertencia": "Verifica los prerrequisitos técnicos antes de ejecutar el Paso 1.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "1",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "punto_clave": "¿Qué es Spring Boot?",
  "impacto_negocio": "Relevancia de ¿Qué es Spring Boot? para Ejecutivo en General: 1.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "1",
      "pagina": 1,
      "similitud_score": 0.95
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **FALLÓ (2 problemas detectados)**

- ❌ FALLO (A): Cantidad generada 3 difiere de la esperada 10 para el nivel Breve.
- ❌ FALLO: Similitud excesiva (74.90%) entre las combinaciones A y B (límite < 70%).