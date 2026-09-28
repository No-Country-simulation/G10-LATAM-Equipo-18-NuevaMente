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

    # Provider rate limits, token thresholds, and batch configurations.
    GEMINI_MAX_RPM: int = int(os.getenv("GEMINI_MAX_RPM", "100"))
    GEMINI_MAX_TPM: int = int(os.getenv("GEMINI_MAX_TPM", "30000"))
    GEMINI_MAX_RPD: int = int(os.getenv("GEMINI_MAX_RPD", "1000"))
    GEMINI_SAFE_TPM: int = int(os.getenv("GEMINI_SAFE_TPM", "25000"))
    # Conservative batch size: 20 texts × ~300 chars avg ≈ 1,500 tokens/request.
    GEMINI_BATCH_SIZE: int = int(os.getenv("GEMINI_BATCH_SIZE", "20"))

    JINA_MAX_RPM: int = int(os.getenv("JINA_MAX_RPM", "100"))
    JINA_MAX_TPM: int = int(os.getenv("JINA_MAX_TPM", "100000"))
    JINA_SAFE_TPM: int = int(os.getenv("JINA_SAFE_TPM", "90000"))
    JINA_BATCH_SIZE: int = int(os.getenv("JINA_BATCH_SIZE", "50"))

    LOCAL_BATCH_SIZE: int = int(os.getenv("LOCAL_BATCH_SIZE", "32"))

    # Priority order for embedding provider fallback.
    EMBEDDING_FALLBACK_CHAIN: List[str] = ["gemini", "jina", "local"]

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
    # Parent chunks: large context windows sent to the LLM for generation.
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    # Child chunks: smaller dense units embedded and indexed in FAISS.
    # Must be strictly less than CHUNK_SIZE and greater than CHILD_CHUNK_OVERLAP.
    CHILD_CHUNK_SIZE: int = int(os.getenv("CHILD_CHUNK_SIZE", "400"))
    CHILD_CHUNK_OVERLAP: int = int(os.getenv("CHILD_CHUNK_OVERLAP", "40"))

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