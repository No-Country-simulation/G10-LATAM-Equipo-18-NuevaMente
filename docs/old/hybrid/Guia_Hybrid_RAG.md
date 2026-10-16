# Guía de Hybrid RAG — NuevaMente

## ¿Qué es el RAG Híbrido?
El RAG Híbrido combina dos estrategias de búsqueda de información para lograr resultados precisos:
1. **Búsqueda Densa (Embeddings):** Comprende el "significado" (semántica) de la pregunta, ideal para sinónimos o conceptos abstractos.
2. **Búsqueda Léxica (BM25):** Busca palabras exactas, ideal para nombres propios, acrónimos, o identificadores técnicos.

## Algoritmo RRF (Reciprocal Rank Fusion)
En lugar de sumar puntuaciones en bruto que tienen diferentes escalas, el RRF suma los *inversos* de los rangos de ambos métodos. Esto crea un equilibrio perfecto sin necesidad de adivinar "pesos" (weights) fijos.

## Flujo de Búsqueda y Reranking (Clean Architecture)

1. **Retrieval Híbrido:** Se obtienen los mejores N resultados (child chunks) combinando Embedding + BM25.
2. **Fallback Dinámico de Embeddings:** El motor de embeddings intentará primero Gemini, luego Jina (al 50% de texto), y luego el modelo local (al 25%).
3. **Mapeo a Padres (Parent-Document Retrieval):** Los "child chunks" se mapean a su contexto mayor (documento padre) para no perder información crítica.
4. **Cohere Reranker:** Se pasa la lista de documentos padres al modelo `Cohere Reranker` (ej. `rerank-multilingual-v3.0`), el cual analiza profundamente la relación entre la pregunta del usuario y cada documento, entregando un reordenamiento final óptimo.

## Evaluación de Clean Code
El diseño de `HybridRAGService` inyecta dependencias correctamente (p. ej., inyecta `EmbeddingService` por el constructor), lo que respeta la Inyección de Dependencias. El modelo de Cohere también está aislado lógicamente. Sin embargo, para mayor limpieza, la lógica RRF y BM25 podría extraerse a módulos utilitarios (p. ej. `SearchUtils`) si la clase llega a volverse demasiado larga, manteniendo así el Principio de Responsabilidad Única.

## ¿Por qué esto hace que NuevaMente sea un mejor proyecto?
En el contexto del Hackathon, implementar un Hybrid RAG con Reranker y Fallback en Cascada demuestra un nivel de ingeniería de software avanzado:
1. **Precisión Quirúrgica:** Combinar búsqueda semántica (conceptos) con búsqueda léxica (palabras exactas) resuelve el problema clásico donde la IA no encuentra un término técnico específico.
2. **Gestión Inteligente de Recursos:** El sistema sabe "ahorrar" truncando el texto proporcionalmente (50% o 25%) cuando se usan las APIs de respaldo (Jina o Local). 
3. **Uso de Estado del Arte:** Utilizar Cohere como Cross-Encoder (Reranker) multilingüe garantiza que los resultados en español sean de la máxima relevancia antes de inyectarlos al prompt final de Gemini.

## ¿Cómo ejecutar el proyecto usando `uv`?
Para probar este módulo, utilizamos `uv`, el gestor ultrarrápido de dependencias de Python.

```bash
# 1. Posiciónate en la carpeta backend
cd backend

# 2. Instala/sincroniza las dependencias (rank_bm25, cohere, google-genai, etc.)
uv sync

# 3. Activa el entorno (Linux/Mac)
source .venv/bin/activate

# 4. Inicia la API
uv run uvicorn main:app --reload
```
*Nota:* Asegúrate de tener configuradas tus variables de entorno en el archivo `.env` (GEMINI_API_KEY, JINA_API_KEY, COHERE_API_KEY).

## Resultados Esperados y Ecosistema de Modelos de IA
Al igual que en el módulo de Ingestión (donde usamos **KeyBERT** para extraer conceptos clave gratuitamente sin gastar tokens del LLM), todo este ecosistema de RAG Híbrido y Grafos está diseñado con una premisa: **"Usar la herramienta adecuada para el trabajo adecuado"**. 

Este es el resultado arquitectónico final que logramos y el rol de cada modelo:

1. **Google Gemini (Generador y Cerebro Principal):**
   - *Rol:* Orquestador. Entiende la solicitud, analiza el "Knowledge Graph" y redacta el material educativo final. 
   - *¿Por qué?* Es un LLM generativo súper poderoso. Su fuerte es razonar y escribir.
2. **Jina AI (El Especialista en Vectores - Plan B):**
   - *Rol:* Motor de Embeddings y Fallback semántico.
   - *¿Por qué?* Jina está altamente optimizado para calcular matemáticas de texto (vectores). No genera texto, pero es el mejor entendiendo "qué se parece a qué". Lo usamos como segunda capa si Gemini falla.
3. **Cohere (El Optimizador Final - Reranker):**
   - *Rol:* Ordenar los resultados antes de entregarlos.
   - *¿Por qué?* Su modelo `rerank-multilingual-v3.0` (Cross-Encoder) lee las preguntas y las respuestas al mismo tiempo para calificar su relevancia exacta. Mejora drásticamente la puntería de lo que va a leer Gemini.
4. **Modelos Locales (Sentence-Transformers / KeyBERT):**
   - *Rol:* El escudo final y optimización de ingesta.
   - *¿Por qué?* Si no hay internet o se acaban las APIs gratuitas, tu computadora levanta estos pequeños modelos localmente. Así tu aplicación web *nunca* se cae. Y en la ingesta, extraen metadatos gratis y rápido.

Con este ecosistema logramos una **arquitectura Enterprise**, donde ningún modelo hace el trabajo del otro, optimizando velocidad y reduciendo costos a $0 en el nivel Always Free.
