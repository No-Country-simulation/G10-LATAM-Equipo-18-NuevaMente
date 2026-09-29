import { Component, Input } from '@angular/core';
import { QuizItem } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-interactive-quiz',
  template: `
    <div class="quiz-section">
      <div class="section-header">
        <h3>❓ Quiz Didáctico Interactivo ({{ quizzes.length }})</h3>
        <span class="subtext">Responde a las preguntas para evaluar tu comprensión.</span>
      </div>

      <div class="quizzes-list">
        <div *ngFor="let q of quizzes; let qIdx = index" class="quiz-card">
          <div class="quiz-question-header">
            <span class="question-number">Pregunta {{ qIdx + 1 }}</span>
            <h4>{{ q.pregunta }}</h4>
          </div>

          <div class="options-grid">
            <button 
              *ngFor="let opt of q.opciones; let oIdx = index" 
              class="option-button"
              [ngClass]="{
                'selected-correct': selectedAnswers[qIdx] === opt && opt === q.respuesta_correcta,
                'selected-incorrect': selectedAnswers[qIdx] === opt && opt !== q.respuesta_correcta,
                'highlight-correct': selectedAnswers[qIdx] && opt === q.respuesta_correcta
              }"
              (click)="selectAnswer(qIdx, opt)"
            >
              <span class="option-prefix">{{ getLetter(oIdx) }}.</span>
              <span class="option-text">{{ opt }}</span>
            </button>
          </div>

          <!-- Feedback Box -->
          <div *ngIf="selectedAnswers[qIdx]" class="feedback-box">
            <div class="feedback-result">
              <span *ngIf="selectedAnswers[qIdx] === q.respuesta_correcta" class="feedback-badge correct">
                ✓ ¡Correcto!
              </span>
              <span *ngIf="selectedAnswers[qIdx] !== q.respuesta_correcta" class="feedback-badge incorrect">
                ✕ Respuesta incorrecta
              </span>
            </div>
            <div class="justification-text">
              💡 <strong>Justificación didáctica:</strong> {{ q.justificacion_didactica }}
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .quiz-section {
      margin-top: 2rem;
      margin-bottom: 2rem;
    }
    .section-header h3 {
      font-size: 1.25rem;
      font-weight: 800;
      color: #0f172a;
    }
    .subtext {
      font-size: 0.85rem;
      color: #64748b;
    }

    .quizzes-list {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      margin-top: 1.25rem;
    }

    .quiz-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    .quiz-question-header {
      margin-bottom: 1.25rem;
    }
    .question-number {
      font-size: 0.75rem;
      font-weight: 800;
      color: #3b82f6;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .quiz-question-header h4 {
      font-size: 1.1rem;
      font-weight: 700;
      color: #0f172a;
      margin-top: 0.25rem;
    }

    .options-grid {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .option-button {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.85rem 1.25rem;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      text-align: left;
      font-size: 0.92rem;
      color: #334155;
      cursor: pointer;
      transition: all 0.2s;
    }
    .option-button:hover {
      border-color: #3b82f6;
      background: #eff6ff;
    }
    .option-prefix {
      font-weight: 800;
      color: #64748b;
    }
    .option-text {
      flex: 1;
    }

    .option-button.selected-correct, .option-button.highlight-correct {
      background: #dcfce7 !important;
      border-color: #22c55e !important;
      color: #15803d !important;
      font-weight: 700;
    }
    .option-button.selected-incorrect {
      background: #fee2e2 !important;
      border-color: #ef4444 !important;
      color: #b91c1c !important;
    }

    .feedback-box {
      margin-top: 1.25rem;
      padding: 1rem 1.25rem;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      border-left: 4px solid #3b82f6;
    }
    .feedback-badge {
      font-size: 0.85rem;
      font-weight: 800;
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      display: inline-block;
      margin-bottom: 0.5rem;
    }
    .feedback-badge.correct {
      background: #dcfce7;
      color: #15803d;
    }
    .feedback-badge.incorrect {
      background: #fee2e2;
      color: #b91c1c;
    }
    .justification-text {
      font-size: 0.88rem;
      color: #334155;
      line-height: 1.5;
    }
  `]
})
export class InteractiveQuizComponent {
  @Input() quizzes: QuizItem[] = [];

  selectedAnswers: { [key: number]: string } = {};

  selectAnswer(quizIndex: number, option: string): void {
    this.selectedAnswers[quizIndex] = option;
  }

  getLetter(index: number): string {
    return String.fromCharCode(65 + index);
  }
}
