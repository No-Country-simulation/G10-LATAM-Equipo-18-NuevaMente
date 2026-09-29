import { ComponentFixture, TestBed } from '@angular/core';
import { QuizRendererComponent } from './quiz-renderer.component';
import { QuizItem } from '../../../core/models/adaptation.model';

describe('QuizRendererComponent', () => {
  let component: QuizRendererComponent;
  let fixture: ComponentFixture<QuizRendererComponent>;

  const mockQuestions: QuizItem[] = [
    {
      pregunta: '¿Dónde colocar la BD?',
      opciones: ['Subred Pública', 'Subred Privada con NSG'],
      respuesta_correcta: 'Subred Privada con NSG',
      justificacion: 'Aislamiento estricto de red.'
    }
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QuizRendererComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(QuizRendererComponent);
    component = fixture.componentInstance;
    component.items = mockQuestions;
    fixture.detectChanges();
  });

  it('should initialize quiz at question 0', () => {
    expect(component.currentIndex()).toBe(0);
    expect(component.score()).toBe(0);
  });

  it('should evaluate correct answer and increment score', () => {
    component.selectOption(1); // 'Subred Privada con NSG'
    component.submitAnswer();
    expect(component.hasSubmitted()).toBeTrue();
    expect(component.score()).toBe(1);
  });
});
