from enum import Enum

class PerfilDestinatario(str, Enum):
    PRINCIPIANTE = "Principiante"
    JUNIOR = "Junior"
    ARQUITECTO = "Arquitecto"
    EJECUTIVO = "Ejecutivo"

class FormatoSalida(str, Enum):
    TUTORIAL = "Tutorial"
    FLASHCARDS = "Flashcards"
    QUIZ = "Quiz"
    RESUMEN = "Resumen"
    GUION_CLASE = "Guion de Clase / Video"

class NichoSector(str, Enum):
    FINTECH = "Fintech"
    SALUD = "Salud"
    ECOMMERCE = "E-commerce"
    GENERAL = "General"
