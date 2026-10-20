import { Component, Input, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QuizItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-quiz-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="quiz-container" *ngIf="items && items.length > 0">
      <!-- QUIZ HEADER TOP CONTROLS & PROGRESS -->
      <div class="quiz-top-bar glass-card" *ngIf="!isCompleted()">
        <div class="bar-info">
          <div class="stepper-badge">
            Pregunta <strong>{{ currentIndex() + 1 }}</strong> de <strong>{{ items.length }}</strong>
          </div>
          <span class="score-live">Puntaje actual: {{ score() }} / {{ items.length }}</span>
        </div>

        <div class="progress-track">
          <div class="progress-fill" [style.width.%]="((currentIndex() + 1) / items.length) * 100"></div>
        </div>

        <div class="mode-toggle-row">
          <button 
            type="button" 
            class="btn-mode"
            [class.active]="mode() === 'stepper'"
            (click)="mode.set('stepper')"
          >
            🎯 Paso a Paso
          </button>
          <button 
            type="button" 
            class="btn-mode"
            [class.active]="mode() === 'all'"
            (click)="mode.set('all')"
          >
            📋 Ver Quiz Completo ({{ items.length }})
          </button>
        </div>
      </div>

      <!-- STEPPER MODE (1 Question at a time) -->
      <div class="glass-card quiz-card" *ngIf="mode() === 'stepper' && !isCompleted()">
        <div class="question-header">
          <div class="q-header-top">
            <span class="q-badge">PREGUNTA #{{ currentIndex() + 1 }}</span>
            <div class="item-badges-cluster">
              <span 
                class="badge-origin"
                [class.is-verified]="getItemEvaluation(currentIndex()).statusKey === 'verified'"
                [class.is-observed]="getItemEvaluation(currentIndex()).statusKey === 'observed'"
                [class.is-unverified]="getItemEvaluation(currentIndex()).statusKey === 'unverified'"
                [class.is-fallback]="getItemEvaluation(currentIndex()).statusKey === 'fallback'"
                [title]="getItemEvaluation(currentIndex()).issues.length > 0 ? getItemEvaluation(currentIndex()).issues[0] : (getItemEvaluation(currentIndex()).origen_verificado ? 'Cita verificada con el documento original' : 'Cita con observaciones o no confirmada')"
              >
                {{ getItemEvaluation(currentIndex()).statusLabel }}
              </span>
              <span class="badge-clarity-sm" [title]="'Claridad pedagógica: ' + getItemEvaluation(currentIndex()).claridad">
                Claridad pedagógica: {{ getItemEvaluation(currentIndex()).claridad }}
              </span>
            </div>
          </div>
          <h3>{{ currentQuestion.pregunta }}</h3>
        </div>

        <div class="options-list">
          <button 
            *ngFor="let opt of currentQuestion.opciones; let idx = index" 
            class="option-item"
            [class.selected]="selectedOptionIndex() === idx"
            [class.correct]="hasSubmitted() && isOptionCorrect(opt)"
            [class.wrong]="hasSubmitted() && selectedOptionIndex() === idx && !isOptionCorrect(opt)"
            [disabled]="hasSubmitted()"
            (click)="selectOption(idx)"
          >
            <span class="option-letter">{{ getOptionLetter(idx) }}</span>
            <span class="option-text">{{ opt }}</span>
            <span class="option-icon" *ngIf="hasSubmitted()">
              {{ isOptionCorrect(opt) ? 'Correcto' : (selectedOptionIndex() === idx ? 'Incorrecto' : '') }}
            </span>
          </button>
        </div>

        <!-- Feedback & Pedagogical Justification Card -->
        <div class="justification-box" *ngIf="hasSubmitted()">
          <div class="justification-header">
            <span class="badge-pedagogic">EXPLICACIÓN PEDAGÓGICA</span>
          </div>
          <p>{{ currentQuestion.justificacion_didactica || currentQuestion.justificacion }}</p>
          <div class="source-tag" *ngIf="currentQuestion.fuentes && currentQuestion.fuentes.length > 0" [title]="formatSourceTooltip(currentQuestion.fuentes[0])">
            Fuente: {{ formatSourceLabel(currentQuestion.fuentes[0]) }}
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="quiz-footer">
          <button 
            *ngIf="!hasSubmitted()" 
            class="btn-submit-answer"
            [disabled]="selectedOptionIndex() === null"
            (click)="submitAnswer()"
          >
            Comprobar Respuesta →
          </button>

          <button 
            *ngIf="hasSubmitted()" 
            class="btn-next-question"
            (click)="nextQuestion()"
          >
            {{ currentIndex() < items.length - 1 ? 'Siguiente Pregunta →' : 'Ver Resultado Final' }}
          </button>
        </div>
      </div>

      <!-- ALL QUESTIONS MODE (Full List View for Review) -->
      <div class="all-questions-list" *ngIf="mode() === 'all' && !isCompleted()">
        <div class="quiz-card glass-card q-block" *ngFor="let q of items; let idx = index">
          <div class="question-header">
            <div class="q-header-top">
              <span class="q-badge">PREGUNTA #{{ idx + 1 }}</span>
              <div class="item-badges-cluster">
                <span 
                  class="badge-origin"
                  [class.is-verified]="getItemEvaluation(idx).statusKey === 'verified'"
                  [class.is-observed]="getItemEvaluation(idx).statusKey === 'observed'"
                  [class.is-unverified]="getItemEvaluation(idx).statusKey === 'unverified'"
                  [class.is-fallback]="getItemEvaluation(idx).statusKey === 'fallback'"
                  [title]="getItemEvaluation(idx).issues.length > 0 ? getItemEvaluation(idx).issues[0] : (getItemEvaluation(idx).origen_verificado ? 'Cita verificada con el documento original' : 'Cita no confirmada contra el documento')"
                >
                  {{ getItemEvaluation(idx).statusLabel }}
                </span>
                <span class="badge-clarity-sm">
                  Claridad pedagógica: {{ getItemEvaluation(idx).claridad }}
                </span>
              </div>
            </div>
            <h3>{{ q.pregunta }}</h3>
          </div>
          <div class="options-list">
            <div 
              *ngFor="let opt of q.opciones; let oIdx = index"
              class="option-item"
              [class.correct]="isOptionCorrectInQuestion(q, opt)"
            >
              <span class="option-letter">{{ getOptionLetter(oIdx) }}</span>
              <span class="option-text">{{ opt }}</span>
              <span class="option-icon" *ngIf="isOptionCorrectInQuestion(q, opt)">Correcto</span>
            </div>
          </div>
          <div class="justification-box">
            <span class="badge-pedagogic">JUSTIFICACIÓN DE LA RESPUESTA:</span>
            <p>{{ q.justificacion_didactica || q.justificacion }}</p>
          </div>
        </div>
      </div>

      <!-- FINAL SCORE SCREEN -->
      <div class="glass-card quiz-card score-screen" *ngIf="isCompleted()">
        <div class="score-badge">🏆 EVALUACIÓN COMPLETADA</div>
        <h2>Puntaje Obtenido: {{ score() }} / {{ items.length }}</h2>
        <p class="score-pct">{{ scorePercent() }}% de aciertos</p>
        
        <p class="score-feedback">
          {{ scorePercent() >= 70 ? '¡Excelente trabajo! Has demostrado alto dominio sobre el documento.' : 'Buen intento. Te recomendamos repasar las tarjetas o secciones con menor puntaje.' }}
        </p>

        <div class="score-actions">
          <button class="btn-restart" (click)="restartQuiz()">🔄 Reiniciar Quiz</button>
          <button class="btn-review-errors" *ngIf="wrongQuestions().length > 0" (click)="reviewWrongQuestions()">
            ⚠️ Repasar Preguntas Falladas ({{ wrongQuestions().length }})
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .quiz-container {
      max-width: 840px;
      margin: 0 auto;
      padding: 0.5rem 0;
    }

    .quiz-top-bar {
      padding: 1.25rem;
      border-radius: 18px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
    }

    .bar-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }

    .stepper-badge {
      font-size: 0.95rem;
      color: var(--text-primary);
    }

    .score-live {
      font-size: 0.88rem;
      font-weight: 700;
      color: #6366F1;
    }

    .progress-track {
      height: 6px;
      background: var(--bg-app);
      border-radius: 3px;
      overflow: hidden;
      margin-bottom: 1rem;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #6366F1 0%, #EC4899 100%);
      transition: width 0.3s ease;
    }

    .mode-toggle-row {
      display: flex;
      gap: 0.5rem;
    }

    .btn-mode {
      padding: 0.35rem 0.75rem;
      border-radius: 8px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
    }

    .btn-mode.active {
      background: rgba(99, 102, 241, 0.12);
      border-color: #6366F1;
      color: #6366F1;
    }

    .quiz-card {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .q-block {
      margin-bottom: 1.5rem;
    }

    .question-header {
      margin-bottom: 1.5rem;
    }

    .q-header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }

    .item-badges-cluster {
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .badge-origin {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      cursor: help;
    }

    .badge-origin.is-verified {
      background: rgba(16, 185, 129, 0.12);
      color: #047857;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-origin.is-observed {
      background: rgba(245, 158, 11, 0.15);
      color: #b45309;
      border: 1px solid rgba(245, 158, 11, 0.4);
    }

    .badge-origin.is-unverified {
      background: rgba(239, 68, 68, 0.12);
      color: #dc2626;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .badge-origin.is-fallback {
      background: rgba(107, 114, 128, 0.15);
      color: #4b5563;
      border: 1px solid rgba(107, 114, 128, 0.3);
    }

    .badge-clarity-sm {
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 6px;
      background: var(--bg-app);
      color: var(--text-secondary);
      border: 1px solid var(--border-subtle);
      cursor: help;
    }

    .q-badge {
      font-size: 0.75rem;
      font-weight: 800;
      color: #6366F1;
      background: rgba(99, 102, 241, 0.12);
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      display: inline-block;
    }

    .question-header h3 {
      font-size: 1.35rem;
      line-height: 1.4;
      color: var(--text-primary);
      margin: 0;
    }

    .options-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .option-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-radius: 12px;
      background: var(--bg-app);
      border: 1.5px solid var(--border-subtle);
      color: var(--text-primary);
      text-align: left;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.2s;
    }

    .option-item:hover:not(:disabled) {
      border-color: #6366F1;
      background: rgba(99, 102, 241, 0.05);
    }

    .option-item.selected {
      border-color: #6366F1;
      background: rgba(99, 102, 241, 0.1);
      font-weight: 600;
    }

    .option-item.correct {
      border-color: #10B981;
      background: rgba(16, 185, 129, 0.12);
      color: #059669;
      font-weight: 700;
    }

    .option-item.wrong {
      border-color: #EF4444;
      background: rgba(239, 68, 68, 0.12);
      color: #DC2626;
    }

    .option-letter {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.85rem;
      flex-shrink: 0;
    }

    .option-text { flex: 1; }

    .justification-box {
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
    }

    .badge-pedagogic {
      font-size: 0.75rem;
      font-weight: 800;
      color: #6366F1;
    }

    .justification-box p {
      margin: 0.4rem 0 0 0;
      font-size: 0.92rem;
      color: var(--text-primary);
      line-height: 1.5;
    }

    .source-tag {
      font-size: 0.78rem;
      color: #0284C7;
      font-weight: 600;
      margin-top: 0.5rem;
    }

    .quiz-footer {
      display: flex;
      justify-content: flex-end;
    }

    .btn-submit-answer, .btn-next-question, .btn-restart {
      padding: 0.75rem 1.5rem;
      border-radius: 12px;
      background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
      border: none;
      color: #FFFFFF;
      font-weight: 800;
      font-size: 0.95rem;
      cursor: pointer;
    }

    .btn-submit-answer:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .score-screen {
      text-align: center;
      padding: 3rem 2rem;
    }

    .score-badge {
      font-size: 0.8rem;
      font-weight: 800;
      color: #6366F1;
      margin-bottom: 1rem;
    }

    .score-pct {
      font-size: 2.5rem;
      font-weight: 800;
      color: #10B981;
      margin: 0.5rem 0 1rem;
    }

    .score-feedback {
      font-size: 1rem;
      color: var(--text-secondary);
      margin-bottom: 1.5rem;
    }

    .score-actions {
      display: flex;
      justify-content: center;
      gap: 1rem;
    }

    .btn-review-errors {
      padding: 0.75rem 1.5rem;
      border-radius: 12px;
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid #F59E0B;
      color: #D97706;
      font-weight: 700;
      cursor: pointer;
    }
  `]
})
export class QuizRendererComponent {
  @Input({ required: true }) items: QuizItem[] = [];
  @Input() evaluacion?: any;

  mode = signal<'stepper' | 'all'>('stepper');
  currentIndex = signal<number>(0);
  selectedOptionIndex = signal<number | null>(null);
  hasSubmitted = signal<boolean>(false);
  score = signal<number>(0);
  isCompleted = signal<boolean>(false);
  wrongQuestions = signal<QuizItem[]>([]);

  getItemEvaluation(idx: number): {
    statusKey: 'verified' | 'observed' | 'unverified' | 'fallback';
    statusLabel: string;
    origen_verificado: boolean;
    claridad: string;
    issues: string[];
  } {
    const item = (this.items || [])[idx];
    const perItem = this.evaluacion?.per_item || this.evaluacion?.por_item;

    let entry: any = null;
    if (Array.isArray(perItem)) {
      if (item?._gid) {
        entry = perItem.find((p: any) => p._gid === item._gid);
      }
      if (!entry && perItem[idx]) {
        entry = perItem[idx];
      }
    }

    const isFallback = Boolean(item?.es_fallback || entry?.es_fallback);
    const verificadoLexico = Boolean(
      entry?.verificado_lexico !== undefined
        ? entry.verificado_lexico
        : (item?.fuentes?.some((f: any) => f.verificado !== false) ?? false)
    );
    const verificadoRevisor = Boolean(
      entry?.verificado_revisor !== undefined
        ? entry.verificado_revisor
        : (entry ? (entry.origen_verificado ?? true) : true)
    );
    const origenVerificado = Boolean(
      entry?.origen_verificado !== undefined
        ? entry.origen_verificado
        : (verificadoLexico && verificadoRevisor)
    );

    let statusKey: 'verified' | 'observed' | 'unverified' | 'fallback' = 'unverified';
    let statusLabel = 'Sin verificar';

    if (isFallback) {
      statusKey = 'fallback';
      statusLabel = 'Fallback';
    } else if (origenVerificado) {
      statusKey = 'verified';
      statusLabel = 'Verificado';
    } else if (verificadoLexico && !verificadoRevisor) {
      statusKey = 'observed';
      statusLabel = 'Revisado con observaciones';
    } else {
      statusKey = 'unverified';
      statusLabel = 'Sin verificar';
    }

    const claridad = entry?.claridad || this.evaluacion?.claridad_pedagogica || 'Alta';
    const issues = entry?.issues || (origenVerificado ? [] : ['Cita con observaciones o no confirmada contra el documento']);

    return {
      statusKey,
      statusLabel,
      origen_verificado: origenVerificado,
      claridad,
      issues
    };
  }

  get currentQuestion(): QuizItem {
    return this.items[this.currentIndex()] || { pregunta: '', opciones: [], respuesta_correcta: '', justificacion: '' };
  }

  scorePercent = computed(() => {
    if (!this.items.length) return 0;
    return Math.round((this.score() / this.items.length) * 100);
  });

  getOptionLetter(idx: number): string {
    return String.fromCharCode(65 + idx);
  }

  selectOption(idx: number): void {
    if (!this.hasSubmitted()) {
      this.selectedOptionIndex.set(idx);
    }
  }

  isOptionCorrect(option: string): boolean {
    return option === this.currentQuestion.respuesta_correcta;
  }

  isOptionCorrectInQuestion(question: QuizItem, option: string): boolean {
    return option === question.respuesta_correcta;
  }

  submitAnswer(): void {
    if (this.selectedOptionIndex() === null) return;
    this.hasSubmitted.set(true);

    const selectedOpt = this.currentQuestion.opciones[this.selectedOptionIndex()!];
    if (this.isOptionCorrect(selectedOpt)) {
      this.score.update(s => s + 1);
    } else {
      this.wrongQuestions.update(list => [...list, this.currentQuestion]);
    }
  }

  nextQuestion(): void {
    if (this.currentIndex() < this.items.length - 1) {
      this.currentIndex.update(i => i + 1);
      this.selectedOptionIndex.set(null);
      this.hasSubmitted.set(false);
    } else {
      this.isCompleted.set(true);
    }
  }

  reviewWrongQuestions(): void {
    if (this.wrongQuestions().length > 0) {
      this.mode.set('all');
      this.isCompleted.set(false);
    }
  }

  restartQuiz(): void {
    this.currentIndex.set(0);
    this.selectedOptionIndex.set(null);
    this.hasSubmitted.set(false);
    this.score.set(0);
    this.wrongQuestions.set([]);
    this.isCompleted.set(false);
  }

  formatSourceLabel(fuente?: any): string {
    if (!fuente) return 'Cita fuente';
    if (fuente.breadcrumb && fuente.breadcrumb !== 'N/A') {
      const pageStr = (fuente.pagina && fuente.pagina > 0) ? ` · Pág. ${fuente.pagina}` : '';
      return `${fuente.breadcrumb}${pageStr}`;
    }
    if (fuente.seccion) {
      const pageStr = (fuente.pagina && fuente.pagina > 0) ? ` · Pág. ${fuente.pagina}` : '';
      return `${fuente.seccion}${pageStr}`;
    }
    if (fuente.pagina && fuente.pagina > 0) {
      return `Pág. ${fuente.pagina}`;
    }
    return 'Documento base';
  }

  formatSourceTooltip(fuente?: any): string {
    if (!fuente) return '';
    const parts: string[] = [];
    if (fuente.breadcrumb) parts.push(`Ruta: ${fuente.breadcrumb}`);
    if (fuente.seccion) parts.push(`Sección: ${fuente.seccion}`);
    if (fuente.pagina && fuente.pagina > 0) parts.push(`Página: ${fuente.pagina}`);
    if (fuente.extracto) parts.push(`«${fuente.extracto.trim().slice(0, 150)}...»`);
    return parts.join(' | ');
  }
}
