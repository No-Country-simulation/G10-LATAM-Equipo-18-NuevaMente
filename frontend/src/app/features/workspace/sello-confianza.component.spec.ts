import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SelloConfianzaComponent } from './sello-confianza.component';
import { EvaluacionCalidad } from '../../core/models/adaptation.model';

describe('SelloConfianzaComponent', () => {
  let component: SelloConfianzaComponent;
  let fixture: ComponentFixture<SelloConfianzaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelloConfianzaComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(SelloConfianzaComponent);
    component = fixture.componentInstance;
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should calculate score ratio and percentage correctly', () => {
    const mockEvaluacion: EvaluacionCalidad = {
      anclaje_fuente_score: 0.92,
      claridad_pedagogica: 'Alta',
      observaciones: 'Excelente alineación con la fuente.'
    };
    fixture.componentRef.setInput('evaluacion', mockEvaluacion);
    fixture.detectChanges();

    expect(component.scoreRatio()).toBe(0.92);
    expect(component.scorePercent()).toBe(92);
    expect(component.threshold().label).toBe('Excelente');
    expect(component.threshold().colorClass).toBe('green');
  });

  it('should return fallback state when evaluacion is null', () => {
    fixture.componentRef.setInput('evaluacion', null);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.fallback-view')).toBeTruthy();
    expect(compiled.textContent).toContain('Verificación no disponible temporalmente');
  });

  it('should toggle explanation drawer on button click', () => {
    const mockEvaluacion: EvaluacionCalidad = {
      anclaje_fuente_score: 0.85,
      claridad_pedagogica: 'Media',
      observaciones: 'Notas de prueba.'
    };
    fixture.componentRef.setInput('evaluacion', mockEvaluacion);
    fixture.detectChanges();

    expect(component.isExpanded()).toBeFalse();
    component.isExpanded.set(true);
    fixture.detectChanges();

    expect(component.isExpanded()).toBeTrue();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.explain-drawer')).toBeTruthy();
  });
});
