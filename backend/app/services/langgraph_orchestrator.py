from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END
from app.schemas.adaptation import AdaptationRequest, AdaptedContent
from app.infrastructure.llm import GroqClient as GroqAdapter
from loguru import logger
from pydantic import BaseModel

# 1. Definimos el Estado del Grafo
class AgentState(TypedDict):
    request: AdaptationRequest
    context: str
    draft: AdaptedContent
    feedback: str
    revision_count: int
    is_approved: bool

# Definimos el esquema de evaluación del Crítico
class ReviewEvaluation(BaseModel):
    is_approved: bool
    feedback: str

class LangGraphOrchestrator:
    """
    Implementación del requisito diferencial de Hackathon ONE:
    Sistema Multi-Agente con LangGraph (Investigador, Redactor, Revisor).
    """
    def __init__(self):
        self.llm_adapter = GroqAdapter()
        self.max_revisions = 2

    def _node_researcher(self, state: AgentState) -> dict:
        """Agente Investigador: Extrae y resume el contexto relevante (Simulado aquí si ya viene en el state)."""
        logger.info("🕵️ [Agente Investigador] Analizando el documento original...")
        # Aquí normalmente haríamos la llamada a FAISS/VectorStore.
        # Asumimos que el contexto ya está en el state o lo limpiamos.
        return {"context": state['context']}

    def _node_writer(self, state: AgentState) -> dict:
        """Agente Redactor: Genera el contenido pedagógico estructurado."""
        logger.info(f"✍️ [Agente Redactor] Escribiendo borrador (Revisión #{state.get('revision_count', 0)})...")
        
        profile = state['request'].recipient_profile
        profile_str = profile.value if hasattr(profile, 'value') else str(profile)
        
        fmt = state['request'].output_format
        fmt_str = fmt.value if hasattr(fmt, 'value') else str(fmt)
        
        prompt = f"""
        Eres un experto pedagogo. Adapta el siguiente contenido técnico al perfil '{profile_str}'.
        Formato requerido: '{fmt_str}'
        Contexto original:
        {state['context']}
        
        Feedback previo a corregir (si aplica): {state.get('feedback', 'Ninguno, es el primer borrador.')}
        """
        
        # Usamos nuestro GroqAdapter resiliente para generar el JSON exacto de AdaptedContent
        draft = self.llm_adapter.generate_structured(prompt, AdaptedContent)
        
        # Incrementamos el contador de revisiones
        rev_count = state.get('revision_count', 0) + 1
        return {"draft": draft, "revision_count": rev_count}

    def _node_reviewer(self, state: AgentState) -> dict:
        """Agente Crítico: Evalúa si el borrador cumple con la calidad y fidelidad."""
        logger.info("🧐 [Agente Crítico] Evaluando calidad pedagógica y anclaje (fidelidad)...")
        
        profile = state['request'].recipient_profile
        profile_str = profile.value if hasattr(profile, 'value') else str(profile)
        
        prompt = f"""
        Eres un crítico técnico riguroso. Evalúa este borrador educativo.
        Perfil objetivo: '{profile_str}'.
        
        Borrador generado: {state['draft'].model_dump_json()}
        
        ¿Cumple con el perfil objetivo de manera clara y no contiene alucinaciones técnicas?
        Responde estrictamente con un JSON según el esquema solicitado. Si no apruebas, da un feedback claro de qué arreglar.
        """
        
        eval_result = self.llm_adapter.generate_structured(prompt, ReviewEvaluation)
        
        logger.info(f"Resultado de Evaluación: Aprobado={eval_result.is_approved}, Feedback='{eval_result.feedback}'")
        return {"is_approved": eval_result.is_approved, "feedback": eval_result.feedback}

    def _router_needs_revision(self, state: AgentState) -> str:
        """Enrutador de Decisión: Decide si el grafo termina o vuelve al redactor."""
        if state["is_approved"] or state["revision_count"] >= self.max_revisions:
            if not state["is_approved"]:
                logger.warning("⚠️ Límite de revisiones alcanzado. Forzando aprobación del mejor borrador.")
            return "end"
        logger.info("🔄 Devolviendo al Redactor para correcciones...")
        return "rewrite"

    def build_graph(self) -> StateGraph:
        """Construye y compila el flujo del grafo."""
        workflow = StateGraph(AgentState)

        # Añadimos los nodos (agentes)
        workflow.add_node("researcher", self._node_researcher)
        workflow.add_node("writer", self._node_writer)
        workflow.add_node("reviewer", self._node_reviewer)

        # Definimos el flujo lógico
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "writer")
        workflow.add_edge("writer", "reviewer")
        
        # Añadimos la condicional
        workflow.add_conditional_edges(
            "reviewer",
            self._router_needs_revision,
            {
                "rewrite": "writer",
                "end": END
            }
        )

        return workflow.compile()

    def run(self, request: AdaptationRequest, context: str) -> AdaptedContent:
        graph = self.build_graph()
        initial_state = {
            "request": request,
            "context": context,
            "revision_count": 0,
            "is_approved": False,
            "feedback": ""
        }
        
        # Ejecutamos el grafo hasta el final
        final_state = graph.invoke(initial_state)
        logger.success("🎉 Flujo Multi-Agente de LangGraph completado exitosamente.")
        return final_state["draft"]
