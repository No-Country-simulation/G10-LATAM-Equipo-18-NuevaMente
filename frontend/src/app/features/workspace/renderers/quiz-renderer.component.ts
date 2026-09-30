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
          <span class="q-badge">PREGUNTA #{{ currentIndex() + 1 }}</span>
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
              {{ isOptionCorrect(opt) ? '✅' : (selectedOptionIndex() === idx ? '❌' : '') }}
            </span>
          </button>
        </div>

        <!-- Feedback & Pedagogical Justification Card -->
        <div class="justification-box" *ngIf="hasSubmitted()">
          <div class="justification-header">
            <span class="badge-pedagogic">💡 EXPLICACIÓN PEDAGÓGICA</span>
          </div>
          <p>{{ currentQuestion.justificacion_didactica || currentQuestion.justificacion }}</p>
          <div class="source-tag" *ngIf="currentQuestion.fuentes && currentQuestion.fuentes.length > 0">
            📄 Cita Fuente: Pág. {{ currentQuestion.fuentes[0].pagina || 1 }}
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
            {{ currentIndex() < items.length - 1 ? 'Siguiente Pregunta →' : 'Ver Resultado Final 🏆' }}
          </button>
        </div>
      </div>

      <!-- ALL QUESTIONS MODE (Full List View for Review) -->
      <div class="all-questions-list" *ngIf="mode() === 'all' && !isCompleted()">
        <div class="quiz-card glass-card q-block" *ngFor="let q of items; let idx = index">
          <div class="question-header">
            <span class="q-badge">PREGUNTA #{{ idx + 1 }}</span>
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
              <span class="option-icon" *ngIf="isOptionCorrectInQuestion(q, opt)">✅</span>
            </div>
          </div>
          <div class="justification-box">
            <span class="badge-pedagogic">💡 JUSTIFICACIÓN DE LA RESPUESTA:</span>
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

    .q-badge {
      font-size: 0.75rem;
      font-weight: 800;
      color: #6366F1;
      background: rgba(99, 102, 241, 0.12);
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      display: inline-block;
      margin-bottom: 0.5rem;
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

  mode = signal<'stepper' | 'all'>('stepper');
  currentIndex = signal<number>(0);
  selectedOptionIndex = signal<number | null>(null);
  hasSubmitted = signal<boolean>(false);
  score = signal<number>(0);
  isCompleted = signal<boolean>(false);
  wrongQuestions = signal<QuizItem[]>([]);

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
}
