# Guía del Ecosistema Multi-Agente (Clean Architecture)

El sistema NuevaMente ha evolucionado de un modelo monolítico (únicamente Gemini) a un **Ecosistema Multi-Agente Dinámico**. Esto significa que delegamos tareas a diferentes modelos de IA basándonos en sus puntos fuertes, velocidad y costos.

## 🧠 Multi-Agent Router (El Policía de Tráfico)
Archivo: `app/services/multi_agent_router.py`

El **MultiAgentRouter** es el cerebro que decide qué modelo (agente) procesará la tarea actual.
Analiza la petición del usuario (ej. Formato de Salida y Perfil) y busca palabras clave mediante expresiones regulares para asignar el modelo óptimo.

### Perfiles Soportados Actualmente:
1. **GEMINI (Google):** `Investigador Heavy-Lifter`. Tareas pesadas, análisis profundo y tutoriales complejos. (Agente por defecto).
2. **GROQ (Llama-3):** `Generador Rápido`. Tareas de baja latencia como Flashcards, Quizzes y estructuración de datos rápidos.
3. **GROK:** `Conversacional`. Workflows, flujos interactivos de chat y voz.
4. **CEREBRAS:** `Ultra-Low Latency`. Clasificación exprés y validaciones a latencia casi cero.
5. **QWEN_VL:** `Multimodal Visión`. Analizador de imágenes, diagramas y extracción de texto visual.
6. **OPENROUTER:** `File Fetcher`. Ingesta y parseo masivo de documentos.
7. **OLLAMA:** `Respaldo Local`. Alternativa de emergencia offline (Fallback) si falla la conexión a internet o por temas de privacidad estricta.

## 🔌 Capa de Infraestructura (Clean Architecture)
Para no acoplar los servicios a librerías externas, todos los clientes de IA residen en la capa `app/infrastructure/`.
* `gemini_client.py`: Maneja el SDK de Google GenAI v2.x
* `groq_client.py`: Maneja la LPU hiper-rápida de Groq.
* `jina_client.py`: Gestiona los Embeddings mediante la API de Jina AI.
* `cohere_client.py`: Gestiona el Reranking usando el modelo multilingüe de Cohere V2.

Cada cliente incluye un **Modo Mock (Rescate)** que devuelve una respuesta simulada válida (evitando errores de validación en Pydantic) si la API Key falla, falta, o el servicio se satura (ej. Error 503).
