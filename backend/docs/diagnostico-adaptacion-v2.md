# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 1 | **Caracteres Total:** 21614 | **Fecha:** 2026-10-02 19:08:18

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 10/10 | `0.957` | `322aad75f4...` | 18.79s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 80/40 | `0.934` | `bce16b6339...` | 51.26s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.901` | `f68d00a90d...` | 21.04s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/5 | `0.894` | `69eb61488b...` | 16.96s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/25 | `0.947` | `c66b3180f9...` | 32.49s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.898` | `afcc2c55f8...` | 19.47s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0001s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `2.78%`
- **Similitud Máxima entre Salidas:** `4.49%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿Cuál es la condición principal del proyecto?",
  "dorso": "El proyecto se encuentra listo para importar y ejecutar inmediatamente.",
  "pista_didactica": "Piensa en un recurso preparado que no requiere pasos previos antes de usarlo.",
  "pregunta": "¿En qué estado se encuentra el proyecto según el texto?",
  "opciones": [
    "Listo para importar y ejecutar inmediatamente",
    "En proceso de configuración pendiente",
    "Requiere instalación previa de librerías externas",
    "Listo únicamente para revisión de código"
  ],
  "respuesta_correcta": "Listo para importar y ejecutar inmediatamente",
  "justificacion": "El texto indica explícitamente que es un proyecto listo para importar y ejecutar inmediatamente.",
  "paso": 1,
  "titulo": "Estado inicial del proyecto",
  "instruccion": "Identifica que el recurso provisto ya se encuentra completamente preparado.",
  "ejemplo": "Disponer de un proyecto listo para importar y ejecutar inmediatamente.",
  "punto_clave": "El proyecto está listo.",
  "impacto_negocio": "Permite iniciar actividades sin tiempos muertos de preparación.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "El punto de partida es un proyecto que ya está listo para importar y ejecutar de forma inmediata.",
  "apoyo_visual": "Texto en pantalla destacando: 'Listo para importar y ejecutar inmediatamente'.",
  "fuentes": [
    {
      "chunk_id": "parent_18",
      "extracto": "Proyecto listo para importar y ejecutar inmediatamente",
      "pagina": 3
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Qué componente de comunicación y diseño de endpoints se aborda en el contenido técnico?",
  "dorso": "Las APIs REST, contemplando su diseño y uso en la arquitectura.",
  "pista_didactica": "Piensa en el estilo arquitectónico estándar para endpoints web.",
  "pregunta": "¿Cuál es la tecnología de interfaces de comunicación mencionada en el material?",
  "opciones": [
    "APIs REST",
    "SOAP RPC",
    "gRPC puro",
    "GraphQL sin esquemas"
  ],
  "respuesta_correcta": "APIs REST",
  "justificacion": "El texto explicita 'APIs REST' como parte fundamental del temario.",
  "paso": 1,
  "titulo": "Implementación de APIs REST",
  "instruccion": "Diseñar e implementar endpoints siguiendo la especificación de APIs REST.",
  "ejemplo": "Exposición de endpoints mediante APIs REST.",
  "punto_clave": "APIs REST como base de la interfaz.",
  "impacto_negocio": "Estandariza la integración técnica de servicios.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "Iniciamos revisando las APIs REST y sus componentes clave.",
  "apoyo_visual": "Diagrama de arquitectura mostrando endpoints de APIs REST.",
  "fuentes": [
    {
      "chunk_id": "parent_2",
      "extracto": "APIs REST, documentación y best practices",
      "pagina": 1
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "frente": "¿Cuál es el componente de comunicación base indicado para el servicio?",
  "dorso": "Las APIs REST.",
  "pista_didactica": "Revise el primer elemento mencionado en el contenido.",
  "pregunta": "¿Qué elemento se señala para la capa de interfaces del servicio?",
  "opciones": [
    "APIs REST",
    "SOAP RPC",
    "GraphQL puro",
    "gRPC binario"
  ],
  "respuesta_correcta": "APIs REST",
  "justificacion": "El texto explicita 'APIs REST' dentro de los elementos principales.",
  "paso": 1,
  "titulo": "Definición de APIs REST",
  "instruccion": "Establecer la interfaz de comunicación del servicio enfocándose en APIs REST.",
  "ejemplo": "Definir endpoints conformes a la especificación de APIs REST.",
  "punto_clave": "APIs REST como base de la interfaz.",
  "impacto_negocio": "Estandariza los contratos de integración para las soluciones técnicas.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "Iniciamos revisando el componente de APIs REST según la estructura técnica provista.",
  "apoyo_visual": "Texto en pantalla destacando el bloque 'APIs REST'.",
  "fuentes": [
    {
      "chunk_id": "parent_2",
      "extracto": "APIs REST, documentación y best practices\n\n3\n\n4\n\nPersistencia y Testing Spring Data, validación y testing avanzado",
      "pagina": 1
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "frente": "¿Qué aspecto inicial del entorno se menciona en el documento?",
  "dorso": "Se establecen las características del entorno.",
  "pista_didactica": "Enfóquese en el primer término del encabezado.",
  "pregunta": "¿Cuál es uno de los temas documentados respecto al entorno?",
  "opciones": [
    "Características",
    "Costos de licenciamiento",
    "Auditoría externa",
    "Migración de nube"
  ],
  "respuesta_correcta": "Características",
  "justificacion": "El documento señala explícitamente 'Características y conguración del entorno'.",
  "paso": 1,
  "titulo": "Identificación de características del entorno",
  "instruccion": "Revisar las características registradas para el entorno.",
  "ejemplo": "Inspección del rubro de características del entorno.",
  "punto_clave": "Características del entorno.",
  "impacto_negocio": "Permite reconocer la base estructural del entorno informada.",
  "escena": 1,
  "duracion_seg": 30,
  "narracion": "El documento define las características asociadas al entorno corporativo.",
  "apoyo_visual": "Texto en pantalla mostrando 'Características del entorno'.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno\n\n2",
      "pagina": 1
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.