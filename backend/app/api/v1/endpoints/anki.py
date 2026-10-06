import tempfile
import os
import random
import zlib
from typing import List, Optional
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import genanki

router = APIRouter()

class FlashcardItem(BaseModel):
    frente: str
    dorso: str
    pista_didactica: Optional[str] = None

class AnkiExportRequest(BaseModel):
    deck_name: Optional[str] = "NuevaMente - Adaptación Educativa"
    flashcards: List[FlashcardItem]

class AnkiSyncRequest(BaseModel):
    deck_name: Optional[str] = "NuevaMente - Adaptación Educativa"
    flashcards: List[FlashcardItem]

def generate_stable_id(name: str) -> int:
    """Genera un ID entero único de 30 bits para genanki basado en el nombre del mazo."""
    return abs(zlib.crc32(name.encode('utf-8'))) % 1000000000 + 1000000000

@router.post("/anki/export-deck")
def export_anki_deck(request: AnkiExportRequest):
    if not request.flashcards:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos una tarjeta (flashcard) para exportar.")

    deck_title = request.deck_name or "NuevaMente - Adaptación Educativa"
    model_id = generate_stable_id(deck_title + "_model")
    deck_id = generate_stable_id(deck_title + "_deck")

    style = """
    .card {
        font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
        font-size: 18px;
        text-align: center;
        color: #0f172a;
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border: 2px solid #6366f1;
    }
    .question {
        font-weight: 700;
        font-size: 20px;
        color: #4f46e5;
        margin-bottom: 12px;
    }
    .hint {
        font-size: 14px;
        color: #64748b;
        background-color: #f1f5f9;
        padding: 6px 12px;
        border-radius: 9999px;
        display: inline-block;
        margin-top: 10px;
    }
    .answer {
        font-size: 18px;
        color: #0284c7;
        font-weight: 600;
        background-color: #e0f2fe;
        padding: 16px;
        border-radius: 12px;
        margin-top: 16px;
        border: 1px solid #7dd3fc;
    }
    .badge {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8b5cf6;
        font-weight: 800;
        margin-bottom: 8px;
    }
    """

    my_model = genanki.Model(
        model_id,
        'Modelo NuevaMente AI Flashcards',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
            {'name': 'Hint'}
        ],
        templates=[
            {
                'name': 'Tarjeta NuevaMente',
                'qfmt': '''
                <div class="card">
                    <div class="badge">🧠 NuevaMente Flashcard</div>
                    <div class="question">{{Question}}</div>
                    {{#Hint}}<div class="hint">💡 Pista: {{Hint}}</div>{{/Hint}}
                </div>
                ''',
                'afmt': '''
                <div class="card">
                    <div class="badge">🧠 NuevaMente Flashcard</div>
                    <div class="question">{{Question}}</div>
                    <hr style="border: 0; height: 1px; background: #e2e8f0; margin: 16px 0;">
                    <div class="answer">{{Answer}}</div>
                </div>
                ''',
            }
        ],
        css=style
    )

    my_deck = genanki.Deck(deck_id, deck_title)

    for card in request.flashcards:
        note = genanki.Note(
            model=my_model,
            fields=[
                card.frente.strip(),
                card.dorso.strip(),
                card.pista_didactica.strip() if card.pista_didactica else ""
            ]
        )
        my_deck.add_note(note)

    # Generar el archivo temporal .apkg
    temp_dir = tempfile.mkdtemp()
    import secrets
    file_name = f"NuevaMente_Deck_{secrets.token_hex(4)}.apkg"
    output_path = os.path.join(temp_dir, file_name)

    package = genanki.Package(my_deck)
    package.write_to_file(output_path)

    return FileResponse(
        path=output_path,
        media_type="application/apkg",
        filename=file_name,
        headers={"Content-Disposition": f"attachment; filename={file_name}"}
    )

@router.post("/anki/sync-ankiconnect")
def sync_anki_connect(request: AnkiSyncRequest):
    """Sincroniza directamente con la extensión AnkiConnect en http://localhost:8765 si está activa en el equipo."""
    anki_connect_url = "http://localhost:8765"

    notes_payload = []
    for card in request.flashcards:
        notes_payload.append({
            "deckName": request.deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": f"<b>{card.frente}</b>" + (f"<br><small>💡 Pista: {card.pista_didactica}</small>" if card.pista_didactica else ""),
                "Back": card.dorso
            },
            "tags": ["nuevamente", "adaptacion_ia"]
        })

    try:
        # Intentar crear mazo
        requests.post(anki_connect_url, json={
            "action": "createDeck",
            "version": 6,
            "params": {"deck": request.deck_name}
        }, timeout=2)

        # Añadir tarjetas
        res = requests.post(anki_connect_url, json={
            "action": "addNotes",
            "version": 6,
            "params": {"notes": notes_payload}
        }, timeout=3)
        res_data = res.json()

        return {
            "status": "exito",
            "message": f"Se sincronizaron exitosamente {len(request.flashcards)} tarjetas con tu aplicación Anki Desktop local.",
            "detail": res_data
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": "No se detectó el complemento AnkiConnect en ejecución en http://localhost:8765.",
            "recommendation": "Puedes descargar el archivo .apkg haciendo clic en 'Exportar Paquete Anki (.apkg)' e importarlo directamente en Anki Desktop, AnkiMobile o AnkiWeb (gratuito)."
        }

@router.get("/anki/info")
def get_anki_integration_info():
    """Retorna información detallada sobre la integración con Anki, credenciales y claves API."""
    return {
        "title": "Integración de Tarjetas Educativas con Anki (Spaced Repetition)",
        "requires_api_key": False,
        "requires_registration": False,
        "features": [
            "Exportación nativa directa a paquetes .apkg compatibles con Anki Desktop, AnkiDroid, AnkiMobile y AnkiWeb.",
            "Algoritmo de Repetición Espaciada (Spaced Repetition / SuperMemo SM-2) integrado al usar Anki.",
            "Sincronización opcional automática con AnkiConnect en puerto 8765."
        ],
        "instructions": {
            "anki_desktop": "Abre Anki -> Archivo -> Importar -> Selecciona el archivo .apkg descargado.",
            "anki_web": "Crea una cuenta gratuita en https://ankiweb.net -> Importa tu paquete .apkg para estudiar en cualquier navegador o celular.",
            "anki_connect": "Instala el add-on AnkiConnect (Código: 2055492159) en Anki Desktop para sincronización con 1-clic."
        }
    }
