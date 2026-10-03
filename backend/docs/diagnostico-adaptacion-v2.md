# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 1 | **Caracteres Total:** 21614 | **Fecha:** 2026-10-03 08:49:55

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 10/10 | `0.957` | `322aad75f4...` | 21.47s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 80/40 | `0.934` | `bce16b6339...` | 49.89s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.901` | `f68d00a90d...` | 19.72s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/5 | `0.894` | `69eb61488b...` | 16.01s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/25 | `0.947` | `c66b3180f9...` | 32.49s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.898` | `afcc2c55f8...` | 19.95s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0001s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `2.29%`
- **Similitud Máxima entre Salidas:** `4.10%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿Qué aspecto principal relativo al entorno se menciona en el texto?",
  "dorso": "El texto menciona las 'Características y configuración del entorno'.",
  "pista_didactica": "Observa el título inicial presentado en el fragmento.",
  "pregunta": "¿Qué elementos del entorno se enuncian textualmente en el fragmento?",
  "opciones": [
    "Características y configuración del entorno",
    "Instalación y monitoreo de microservicios",
    "Bases de datos y redes",
    "Seguridad y despliegue continuo"
  ],
  "respuesta_correcta": "Características y configuración del entorno",
  "justificacion": "El fragmento documenta explícitamente: 'Características y configuración del entorno'.",
  "paso": 1,
  "titulo": "Identificación del tema del entorno",
  "instruccion": "Reconocer las características y la configuración del entorno según el texto.",
  "ejemplo": "Lectura de: 'Características y configuración del entorno'.",
  "punto_clave": "El texto aborda las características y la configuración del entorno.",
  "impacto_negocio": "Permite identificar el punto de partida indicado en la documentación.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "En el documento se indica el título sobre características y configuración del entorno.",
  "apoyo_visual": "Texto en pantalla mostrando 'Características y configuración del entorno'.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno\n\n2",
      "pagina": 1
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Qué estilo de interfaz se especifica para la comunicación en este bloque formativo?",
  "dorso": "Se especifican APIs REST junto con su documentación y best practices.",
  "pista_didactica": "Piensa en el estilo arquitectónico de comunicación mencionado en la primera línea.",
  "pregunta": "¿Cuál es el componente de comunicación técnica listado en el texto?",
  "opciones": [
    "APIs REST",
    "gRPC",
    "GraphQL",
    "WebSockets"
  ],
  "respuesta_correcta": "APIs REST",
  "justificacion": "El texto explicita textualmente 'APIs REST, documentación y best practices'.",
  "paso": 1,
  "titulo": "Definición de APIs REST",
  "instruccion": "Identificar el uso de APIs REST como interfaz según el programa técnico.",
  "ejemplo": "Implementación de APIs REST siguiendo los requisitos del contenido.",
  "punto_clave": "APIs REST",
  "impacto_negocio": "Estandarización técnica de la interfaz de servicios.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "El temario inicia destacando el trabajo con APIs REST.",
  "apoyo_visual": "Texto resaltando APIs REST.",
  "fuentes": [
    {
      "chunk_id": "parent_2",
      "extracto": "APIs REST, documentación y best practices\n\n3\n\n4\n\nPersistencia y Testing Spring Data, validación y testing avanzado",
      "pagina": 1
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "frente": "¿Cuál es el rol primordial del diseño de APIs REST dentro del módulo técnico?",
  "dorso": "Establecer la interfaz de comunicación estándar mediante APIs REST, asegurando la interoperabilidad del sistema conforme al programa.",
  "pista_didactica": "Piensa en el primer término mencionado en el fragmento para la comunicación de servicios.",
  "pregunta": "¿Qué elemento encabeza la sección de comunicación en el contenido provisto?",
  "opciones": [
    "APIs REST",
    "GraphQL",
    "gRPC",
    "Colas de mensajería"
  ],
  "respuesta_correcta": "APIs REST",
  "justificacion": "El texto explicita textualmente 'APIs REST' como componente inicial de estudio y desarrollo.",
  "paso": 1,
  "titulo": "Definición y Diseño de APIs REST",
  "instruccion": "Diseñar e implementar las interfaces basadas en APIs REST para garantizar la conectividad de los componentes.",
  "ejemplo": "Definición de endpoints para el intercambio de recursos bajo el estándar de APIs REST.",
  "punto_clave": "Las APIs REST constituyen el núcleo de la interfaz técnica expuesta en el temario.",
  "impacto_negocio": "Estandariza los contratos de integración minimizando fricciones técnicas entre servicios.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "Iniciamos revisando el estándar de APIs REST para estructurar los servicios del sistema.",
  "apoyo_visual": "Diagrama de bloques destacando las interfaces basadas en APIs REST.",
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
  "dorso": "Se mencionan las características y la configuración del entorno.",
  "pista_didactica": "Revise el título principal del fragmento.",
  "pregunta": "¿Cuáles son los conceptos clave señalados respecto al entorno?",
  "opciones": [
    "Características y configuración del entorno",
    "Costos y presupuestos",
    "Monitoreo externo de red",
    "Estrategia de ventas"
  ],
  "respuesta_correcta": "Características y configuración del entorno",
  "justificacion": "El texto cita textualmente 'Características y conguración del entorno'.",
  "paso": 1,
  "titulo": "Identificación del Entorno",
  "instruccion": "Reconocer las características y la configuración del entorno según el texto.",
  "ejemplo": "Lectura del encabezado: Características y configuración del entorno.",
  "punto_clave": "Características y configuración del entorno.",
  "impacto_negocio": "Permite alinear la toma de decisiones con el entorno definido.",
  "escena": 1,
  "duracion_seg": 30,
  "narracion": "El documento establece como punto de partida las características y la configuración del entorno.",
  "apoyo_visual": "Texto en pantalla mostrando 'Características y configuración del entorno'.",
  "fuentes": [
    {
      "chunk_id": "parent_1",
      "extracto": "Características y conguración del entorno",
      "pagina": 1
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.