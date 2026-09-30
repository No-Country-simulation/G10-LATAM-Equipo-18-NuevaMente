import { Component, Input, signal, computed, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FlashcardItem, RagFuente } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-flashcards-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flashcards-container" *ngIf="items && items.length > 0">
      <!-- TOP CONTROL & STUDY STATS BAR -->
      <div class="study-bar glass-card no-print">
        <div class="bar-top">
          <div class="card-counter">
            <span class="badge-num">{{ currentIndex() + 1 }} / {{ activeItems().length }}</span>
            <span class="sub-counter">Tarjetas</span>
          </div>

          <div class="mode-stats">
            <span class="stat-known">✓ Sabidas: {{ knownCount() }}</span>
            <span class="stat-review">🔄 Repasar: {{ reviewCount() }}</span>
          </div>

          <div class="view-toggle">
            <button 
              type="button" 
              class="btn-toggle-view"
              [class.active]="viewMode() === 'deck'"
              (click)="viewMode.set('deck')"
            >
              🎴 Modo Mazo 3D
            </button>
            <button 
              type="button" 
              class="btn-toggle-view"
              [class.active]="viewMode() === 'grid'"
              (click)="viewMode.set('grid')"
            >
              📋 Ver Todas ({{ activeItems().length }})
            </button>
          </div>
        </div>

        <!-- PROGRESS BAR -->
        <div class="progress-track" *ngIf="viewMode() === 'deck'">
          <div class="progress-fill" [style.width.%]="progressPercent()"></div>
        </div>

        <!-- UTILITY ACTIONS BAR (Shuffle, Filter) -->
        <div class="utility-actions">
          <button type="button" class="btn-action-sm" (click)="shuffleCards()">
            🔀 Barajar Mazo
          </button>
          <button type="button" class="btn-action-sm" (click)="resetStudyStats()">
            ↺ Reiniciar Progreso
          </button>
          <span class="keyboard-hint"><b>Espacio</b>: Girar | <b>← / →</b>: Navegar</span>
        </div>
      </div>

      <!-- MODE 1: INTERACTIVE 3D FLIP CARD -->
      <ng-container *ngIf="viewMode() === 'deck'">
        <div class="card-3d-wrapper no-print" (click)="toggleFlip()" *ngIf="currentCard">
          <div class="card-3d" [class.flipped]="isFlipped()">
            <!-- Front Face -->
            <div class="card-face card-front">
              <div class="face-badge">PREGUNTA / CONCEPTO #{{ currentIndex() + 1 }}</div>
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
              
              <div class="face-sources" *ngIf="currentCard.fuentes && currentCard.fuentes.length > 0">
                <span class="source-chip">
                  📄 Cita Fuente [Pág. {{ currentCard.fuentes[0].pagina || 1 }}]
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Controls -->
        <div class="controls-row no-print" *ngIf="currentCard">
          <button class="btn-nav" (click)="prevCard()" [disabled]="currentIndex() === 0">
            ← Anterior
          </button>

          <div class="review-buttons" *ngIf="isFlipped()">
            <button class="btn-review" (click)="markReview()">🔄 Necesito Repasar</button>
            <button class="btn-known" (click)="markKnown()">✅ Lo Sabía</button>
          </div>

          <button class="btn-nav" (click)="nextCard()" [disabled]="currentIndex() === activeItems().length - 1">
            Siguiente →
          </button>
        </div>
      </ng-container>

      <!-- MODE 2: GRID / SCROLLABLE LIST FOR HIGH VOLUMES (80+ items) -->
      <div class="cards-grid-list no-print" *ngIf="viewMode() === 'grid'">
        <div class="grid-card glass-card" *ngFor="let card of activeItems(); let idx = index">
          <div class="grid-card-header">
            <span class="card-idx">#{{ idx + 1 }}</span>
            <span class="hint-inline" *ngIf="card.pista_didactica">💡 {{ card.pista_didactica }}</span>
          </div>
          <h4 class="card-q">{{ card.frente }}</h4>
          <p class="card-a">{{ card.dorso }}</p>
          <div class="card-source" *ngIf="card.fuentes && card.fuentes.length > 0">
            <span>📄 Fuente: Pág. {{ card.fuentes[0].pagina || 1 }}</span>
          </div>
        </div>
      </div>

      <!-- PRINT-ONLY DEDICATED FLASHCARDS LIST -->
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
      max-width: 840px;
      margin: 0 auto;
      padding: 0.5rem 0;
    }

    .study-bar {
      padding: 1.25rem;
      border-radius: 18px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
    }

    .bar-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
      margin-bottom: 0.85rem;
    }

    .card-counter {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .badge-num {
      font-size: 1.1rem;
      font-weight: 800;
      color: #EC4899;
      background: rgba(236, 72, 153, 0.12);
      padding: 0.25rem 0.65rem;
      border-radius: 8px;
    }

    .sub-counter {
      font-size: 0.88rem;
      font-weight: 700;
      color: var(--text-secondary);
    }

    .mode-stats {
      display: flex;
      gap: 1.25rem;
      font-size: 0.88rem;
      font-weight: 700;
    }
    .stat-known { color: #10B981; }
    .stat-review { color: #F59E0B; }

    .view-toggle {
      display: flex;
      gap: 0.35rem;
      background: var(--bg-app);
      padding: 0.25rem;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
    }

    .btn-toggle-view {
      padding: 0.35rem 0.75rem;
      border-radius: 8px;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
    }

    .btn-toggle-view.active {
      background: var(--bg-surface);
      color: var(--text-primary);
      box-shadow: var(--shadow-sm);
    }

    .progress-track {
      height: 6px;
      background: var(--bg-app);
      border-radius: 3px;
      overflow: hidden;
      margin-bottom: 0.85rem;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #EC4899 0%, #6366F1 100%);
      transition: width 0.3s ease-out;
    }

    .utility-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .btn-action-sm {
      padding: 0.35rem 0.75rem;
      border-radius: 8px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
    }

    .keyboard-hint {
      margin-left: auto;
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
      width: 100%;
      height: 100%;
      backface-visibility: hidden !important;
      border-radius: 20px;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-lg);
    }

    .card-front {
      transform: rotateY(0deg);
      border-top: 4px solid #EC4899;
    }

    .card-back {
      transform: rotateY(180deg);
      border-top: 4px solid #10B981;
    }

    .card-3d.flipped .card-front {
      opacity: 0;
      visibility: hidden;
    }

    .card-3d:not(.flipped) .card-back {
      opacity: 0;
      visibility: hidden;
    }

    .face-badge {
      font-size: 0.72rem;
      font-weight: 800;
      color: #EC4899;
      letter-spacing: 0.08em;
    }
    .back-badge { color: #10B981; }

    .face-content h3 {
      font-size: 1.4rem;
      line-height: 1.35;
      font-weight: 700;
      color: var(--text-primary);
    }

    .face-content p {
      font-size: 1.05rem;
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
      padding: 0.3rem 0.65rem;
      border-radius: 8px;
      background: rgba(34, 211, 238, 0.12);
      color: #0284C7;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .controls-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }

    .btn-nav {
      padding: 0.65rem 1.25rem;
      border-radius: 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-weight: 700;
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
      padding: 0.65rem 1.15rem;
      border-radius: 12px;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid #F59E0B;
      color: #D97706;
      font-weight: 700;
      cursor: pointer;
    }

    .btn-known {
      padding: 0.65rem 1.15rem;
      border-radius: 12px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10B981;
      color: #059669;
      font-weight: 700;
      cursor: pointer;
    }

    /* GRID LIST VIEW FOR HIGH VOLUMES */
    .cards-grid-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
    }

    .grid-card {
      padding: 1.5rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .grid-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .card-idx {
      font-size: 0.8rem;
      font-weight: 800;
      color: #EC4899;
      background: rgba(236, 72, 153, 0.12);
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
    }

    .hint-inline {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-style: italic;
    }

    .card-q {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-primary);
      line-height: 1.4;
      margin: 0;
    }

    .card-a {
      font-size: 0.92rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin: 0;
      background: var(--bg-app);
      padding: 0.85rem;
      border-radius: 10px;
    }

    .card-source {
      font-size: 0.78rem;
      color: #0284C7;
      font-weight: 600;
    }

    .print-only-list { display: none; }

    @media print {
      .no-print { display: none !important; }
      .print-only-list { display: block !important; }
    }
  `]
})
export class FlashcardsRendererComponent {
  @Input({ required: true }) items: FlashcardItem[] = [];

  viewMode = signal<'deck' | 'grid'>('deck');
  currentIndex = signal<number>(0);
  isFlipped = signal<boolean>(false);
  knownCount = signal<number>(0);
  reviewCount = signal<number>(0);
  shuffledItems = signal<FlashcardItem[] | null>(null);

  activeItems = computed(() => {
    return this.shuffledItems() || this.items || [];
  });

  progressPercent = computed(() => {
    const total = this.activeItems().length;
    if (total === 0) return 0;
    return Math.round(((this.currentIndex() + 1) / total) * 100);
  });

  get currentCard(): FlashcardItem | null {
    const list = this.activeItems();
    return list[this.currentIndex()] || null;
  }

  toggleFlip(): void {
    this.isFlipped.update(v => !v);
  }

  nextCard(): void {
    if (this.currentIndex() < this.activeItems().length - 1) {
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

  shuffleCards(): void {
    const array = [...(this.items || [])];
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    this.shuffledItems.set(array);
    this.currentIndex.set(0);
    this.isFlipped.set(false);
  }

  resetStudyStats(): void {
    this.shuffledItems.set(null);
    this.currentIndex.set(0);
    this.isFlipped.set(false);
    this.knownCount.set(0);
    this.reviewCount.set(0);
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent): void {
    if (this.viewMode() !== 'deck') return;
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
