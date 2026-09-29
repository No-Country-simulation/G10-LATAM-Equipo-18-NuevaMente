import { Component, Input, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlashcardItem, RagFuente } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-flashcards-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flashcards-container" *ngIf="items && items.length > 0">
      <!-- Top Toolbar / Study Stats (Interactive Screen Mode Only) -->
      <div class="study-bar no-print">
        <div class="card-counter">
          Tarjeta {{ currentIndex() + 1 }} de {{ items.length }}
        </div>
        <div class="mode-stats">
          <span class="stat-known">✓ Sabidas: {{ knownCount() }}</span>
          <span class="stat-review">🔄 Repasar: {{ reviewCount() }}</span>
        </div>
        <div class="keyboard-hint">
          <span>Keyboard: <b>Space</b> (Flip), <b>← / →</b> (Navegar)</span>
        </div>
      </div>

      <!-- Main 3D Flip Card Container (Interactive Screen Mode Only) -->
      <div class="card-3d-wrapper no-print" (click)="toggleFlip()">
        <div class="card-3d" [class.flipped]="isFlipped()">
          <!-- Front Face -->
          <div class="card-face card-front">
            <div class="face-badge">PREGUNTA / CONCEPTO</div>
            <div class="face-content">
              <h3>{{ currentCard.frente }}</h3>
            </div>
            <div class="face-footer" *ngIf="currentCard.pista_didactica">
              <span class="hint-tag">💡 Pista: {{ currentCard.pista_didactica }}</span>
            </div>
          </div>

          <!-- Back Face -->
          <div class="card-face card-back">
            <div class="face-badge back-badge">RESPUESTA / EXPLICACIÓN</div>
            <div class="face-content">
              <p>{{ currentCard.dorso }}</p>
            </div>
            
            <!-- RAG Source Badge if present -->
            <div class="face-sources" *ngIf="currentCard.fuentes && currentCard.fuentes.length > 0" (click)="$event.stopPropagation(); selectFuente(currentCard.fuentes[0])">
              <span class="source-chip">
                🔍 Cita Fuente [Pág {{ currentCard.fuentes[0].pagina || 1 }}] (Score: {{ (currentCard.fuentes[0].similitud_score || 0.95) * 100 | number:'1.0-0' }}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Action & Navigation Controls (Interactive Screen Mode Only) -->
      <div class="controls-row no-print">
        <button class="btn-nav" (click)="prevCard()" [disabled]="currentIndex() === 0">
          ← Anterior
        </button>

        <div class="review-buttons" *ngIf="isFlipped()">
          <button class="btn-review" (click)="markReview()">🔄 Necesito Repasar</button>
          <button class="btn-known" (click)="markKnown()">✅ Lo Sabía</button>
        </div>

        <button class="btn-nav" (click)="nextCard()" [disabled]="currentIndex() === items.length - 1">
          Siguiente →
        </button>
      </div>

      <!-- PRINT-ONLY DEDICATED FLASHCARDS LIST (All Cards Cleanly Formatted for PDF Export) -->
      <div class="print-only-list">
        <h2 class="print-section-title">Mazo Completo de Flashcards ({{ items.length }} Tarjetas)</h2>
        <div class="print-card-item" *ngFor="let card of items; let idx = index">
          <div class="print-card-header">Tarjeta #{{ idx + 1 }}</div>
          <div class="print-card-q"><strong>Pregunta / Concepto:</strong> {{ card.frente }}</div>
          <div class="print-card-a"><strong>Respuesta / Explicación:</strong> {{ card.dorso }}</div>
          <div class="print-card-hint" *ngIf="card.pista_didactica"><em>💡 Pista: {{ card.pista_didactica }}</em></div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .flashcards-container {
      max-width: 680px;
      margin: 0 auto;
      padding: 1rem 0;
    }

    .study-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
      color: var(--text-secondary);
    }

    .card-counter {
      font-weight: 700;
      color: var(--text-primary);
    }

    .mode-stats {
      display: flex;
      gap: 1rem;
      font-weight: 600;
    }
    .stat-known { color: #10B981; }
    .stat-review { color: #F59E0B; }

    .keyboard-hint {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    /* 3D FLIP CARD */
    .card-3d-wrapper {
      perspective: 1000px;
      height: 320px;
      cursor: pointer;
      margin-bottom: 1.5rem;
    }

    .card-3d {
      width: 100%;
      height: 100%;
      position: relative;
      transform-style: preserve-3d;
      transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .card-3d.flipped {
      transform: rotateY(180deg);
    }

    .card-face {
      position: absolute;
      inset: 0;
      backface-visibility: hidden;
      border-radius: 20px;
      padding: 2.25rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-lg);
    }

    .card-front {
      border-top: 4px solid #EC4899;
    }

    .card-back {
      transform: rotateY(180deg);
      border-top: 4px solid #10B981;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(16, 185, 129, 0.04) 100%);
    }

    .face-badge {
      font-size: 0.72rem;
      font-weight: 800;
      color: #EC4899;
      letter-spacing: 0.08em;
    }
    .back-badge { color: #10B981; }

    .face-content h3 {
      font-size: 1.45rem;
      line-height: 1.35;
      font-weight: 700;
    }

    .face-content p {
      font-size: 1.1rem;
      line-height: 1.6;
      color: var(--text-primary);
    }

    .face-footer {
      border-top: 1px solid var(--border-subtle);
      padding-top: 0.75rem;
    }

    .hint-tag {
      font-size: 0.85rem;
      color: var(--text-secondary);
      font-style: italic;
    }

    .face-sources {
      margin-top: 0.75rem;
    }

    .source-chip {
      display: inline-flex;
      align-items: center;
      padding: 0.35rem 0.75rem;
      border-radius: 12px;
      background: rgba(34, 211, 238, 0.12);
      border: 1px solid rgba(34, 211, 238, 0.3);
      color: #0284C7;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }

    .controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .btn-nav {
      padding: 0.6rem 1.25rem;
      border-radius: 10px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-weight: 600;
      cursor: pointer;
    }

    .btn-nav:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .review-buttons {
      display: flex;
      gap: 0.75rem;
    }

    .btn-review {
      padding: 0.6rem 1rem;
      border-radius: 10px;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid #F59E0B;
      color: #D97706;
      font-weight: 700;
      cursor: pointer;
    }

    .btn-known {
      padding: 0.6rem 1rem;
      border-radius: 10px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10B981;
      color: #059669;
      font-weight: 700;
      cursor: pointer;
    }

    .print-only-list {
      display: none;
    }

    @media print {
      .no-print, .study-bar, .card-3d-wrapper, .controls-row {
        display: none !important;
      }
      .print-only-list {
        display: block !important;
        max-width: 100% !important;
      }
      .print-section-title {
        font-size: 1.4pt !important;
        font-weight: 800 !important;
        margin-bottom: 1rem !important;
        color: #000000 !important;
      }
      .print-card-item {
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        page-break-inside: avoid !important;
        background: #ffffff !important;
      }
      .print-card-header {
        font-weight: 800 !important;
        color: #4f46e5 !important;
        margin-bottom: 0.4rem !important;
        font-size: 0.9pt !important;
      }
      .print-card-q {
        font-size: 1.1pt !important;
        margin-bottom: 0.4rem !important;
        color: #0f172a !important;
      }
      .print-card-a {
        font-size: 0.95pt !important;
        color: #334155 !important;
        line-height: 1.5 !important;
      }
      .print-card-hint {
        font-size: 0.85pt !important;
        color: #64748b !important;
        margin-top: 0.4rem !important;
      }
    }
  `]
})
export class FlashcardsRendererComponent {
  @Input({ required: true }) items: FlashcardItem[] = [];

  currentIndex = signal<number>(0);
  isFlipped = signal<boolean>(false);
  knownCount = signal<number>(0);
  reviewCount = signal<number>(0);

  get currentCard(): FlashcardItem {
    return this.items[this.currentIndex()] || { frente: '', dorso: '' };
  }

  toggleFlip(): void {
    this.isFlipped.update(v => !v);
  }

  nextCard(): void {
    if (this.currentIndex() < this.items.length - 1) {
      this.currentIndex.update(i => i + 1);
      this.isFlipped.set(false);
    }
  }

  prevCard(): void {
    if (this.currentIndex() > 0) {
      this.currentIndex.update(i => i - 1);
      this.isFlipped.set(false);
    }
  }

  markKnown(): void {
    this.knownCount.update(c => c + 1);
    this.nextCard();
  }

  markReview(): void {
    this.reviewCount.update(c => c + 1);
    this.nextCard();
  }

  selectFuente(fuente: RagFuente): void {
    console.log('Selected fuente:', fuente);
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent): void {
    if (event.code === 'Space') {
      event.preventDefault();
      this.toggleFlip();
    } else if (event.code === 'ArrowRight') {
      this.nextCard();
    } else if (event.code === 'ArrowLeft') {
      this.prevCard();
    }
  }
}
