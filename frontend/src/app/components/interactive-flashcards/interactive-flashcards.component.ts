import { Component, Input } from '@angular/core';
import { FlashcardItem } from '../../core/models/adaptation.model';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-interactive-flashcards',
  template: `
    <div class="flashcards-section">
      <div class="section-header">
        <div class="header-left">
          <h3>🎴 Flashcards Didácticas & Repetición Espaciada ({{ items.length }})</h3>
          <span class="subtext">Haz clic en cada tarjeta para girarla y repasar conceptos clave. Integrado con <strong>Anki</strong>.</span>
        </div>
        <div class="anki-integration-actions">
          <button class="anki-btn export-btn" (click)="downloadAnkiDeck()" [disabled]="isExporting">
            <span *ngIf="!isExporting">📥 Exportar Paquete Anki (.apkg)</span>
            <span *ngIf="isExporting">⏳ Generando mazo .apkg...</span>
          </button>
          <button class="anki-btn sync-btn" (click)="syncWithAnkiConnect()" [disabled]="isSyncing">
            <span *ngIf="!isSyncing">⚡ Sincronizar AnkiConnect</span>
            <span *ngIf="isSyncing">⏳ Conectando...</span>
          </button>
          <button class="anki-btn info-btn" (click)="showAnkiInfo = !showAnkiInfo">
            💡 Guía Anki / Credenciales
          </button>
        </div>
      </div>

      <!-- Info Banner regarding Anki API Keys and accounts -->
      <div *ngIf="showAnkiInfo" class="anki-info-banner">
        <div class="banner-title">
          <span>ℹ️ Informes de Integración Anki (Algoritmo SM-2 Spaced Repetition)</span>
          <button class="close-info" (click)="showAnkiInfo = false">✕</button>
        </div>
        <div class="banner-content">
          <p><strong>¿Requiere registro o API Key?</strong> <u>NO</u>. Puedes exportar y estudiar tus tarjetas en la app oficial de Anki de forma 100% libre y sin crear ninguna clave de API.</p>
          <ul>
            <li><strong>Anki Desktop / Mobile:</strong> Descarga el paquete <code>.apkg</code> generado e impórtalo directamente (Menú Archivo ➔ Importar).</li>
            <li><strong>AnkiWeb (Nube Gratuita):</strong> Si deseas sincronizar con la nube para estudiar en la web o celular, crea una cuenta gratuita en <a href="https://ankiweb.net" target="_blank" class="anki-link">ankiweb.net</a>.</li>
            <li><strong>AnkiConnect:</strong> Si tienes Anki Desktop abierto con el complemento <code>2055492159</code>, el botón 'Sincronizar AnkiConnect' enviará las tarjetas al instante a tu mazo local.</li>
          </ul>
        </div>
      </div>

      <!-- Status Toast Message -->
      <div *ngIf="statusMessage" class="status-alert" [ngClass]="statusMessageType">
        {{ statusMessage }}
      </div>

      <div class="flashcards-grid">
        <div 
          *ngFor="let card of items; let i = index" 
          class="flashcard-card" 
          [ngClass]="{'flipped': flippedState[i]}"
          (click)="toggleFlip(i)"
        >
          <div class="card-inner">
            <!-- Front Face -->
            <div class="card-front">
              <div class="card-header-badge">
                <span>Flashcard #{{ i + 1 }}</span>
                <span class="anki-tag">⭐️ Anki Ready</span>
              </div>
              <div class="card-question">❓ {{ card.frente }}</div>
              <div *ngIf="card.pista_didactica" class="card-hint">
                💡 <strong>Pista:</strong> {{ card.pista_didactica }}
              </div>
              <div class="flip-instruction">Toca para voltear ➔</div>
            </div>

            <!-- Back Face -->
            <div class="card-back">
              <div class="card-header-badge back-badge">Respuesta Didáctica</div>
              <div class="card-answer">✨ {{ card.dorso }}</div>
              <div class="flip-instruction back-instruction">↺ Volver a la pregunta</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .flashcards-section {
      margin-top: 2rem;
      margin-bottom: 2rem;
    }
    .section-header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.25rem;
    }
    .section-header h3 {
      font-size: 1.25rem;
      font-weight: 800;
      color: #0f172a;
      margin: 0;
    }
    .subtext {
      font-size: 0.85rem;
      color: #64748b;
    }

    .anki-integration-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .anki-btn {
      padding: 0.5rem 0.85rem;
      border-radius: 10px;
      font-size: 0.82rem;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }

    .export-btn {
      background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
    }
    .export-btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(79, 70, 229, 0.35);
    }

    .sync-btn {
      background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
    }
    .sync-btn:hover {
      transform: translateY(-1px);
    }

    .info-btn {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .info-btn:hover {
      background: #e2e8f0;
      color: #1e293b;
    }

    .anki-info-banner {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-left: 4px solid #6366f1;
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1.25rem;
    }

    .banner-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 700;
      font-size: 0.92rem;
      color: #334155;
      margin-bottom: 0.5rem;
    }

    .close-info {
      background: none;
      border: none;
      font-size: 1rem;
      color: #64748b;
      cursor: pointer;
    }

    .banner-content p {
      font-size: 0.85rem;
      color: #475569;
      margin-bottom: 0.5rem;
    }

    .banner-content ul {
      margin: 0;
      padding-left: 1.25rem;
      font-size: 0.82rem;
      color: #475569;
    }

    .banner-content li {
      margin-bottom: 0.3rem;
    }

    .anki-link {
      color: #2563eb;
      font-weight: 700;
      text-decoration: underline;
    }

    .status-alert {
      padding: 0.75rem 1rem;
      border-radius: 10px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 1.25rem;
    }

    .status-alert.success {
      background: #f0fdf4;
      color: #166534;
      border: 1px solid #bbf7d0;
    }

    .status-alert.warning {
      background: #fffbeb;
      color: #92400e;
      border: 1px solid #fde68a;
    }

    .flashcards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
    }

    .flashcard-card {
      perspective: 1000px;
      height: 230px;
      cursor: pointer;
    }

    .card-inner {
      position: relative;
      width: 100%;
      height: 100%;
      transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
      transform-style: preserve-3d;
      border-radius: 16px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.04);
    }

    .flashcard-card.flipped .card-inner {
      transform: rotateY(180deg);
    }

    .card-front, .card-back {
      position: absolute;
      width: 100%;
      height: 100%;
      backface-visibility: hidden;
      border-radius: 16px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 1px solid #e2e8f0;
      background: #ffffff;
    }

    .card-front {
      background: #ffffff;
    }

    .card-back {
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      border-color: #bfdbfe;
      transform: rotateY(180deg);
    }

    .card-header-badge {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #3b82f6;
    }

    .anki-tag {
      font-size: 0.68rem;
      background: #e0e7ff;
      color: #4338ca;
      padding: 2px 6px;
      border-radius: 6px;
    }

    .back-badge {
      color: #1e40af;
    }

    .card-question {
      font-size: 1.02rem;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.4;
    }

    .card-hint {
      font-size: 0.8rem;
      color: #b45309;
      background: #fffbeb;
      padding: 0.4rem 0.75rem;
      border-radius: 8px;
    }

    .card-answer {
      font-size: 0.95rem;
      font-weight: 600;
      color: #1e3a8a;
      line-height: 1.5;
    }

    .flip-instruction {
      font-size: 0.75rem;
      font-weight: 700;
      color: #94a3b8;
      text-align: right;
    }
    .back-instruction {
      color: #3b82f6;
    }
  `]
})
export class InteractiveFlashcardsComponent {
  @Input() items: FlashcardItem[] = [];

  flippedState: { [key: number]: boolean } = {};
  isExporting = false;
  isSyncing = false;
  showAnkiInfo = false;
  statusMessage = '';
  statusMessageType: 'success' | 'warning' = 'success';

  constructor(private apiService: ApiService) {}

  toggleFlip(index: number): void {
    this.flippedState[index] = !this.flippedState[index];
  }

  downloadAnkiDeck(): void {
    if (!this.items || this.items.length === 0) return;

    this.isExporting = true;
    this.statusMessage = '';

    this.apiService.exportAnkiDeck('NuevaMente - Adaptación Inteligente', this.items).subscribe({
      next: (blob: Blob) => {
        this.isExporting = false;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `NuevaMente_Anki_Deck_${Date.now()}.apkg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.statusMessageType = 'success';
        this.statusMessage = '✅ ¡Mazo Anki (.apkg) descargado con éxito! Abre el archivo para importarlo en Anki Desktop o AnkiMobile.';
      },
      error: (err) => {
        this.isExporting = false;
        this.statusMessageType = 'warning';
        this.statusMessage = '⚠️ No se pudo generar el archivo .apkg. Intenta de nuevo.';
      }
    });
  }

  syncWithAnkiConnect(): void {
    if (!this.items || this.items.length === 0) return;

    this.isSyncing = true;
    this.statusMessage = '';

    this.apiService.syncAnkiConnect('NuevaMente - Adaptación Inteligente', this.items).subscribe({
      next: (res: any) => {
        this.isSyncing = false;
        if (res.status === 'exito') {
          this.statusMessageType = 'success';
          this.statusMessage = `✅ ${res.message}`;
        } else {
          this.statusMessageType = 'warning';
          this.statusMessage = `ℹ️ ${res.message} ${res.recommendation}`;
        }
      },
      error: () => {
        this.isSyncing = false;
        this.statusMessageType = 'warning';
        this.statusMessage = 'ℹ️ No se detectó AnkiConnect localmente. Descarga el paquete .apkg e impórtalo en Anki.';
      }
    });
  }
}
