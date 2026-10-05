"""
adaptation.py

Purpose:
    Typed Pydantic data contracts for educational content adaptation requests
    and responses. Defined in English with field aliases to maintain full
    backward compatibility with Spanish keys used by frontend or tests.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AdaptationRequest(BaseModel):
    """Payload submitted to request adapted educational content."""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., alias="documento_titulo")
    content: str = Field(..., alias="documento_contenido")
    recipient_profile: str = Field(..., alias="perfil_destinatario")
    output_format: str = Field(..., alias="formato_salida")
    niche: str = Field(default="general", alias="nicho_sector")
    detail_level: str = Field(default="didactic", alias="nivel_detalle")
    quantity_level: Optional[str] = Field(default="Estandar", alias="nivel_cantidad")
    target_quantity: Optional[int] = Field(default=None, alias="cantidad_objetivo")
    quantity: Optional[int] = Field(default=5, alias="cantidad_generar")
    chunk_size: Optional[int] = Field(default=500, alias="tamano_chunk", description="Tamaño de fragmentación (chunks) para el procesamiento RAG (100 - 2000)")
    additional_instructions: Optional[str] = Field(default=None, alias="instrucciones_adicionales")
    force_regenerate: Optional[bool] = Field(default=False, alias="forzar_regenerar")

    from pydantic import field_validator

    @field_validator("target_quantity", mode="before")
    @classmethod
    def check_max_quantity(cls, v):
        if v is not None and isinstance(v, int) and v > 100:
            raise ValueError("La cantidad solicitada supera el límite máximo permitido (100).")
        return v


class RagFuente(BaseModel):
    """Source passage citation for RAG grounding."""
    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str
    extracto: str
    pagina: Optional[int] = 1
    similitud_score: Optional[float] = 0.95


class FlashcardItem(BaseModel):
    """Represents a single flashcard question/answer pair."""
    model_config = ConfigDict(populate_by_name=True)

    front: str = Field(..., alias="frente")
    back: str = Field(..., alias="dorso")
    hint: Optional[str] = Field(None, alias="pista_didactica")
    sources: Optional[List[RagFuente]] = Field(None, alias="fuentes")


class QuizItem(BaseModel):
    """Represents a multiple-choice quiz question."""
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., alias="pregunta")
    options: List[str] = Field(..., alias="opciones")
    correct_answer: str = Field(..., alias="respuesta_correcta")
    justification: Optional[str] = Field(None, alias="justificacion")
    didactic_justification: Optional[str] = Field(None, alias="justificacion_didactica")
    sources: Optional[List[RagFuente]] = Field(None, alias="fuentes")


class AdaptedContent(BaseModel):
    """Structured educational material produced by agents."""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., alias="titulo")
    contextualized_introduction: str = Field(..., alias="introduccion_contextualizada")
    executive_summary: Optional[str] = Field(None, alias="resumen_ejecutivo")
    items: Optional[List[Any]] = None
    quizzes: Optional[List[QuizItem]] = None
    tutorial_sections: Optional[List[Dict[str, Any]]] = Field(None, alias="secciones_tutorial")


class ResponseMetadata(BaseModel):
    """Metadata regarding adaptation execution and study metrics."""
    model_config = ConfigDict(populate_by_name=True)

    profile_applied: str = Field(..., alias="perfil_aplicado")
    format_generated: str = Field(..., alias="formato_generado")
    niche_sector: Optional[str] = Field(None, alias="nicho_sector")
    detail_level: Optional[str] = Field(None, alias="nivel_detalle")
    quantity_level: Optional[str] = Field(None, alias="nivel_cantidad")
    requested_items: Optional[int] = Field(None, alias="items_solicitados")
    generated_items: Optional[int] = Field(None, alias="items_generados")
    quantity_warning: Optional[str] = Field(None, alias="aviso_cantidad")
    estimated_study_time_minutes: int = Field(..., alias="tiempo_estimado_estudio_minutos")
    key_concepts: List[str] = Field(..., alias="conceptos_clave")
    prerequisites: Optional[List[str]] = Field(None, alias="prerrequisitos")
    llm_provider: Optional[str] = Field("gemini", alias="proveedor_llm")
    llm_model: Optional[str] = Field("gemini-flash-latest", alias="modelo_llm")
    embedding_provider: Optional[str] = Field("gemini", alias="proveedor_embeddings")
    degraded_retrieval: Optional[bool] = Field(False, alias="recuperacion_degradada")
    retrieval_mode: Optional[str] = Field("semantico", alias="modo_recuperacion")
    fallback_used: Optional[bool] = Field(False, alias="fallback_usado")
    degradations: Optional[List[str]] = Field(default_factory=list, alias="degradaciones")
    ingestion_summary: Optional[Dict[str, Any]] = Field(None, alias="resumen_ingesta")
    prompt_hash: Optional[str] = Field(None, alias="prompt_hash")
    origin: Optional[str] = Field("llm", alias="origen")
    timings: Optional[Dict[str, float]] = Field(default_factory=dict, alias="timings")
    llm_calls: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="llm_calls")


class QualityEvaluation(BaseModel):
    """Grounding fidelity and educational quality audit."""
    model_config = ConfigDict(populate_by_name=True)

    source_grounding_score: float = Field(..., alias="anclaje_fuente_score", description="Fidelity score from 0.0 to 1.0")
    pedagogical_clarity: str = Field(..., alias="claridad_pedagogica")
    observations: str = Field(..., alias="observaciones")


class OCIStorageResult(BaseModel):
    """Storage metadata from Oracle Cloud Infrastructure Object Storage."""
    model_config = ConfigDict(populate_by_name=True)

    bucket: str
    object_id: str = Field(..., alias="objeto_id")
    upload_status: str = Field(..., alias="status_upload")


class AdaptationResponse(BaseModel):
    """Final unified response returned by adaptation endpoint."""
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="exito")
    metadata: ResponseMetadata = Field(..., alias="metadatos")
    adapted_content: AdaptedContent = Field(..., alias="contenido_adaptado")
    quality_evaluation: QualityEvaluation = Field(..., alias="evaluacion_calidad")
    oci_storage: OCIStorageResult = Field(..., alias="almacenamiento_oci")
    pdf_url: Optional[str] = Field(None, alias="url_pdf")

