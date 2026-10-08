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
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
ssl.create_default_context = ssl._create_unverified_context
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _orig_send = requests.Session.send
    def _unverified_send(self, request, **kwargs):
        kwargs['verify'] = False
        return _orig_send(self, request, **kwargs)
    requests.Session.send = _unverified_send
except Exception:
    pass

from typing import Dict, List
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Module-level constants used inside the class to avoid cross-field references.
_GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
_JINA_EMBED_MODEL = "jina-embeddings-v3"
_LOCAL_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Settings(BaseModel):
    PROJECT_NAME: str = "NuevaMente - API de Adaptación Educativa"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # ── LLM Configuration ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "MOCK_GEMINI_KEY")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    DEFAULT_OUTPUT_LANGUAGE: str = os.getenv("DEFAULT_OUTPUT_LANGUAGE", "Spanish")

    # LLM model identifiers - defined here, not in .env (which is only for API keys)
    GEMINI_LLM_MODEL: str = "gemini-3.5-flash"
    DEFAULT_GEMINI_MODEL_PRO: str = "gemini-3.5-pro"
    DEFAULT_GEMINI_MODEL_FLASH: str = "gemini-3.5-flash"
    DEFAULT_GROQ_MODEL: str = "openai/gpt-oss-20b"
    DEFAULT_OPENROUTER_MODEL: str = "mistralai/mistral-small-3.2-24b-instruct"

    # ── Embedding Configuration ───────────────────────────────────────────────
    EMBEDDING_METHOD: str = os.getenv("EMBEDDING_METHOD", "api")
    EMBEDDING_API_PROVIDER: str = os.getenv("EMBEDDING_API_PROVIDER", "gemini")

    JINA_API_KEY: str = os.getenv("JINA_API_KEY", "")

    EMBEDDING_API_MODELS: Dict[str, str] = {
        "gemini": _GEMINI_EMBED_MODEL,
        "jina": _JINA_EMBED_MODEL,
    }

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
    # Safe ceilings enforced by the shared rate limiter. Each text in a batch
    # counts as one request, so these are measured in texts, not API calls.
    GEMINI_SAFE_RPM: int = int(os.getenv("GEMINI_SAFE_RPM", "80"))
    GEMINI_SAFE_RPD: int = int(os.getenv("GEMINI_SAFE_RPD", "900"))
    # Maximum total wait (seconds) accepted to index one document with Gemini
    # before routing it to the next provider instead.
    GEMINI_MAX_WAIT_SECONDS: int = int(os.getenv("GEMINI_MAX_WAIT_SECONDS", "600"))
    # Upper bound of texts per Gemini call; the effective size is also capped by GEMINI_SAFE_RPM.
    GEMINI_BATCH_SIZE: int = int(os.getenv("GEMINI_BATCH_SIZE", "20"))

    # Full passes over the provider chain when indexing a document (1 = no retry pass).
    EMBEDDING_CHAIN_ROUNDS: int = int(os.getenv("EMBEDDING_CHAIN_ROUNDS", "2"))
    # Waits allowed on one provider after a mid-document failure, before its partial results are discarded.
    EMBEDDING_PARTIAL_RETRIES: int = int(os.getenv("EMBEDDING_PARTIAL_RETRIES", "2"))
    # Default wait (seconds) between retries when the provider gives no retry delay.
    EMBEDDING_RETRY_WAIT_SECONDS: int = int(os.getenv("EMBEDDING_RETRY_WAIT_SECONDS", "60"))

    JINA_MAX_RPM: int = int(os.getenv("JINA_MAX_RPM", "100"))
    JINA_MAX_TPM: int = int(os.getenv("JINA_MAX_TPM", "100000"))
    JINA_SAFE_TPM: int = int(os.getenv("JINA_SAFE_TPM", "90000"))
    JINA_BATCH_SIZE: int = int(os.getenv("JINA_BATCH_SIZE", "50"))

    LOCAL_BATCH_SIZE: int = int(os.getenv("LOCAL_BATCH_SIZE", "32"))
    # Max tokens per text for the local model; longer texts are truncated silently by the
    # library, so a warning is logged when a text exceeds it. The model supports up to 512.
    LOCAL_MAX_SEQ_LENGTH: int = int(os.getenv("LOCAL_MAX_SEQ_LENGTH", "256"))

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
    SUPABASE_BUCKET_ARTIFACTS: str = os.getenv("SUPABASE_BUCKET_ARTIFACTS", "adapted-artifacts")

    # ── OCI Object Storage Configuration (Always Free) ───────────────────────
    OCI_CONFIG_FILE: str = os.path.expanduser("~/.oci/config")
    OCI_BUCKET_DOCS: str = "nuevamente-documentos-fuente"
    OCI_BUCKET_ARTIFACTS: str = "nuevamente-contenidos-educativos"

    @property
    def OCI_ENABLED(self) -> bool:
        return os.path.exists(self.OCI_CONFIG_FILE)

    # ── RAG Configuration ─────────────────────────────────────────────────────
    MAX_TOP_K_CHUNKS: int = 5
    RRF_DENSE_WEIGHT: float = 0.6
    RRF_SPARSE_WEIGHT: float = 0.4
    RAG_CONTEXT_SNIPPET_SIZE: int = 1500
    RAG_RERANK_POOL_SIZE: int = 10

    # ── Ingestion Configuration ───────────────────────────────────────────────
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".md", ".markdown", ".txt"]
    MAX_FILE_SIZE_MB: int = 20
    # Parent chunks: large context windows sent to the LLM for generation.
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    # Child chunks: smaller dense units embedded and indexed in FAISS.
    # Must be strictly less than CHUNK_SIZE and greater than CHILD_CHUNK_OVERLAP.
    CHILD_CHUNK_SIZE: int = int(os.getenv("CHILD_CHUNK_SIZE", "500"))
    CHILD_CHUNK_OVERLAP: int = int(os.getenv("CHILD_CHUNK_OVERLAP", "50"))

    # Extracts short key-concept tags per chunk at ingestion time (KeyBERT).
    # Disabled by default: it loads its own local model and adds ingestion
    # latency, so it's opt-in until measured on real documents.
    USE_KEYBERT_CONCEPTS: bool = os.getenv("USE_KEYBERT_CONCEPTS", "false").lower() == "true"

    # ── Text Cleaning & Noise Filtering (ingestion) ───────────────────────────
    # Normalizes extracted text: ligatures, invisible characters, line-break
    # hyphenation, explicit page numbering and repeated whitespace.
    CLEAN_TEXT: bool = os.getenv("CLEAN_TEXT", "true").lower() == "true"
    # Drops non-technical sections (legal pages, revision history, figure/table
    # indexes, near-empty pages, normative appendices) before chunking.
    FILTER_NOISE_SECTIONS: bool = os.getenv("FILTER_NOISE_SECTIONS", "true").lower() == "true"
    # Sections with fewer useful characters than this are candidates for removal.
    NOISE_MIN_SECTION_CHARS: int = int(os.getenv("NOISE_MIN_SECTION_CHARS", "40"))
    # If the filter would discard more than this share of the document text,
    # it is skipped and a warning is logged.
    NOISE_MAX_DISCARD_RATIO: float = float(os.getenv("NOISE_MAX_DISCARD_RATIO", "0.4"))
    # Distinct legal patterns a section must match to be treated as a legal page.
    NOISE_MIN_LEGAL_PATTERNS: int = int(os.getenv("NOISE_MIN_LEGAL_PATTERNS", "2"))
    # A section longer than this is never discarded as a legal page by content.
    NOISE_MAX_LEGAL_SECTION_CHARS: int = int(os.getenv("NOISE_MAX_LEGAL_SECTION_CHARS", "1500"))
    # Revision-like lines ("Rev A", "Revision 2") needed to treat a section as a change log.
    NOISE_MIN_REVISION_LINES: int = int(os.getenv("NOISE_MIN_REVISION_LINES", "3"))
    # Share of lines ending in dot leaders + page number needed to treat a section as an index.
    NOISE_MIN_DOT_LEADER_RATIO: float = float(os.getenv("NOISE_MIN_DOT_LEADER_RATIO", "0.4"))
    # A section longer than this is never discarded by content patterns.
    NOISE_PROTECT_LONG_SECTION_CHARS: int = int(os.getenv("NOISE_PROTECT_LONG_SECTION_CHARS", "2000"))
    # Editable JSON with the title and content patterns of each noise category.
    NOISE_PATTERNS_FILE: str = os.getenv(
        "NOISE_PATTERNS_FILE",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "noise_patterns.json"),
    )

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