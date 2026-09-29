import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QuizItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-quiz-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="quiz-container" *ngIf="items && items.length > 0">
      <!-- Quiz Header Progress -->
      <div class="quiz-progress-bar" *ngIf="!isCompleted()">
        <div class="progress-info">
          <span>Pregunta {{ currentIndex() + 1 }} de {{ items.length }}</span>
          <span class="score-live">Score actual: {{ score() }} / {{ items.length }}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" [style.width.%]="((currentIndex() + 1) / items.length) * 100"></div>
        </div>
      </div>

      <!-- Active Question Card -->
      <div class="glass-card quiz-card" *ngIf="!isCompleted()">
        <div class="question-title">
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
          <p>{{ currentQuestion.justificacion }}</p>
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

      <!-- FINAL SCORE SCREEN -->
      <div class="glass-card quiz-card score-screen" *ngIf="isCompleted()">
        <div class="score-badge">🏆 EVALUACIÓN COMPLETADA</div>
        <h2>Puntaje Obtención: {{ score() }} / {{ items.length }}</h2>
        <p class="score-pct">{{ (score() / items.length) * 100 | number:'1.0-0' }}% de aciertos</p>
        
        <p class="score-feedback">
          {{ (score() / items.length) >= 0.7 ? '¡Excelente trabajo! Has demostrado dominio de la materia.' : 'Buen intento. Te recomendamos repasar las fuentes RAG.' }}
        </p>

        <button class="btn-restart" (click)="restartQuiz()">🔄 Reiniciar Quiz</button>
      </div>
    </div>
  `,
  styles: [`
    .quiz-container {
      max-width: 720px;
      margin: 0 auto;
      padding: 1rem 0;
    }

    .quiz-progress-bar {
      margin-bottom: 1.5rem;
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 0.5rem;
    }

    .bar-track {
      height: 8px;
      background: var(--slate-200);
      border-radius: 4px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #8B5CF6, #3B82F6);
      transition: width 0.3s ease;
    }

    .quiz-card {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .question-title h3 {
      font-size: 1.35rem;
      line-height: 1.4;
      margin-bottom: 1.5rem;
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
      border-color: #8B5CF6;
      background: rgba(139, 92, 246, 0.05);
    }

    .option-item.selected {
      border-color: #8B5CF6;
      background: rgba(139, 92, 246, 0.1);
      font-weight: 600;
    }

    .option-item.correct {
      border-color: #10B981;
      background: rgba(16, 185, 129, 0.12);
      color: #065F46;
      font-weight: 700;
    }

    .option-item.wrong {
      border-color: #EF4444;
      background: rgba(239, 68, 68, 0.12);
      color: #991B1B;
    }

    .option-letter {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--slate-200);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.85rem;
      flex-shrink: 0;
    }

    .option-text {
      flex: 1;
    }

    .justification-box {
      background: rgba(139, 92, 246, 0.08);
      border: 1px solid rgba(139, 92, 246, 0.25);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
    }

    .badge-pedagogic {
      font-size: 0.75rem;
      font-weight: 800;
      color: #7C3AED;
      letter-spacing: 0.05em;
    }

    .justification-box p {
      margin-top: 0.4rem;
      font-size: 0.92rem;
      color: var(--text-primary);
      line-height: 1.5;
    }

    .quiz-footer {
      display: flex;
      justify-content: flex-end;
    }

    .btn-submit-answer, .btn-next-question, .btn-restart {
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
      border: none;
      color: #FFFFFF;
      font-weight: 700;
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
      color: #8B5CF6;
      margin-bottom: 1rem;
    }

    .score-pct {
      font-size: 2.5rem;
      font-weight: 800;
      color: #10B981;
      margin: 0.5rem 0 1rem;
    }
  `]
})
export class QuizRendererComponent {
  @Input({ required: true }) items: QuizItem[] = [];

  currentIndex = signal<number>(0);
  selectedOptionIndex = signal<number | null>(null);
  hasSubmitted = signal<boolean>(false);
  score = signal<number>(0);
  isCompleted = signal<boolean>(false);

  get currentQuestion(): QuizItem {
    return this.items[this.currentIndex()] || { pregunta: '', opciones: [], respuesta_correcta: '', justificacion: '' };
  }

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

  submitAnswer(): void {
    if (this.selectedOptionIndex() === null) return;
    this.hasSubmitted.set(true);

    const selectedOpt = this.currentQuestion.opciones[this.selectedOptionIndex()!];
    if (this.isOptionCorrect(selectedOpt)) {
      this.score.update(s => s + 1);
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

  restartQuiz(): void {
    this.currentIndex.set(0);
    this.selectedOptionIndex.set(null);
    this.hasSubmitted.set(false);
    this.score.set(0);
    this.isCompleted.set(false);
  }
}
