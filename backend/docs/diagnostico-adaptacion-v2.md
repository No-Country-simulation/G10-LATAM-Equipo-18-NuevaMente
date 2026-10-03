# Reporte de Diagnóstico y Validación de Adaptación Educativa V2

**Archivo:** `msJava.pdf` | **Páginas:** 1 | **Caracteres Total:** 21614 | **Fecha:** 2026-10-02 18:07:31

## 📊 Tabla Comparativa por Combinación

| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A** | Principiante | Flashcards | `cache` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 10/10 | `0.957` | `322aad75f4...` | 24.13s |
| **B** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 80/40 | `0.934` | `bce16b6339...` | 49.26s |
| **C** | Líder Técnico | Tutorial | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.901` | `f68d00a90d...` | 20.06s |
| **D** | Ejecutivo | Resumen Ejecutivo | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 5/5 | `0.894` | `69eb61488b...` | 19.94s |
| **E** | Desarrollador | Flashcards | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 25/25 | `0.947` | `c66b3180f9...` | 49.84s |
| **F** | Líder Técnico | Quiz | `llm` | gemini (gemini-flash-latest) | `False` | gemini | `semantico` | 15/15 | `0.898` | `afcc2c55f8...` | 46.39s |

## 🔄 Verificación de Caché
- **Origen devuelto:** `cache`
- **Prompt Hash coincidente:** `True`
- **Latencia en caché:** `0.0013s`

## 🔍 Análisis de Comparación de Contenido Real
- **Similitud Media entre Salidas:** `2.93%`
- **Similitud Máxima entre Salidas:** `6.42%`

### Primer Ítem Completo por Combinación:

#### Combinación (A): Principiante · Flashcards · Salud · Didáctico · Breve
```json
{
  "frente": "¿Cuál es el primer concepto mencionado en la lista del fragmento?",
  "dorso": "El primer concepto mencionado es 'Monitoreo'.",
  "pista_didactica": "Comienza con la letra M y se refiere a la observación o supervisión.",
  "pregunta": "¿Qué elemento encabeza la enumeración en el texto?",
  "opciones": [
    "Monitoreo",
    "Docker",
    "Kubernetes",
    "CI/CD"
  ],
  "respuesta_correcta": "Monitoreo",
  "justificacion": "El texto inicia explícitamente con la palabra 'Monitoreo'.",
  "paso": 1,
  "titulo": "Identificación de Monitoreo",
  "instruccion": "Reconoce a Monitoreo como el punto de partida en la lista provista.",
  "ejemplo": "Lectura directa: 'Monitoreo, Docker...'",
  "punto_clave": "Monitoreo es el primer término citado.",
  "impacto_negocio": "Permite registrar y revisar los componentes clave descritos.",
  "escena": 1,
  "duracion_seg": 30,
  "narracion": "Iniciamos revisando el primer concepto listado: Monitoreo.",
  "apoyo_visual": "Texto resaltando la palabra 'Monitoreo'.",
  "fuentes": [
    {
      "chunk_id": "parent_5",
      "extracto": "Monitoreo, Docker, Kubernetes y CI/CD",
      "pagina": 1
    }
  ]
}
```

#### Combinación (B): Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo
```json
{
  "frente": "¿Qué componente de observabilidad técnica se menciona de forma explícita en el fragmento parent_5?",
  "dorso": "El componente mencionado es 'Monitoreo'.",
  "pista_didactica": "Es el primer elemento de la lista técnica provista.",
  "pregunta": "¿Cuál de los siguientes elementos está listado como parte de la infraestructura técnica en el texto?",
  "opciones": [
    "Monitoreo",
    "Event Sourcing",
    "BBDD Relacional",
    "API Gateway"
  ],
  "respuesta_correcta": "Monitoreo",
  "justificacion": "El fragmento parent_5 lista textualmente 'Monitoreo' como parte de sus elementos.",
  "paso": 1,
  "titulo": "Identificación de Monitoreo",
  "instruccion": "Revisar los componentes de supervisión técnica provistos en la fuente.",
  "ejemplo": "Elemento: Monitoreo",
  "punto_clave": "El monitoreo forma parte directa de la lista de componentes técnicos.",
  "impacto_negocio": "Permite registrar el estado y visibilidad de los sistemas.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "Dentro de la lista de componentes se incluye el Monitoreo.",
  "apoyo_visual": "Texto destacando 'Monitoreo'.",
  "fuentes": [
    {
      "chunk_id": "parent_5",
      "extracto": "Monitoreo, Docker, Kubernetes y CI/CD",
      "pagina": 1
    }
  ]
}
```

#### Combinación (C): Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio
```json
{
  "frente": "¿Cuál es el primer componente operativo contemplado en el fragmento para la gestión técnica?",
  "dorso": "El primer componente explícitamente listado es el Monitoreo.",
  "pista_didactica": "Enfóquese en la primera palabra del fragmento sobre la infraestructura técnica.",
  "pregunta": "¿Qué aspecto inicia la lista de capacidades técnicas citadas en el fragmento parent_5?",
  "opciones": [
    "Monitoreo",
    "Docker",
    "Kubernetes",
    "CI/CD"
  ],
  "respuesta_correcta": "Monitoreo",
  "justificacion": "El fragmento documenta de forma secuencial los términos: Monitoreo, Docker, Kubernetes y CI/CD.",
  "paso": 1,
  "titulo": "Identificación de Monitoreo",
  "instruccion": "Establecer la capacidad de Monitoreo como primer elemento clave del ecosistema técnico según las fuentes.",
  "ejemplo": "Supervisión orientada a 'Monitoreo'",
  "punto_clave": "Monitoreo como pilar inicial documentado.",
  "impacto_negocio": "Visibilidad técnica inmediata de acuerdo a las directrices de la arquitectura.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "Iniciamos la revisión de la arquitectura técnica priorizando el componente de Monitoreo definido en la base de conocimiento.",
  "apoyo_visual": "Texto destacado en pantalla que señala 'Monitoreo' como primer bloque del esquema.",
  "fuentes": [
    {
      "chunk_id": "parent_5",
      "extracto": "Monitoreo, Docker, Kubernetes y CI/CD",
      "pagina": 2
    }
  ]
}
```

#### Combinación (D): Ejecutivo · Resumen · General · Conciso · Estándar
```json
{
  "frente": "¿Qué valor numérico o dato inicial se registra en el fragmento provisto sobre el tema?",
  "dorso": "El único dato reportado en la documentación disponible es el valor '1'. No se incluye información técnica o conceptual adicional en el texto fuente.",
  "pista_didactica": "Revise el único carácter numérico provisto en el fragmento.",
  "pregunta": "¿Cuál es el contenido registrado en la fuente para este apartado?",
  "opciones": [
    "1",
    "Microservicios monolíticos",
    "Alta disponibilidad",
    "Ninguno"
  ],
  "respuesta_correcta": "1",
  "justificacion": "El fragmento parent_0 contiene exclusivamente el registro '1'.",
  "paso": 1,
  "titulo": "Identificación del dato base en la documentación",
  "instruccion": "Verificar el valor inicial registrado en la documentación corporativa.",
  "ejemplo": "Dato asentado: 1.",
  "punto_clave": "El documento únicamente asienta la cifra 1.",
  "impacto_negocio": "Garantiza la toma de decisiones basada exclusivamente en registros verificados sin suposiciones.",
  "escena": 1,
  "duracion_seg": 60,
  "narracion": "La documentación analizada asienta como único dato disponible la unidad 1.",
  "apoyo_visual": "Texto en pantalla mostrando la cifra '1' validada en el documento fuente.",
  "fuentes": [
    {
      "chunk_id": "parent_0",
      "extracto": "1",
      "pagina": 1
    }
  ]
}
```

## 🏁 Dictamen Final

### STATUS: **APROBADO** (0 problemas detectados)
Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.