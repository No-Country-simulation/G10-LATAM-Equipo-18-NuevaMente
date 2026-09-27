"""
config.py

Purpose:
    Application settings and global constants for NuevaMente backend.
    Loads environment variables and defines domain profiles, formats,
    model identifiers, embedding providers, and ingestion limits.

Input:
    Environment variables read from backend/.env (see .env.example):
    GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, JINA_API_KEY,
    and optional OCI credentials.

Output:
    `settings` singleton with typed configuration attributes.
"""

import os
from typing import Dict, List
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Module-level constants used inside the class to avoid cross-field references.
_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
_JINA_EMBED_MODEL = "jina-embeddings-v3"
# 768-dim local model, matched to EMBEDDING_DIMENSIONS below so FAISS and
# pgvector indexes stay interchangeable regardless of which provider produced them.
_LOCAL_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


class Settings(BaseModel):
    PROJECT_NAME: str = "NuevaMente - API de Adaptación Educativa"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ── LLM Configuration ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "MOCK_GEMINI_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    DEFAULT_GEMINI_MODEL_PRO: str = "gemini-2.5-pro"
    DEFAULT_GEMINI_MODEL_FLASH: str = "gemini-3.5-flash" # "gemini-3.x-flash-lite"
    DEFAULT_GROQ_MODEL: str = "llama-3.1-8b-instant" # "qwen-2.5-72b"
    DEFAULT_OPENROUTER_MODEL: str = "mistral-small-latest" # "pixtral-12b"

    # ── Embedding Configuration ───────────────────────────────────────────────
    # EMBEDDING_METHOD: "api" uses a remote provider; "local" uses sentence-transformers.
    EMBEDDING_METHOD: str = os.getenv("EMBEDDING_METHOD", "api")

    # Active API provider when EMBEDDING_METHOD="api": "gemini" or "jina".
    EMBEDDING_API_PROVIDER: str = os.getenv("EMBEDDING_API_PROVIDER", "gemini")

    JINA_API_KEY: str = os.getenv("JINA_API_KEY", "")

    # Model identifier per provider — used to tag collections in the vector store.
    EMBEDDING_API_MODELS: Dict[str, str] = {
        "gemini": _GEMINI_EMBED_MODEL,
        "jina": _JINA_EMBED_MODEL,
    }

    # Default embedding model name (resolved at runtime by EmbeddingService).
    DEFAULT_EMBEDDING_MODEL: str = _GEMINI_EMBED_MODEL
    LOCAL_EMBEDDING_MODEL: str = _LOCAL_EMBED_MODEL

    # Fixed output dimension enforced across every provider (Gemini, Jina, local),
    # so FAISS and a future pgvector column always hold compatible vectors.
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

    # Number of texts sent per API call in embed_batch(). Kept conservative
    # since the exact provider ceiling isn't confirmed; EmbeddingService
    # halves this automatically on a batch-size related failure.
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "50"))

    # ── Vector Store Configuration ────────────────────────────────────────────
    # VECTOR_STORE_METHOD: "faiss" (default, local per-document index) or "pgvector".
    VECTOR_STORE_METHOD: str = os.getenv("VECTOR_STORE_METHOD", "faiss")
    VECTOR_STORE_DIR: str = os.getenv("VECTOR_STORE_DIR", "vector_store")

    # ── Document Storage Configuration (original uploaded files) ──────────────
    # STORAGE_METHOD: "supabase" (Supabase Storage) or "oci" (pending an OCI
    # adapter behind the same BaseDocumentStorage interface).
    STORAGE_METHOD: str = os.getenv("STORAGE_METHOD", "supabase")
 
    # Supabase project credentials. SUPABASE_KEY must be the service_role key
    # (backend-only, bypasses Row Level Security) — never the anon/public key,
    # and never committed; it belongs in .env only.
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET_DOCUMENTS: str = os.getenv("SUPABASE_BUCKET_DOCUMENTS", "document-source")

    # ── OCI Object Storage Configuration (Always Free) ───────────────────────
    OCI_CONFIG_FILE: str = os.path.expanduser("~/.oci/config")
    OCI_BUCKET_DOCS: str = "nuevamente-documentos-fuente"
    OCI_BUCKET_ARTIFACTS: str = "nuevamente-contenidos-educativos"

    # ── RAG Configuration ─────────────────────────────────────────────────────
    MAX_TOP_K_CHUNKS: int = 5
    RRF_DENSE_WEIGHT: float = 0.6
    RRF_SPARSE_WEIGHT: float = 0.4

    # ── Ingestion Configuration ───────────────────────────────────────────────
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".md", ".markdown", ".txt"]
    MAX_FILE_SIZE_MB: int = 20
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    CHILD_CHUNK_SIZE: int = 150

    # Extracts short key-concept tags per chunk at ingestion time (KeyBERT).
    # Disabled by default: it loads its own local model and adds ingestion
    # latency, so it's opt-in until measured on real documents.
    USE_KEYBERT_CONCEPTS: bool = os.getenv("USE_KEYBERT_CONCEPTS", "false").lower() == "true"

    # ── Domain Profiles ───────────────────────────────────────────────────────
    PROFILE_BEGINNER: str = "beginner"
    PROFILE_JUNIOR_DEV: str = "junior_developer"
    PROFILE_TECH_LEAD: str = "tech_lead"
    PROFILE_EXECUTIVE: str = "executive"

    @property
    def PROFILES(self) -> List[str]:
        return [
            self.PROFILE_BEGINNER,
            self.PROFILE_JUNIOR_DEV,
            self.PROFILE_TECH_LEAD,
            self.PROFILE_EXECUTIVE,
        ]

    # ── Domain Output Formats ─────────────────────────────────────────────────
    FORMAT_TUTORIAL: str = "tutorial"
    FORMAT_FLASHCARDS: str = "flashcards"
    FORMAT_QUIZ: str = "quiz"
    FORMAT_SUMMARY: str = "executive_summary"
    FORMAT_CLASS_SCRIPT: str = "class_script"

    @property
    def OUTPUT_FORMATS(self) -> List[str]:
        return [
            self.FORMAT_TUTORIAL,
            self.FORMAT_FLASHCARDS,
            self.FORMAT_QUIZ,
            self.FORMAT_SUMMARY,
            self.FORMAT_CLASS_SCRIPT,
        ]

    # ── Domain Niches ─────────────────────────────────────────────────────────
    NICHE_GENERAL: str = "general"
    NICHE_FINTECH: str = "fintech"
    NICHE_HEALTH: str = "health"
    NICHE_ECOMMERCE: str = "ecommerce"

    @property
    def NICHES(self) -> List[str]:
        return [
            self.NICHE_GENERAL,
            self.NICHE_FINTECH,
            self.NICHE_HEALTH,
            self.NICHE_ECOMMERCE,
        ]


settings = Settings()