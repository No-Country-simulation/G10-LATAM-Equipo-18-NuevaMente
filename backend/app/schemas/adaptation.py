"""
adaptation.py

Purpose:
    Typed Pydantic data contracts for educational content adaptation requests
    and responses. Defined in English with field aliases to maintain full
    backward compatibility with Spanish keys used by frontend or tests.

Input:
    Used as type definitions across API, agents, and storage layers.

Output:
    Models: AdaptationRequest, AdaptationResponse, AdaptedContent,
            FlashcardItem, QuizItem, ResponseMetadata, QualityEvaluation, OCIStorageResult.
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
    quantity: Optional[int] = Field(default=5, alias="cantidad_generar")
    chunk_size: Optional[int] = Field(default=500, alias="tamano_chunk", description="Tamaño de fragmentación (chunks) para el procesamiento RAG (100 - 2000)")
    additional_instructions: Optional[str] = Field(default=None, alias="instrucciones_adicionales")


class FlashcardItem(BaseModel):
    """Represents a single flashcard question/answer pair."""
    model_config = ConfigDict(populate_by_name=True)

    front: str = Field(..., alias="frente")
    back: str = Field(..., alias="dorso")
    hint: Optional[str] = Field(None, alias="pista_didactica")


class QuizItem(BaseModel):
    """Represents a multiple-choice quiz question."""
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., alias="pregunta")
    options: List[str] = Field(..., alias="opciones")
    correct_answer: str = Field(..., alias="respuesta_correcta")
    didactic_justification: str = Field(..., alias="justificacion_didactica")


class AdaptedContent(BaseModel):
    """Structured educational material produced by agents."""
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., alias="titulo")
    contextualized_introduction: str = Field(..., alias="introduccion_contextualizada")
    executive_summary: Optional[str] = Field(None, alias="resumen_ejecutivo")
    items: Optional[List[FlashcardItem]] = None
    quizzes: Optional[List[QuizItem]] = None
    tutorial_sections: Optional[List[Dict[str, str]]] = Field(None, alias="secciones_tutorial")


class ResponseMetadata(BaseModel):
    """Metadata regarding adaptation execution and study metrics."""
    model_config = ConfigDict(populate_by_name=True)

    profile_applied: str = Field(..., alias="perfil_aplicado")
    format_generated: str = Field(..., alias="formato_generado")
    estimated_study_time_minutes: int = Field(..., alias="tiempo_estimado_estudio_minutos")
    key_concepts: List[str] = Field(..., alias="conceptos_clave")
    prerequisites: Optional[List[str]] = Field(None, alias="prerrequisitos")


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
