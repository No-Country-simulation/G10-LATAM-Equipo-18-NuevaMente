import { ComponentFixture, TestBed } from '@angular/core/testing';
import { GenerationLoaderComponent } from './generation-loader.component';
import { Component } from '@angular/core';

describe('GenerationLoaderComponent', () => {
  let component: GenerationLoaderComponent;
  let fixture: ComponentFixture<GenerationLoaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GenerationLoaderComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(GenerationLoaderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render main title and default elements in non-compact mode', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.loader-title')?.textContent).toContain('Creando tu contenido educativo');
    expect(compiled.querySelector('.brand-tag')?.textContent).toContain('Procesamiento RAG de Alta Fidelidad');
    expect(compiled.querySelector('.btn-cancel-gen')).toBeTruthy();
  });

  it('should display parameters context chips when params input is provided', () => {
    component.params = {
      perfil: 'Desarrollador',
      formato: 'Quiz',
      nicho: 'Fintech',
      nivel: 'Tecnico'
    };
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const chips = compiled.querySelectorAll('.param-chip');
    expect(chips.length).toBe(4);
    expect(chips[0].textContent).toContain('Desarrollador');
    expect(chips[1].textContent).toContain('Quiz');
    expect(chips[2].textContent).toContain('Fintech');
    expect(chips[3].textContent).toContain('Tecnico');
  });

  it('should toggle technical details panel when toggle button is clicked', () => {
    expect(component.isDetailsOpen()).toBeFalse();
    
    component.toggleDetails();
    fixture.detectChanges();
    expect(component.isDetailsOpen()).toBeTrue();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.technical-details-drawer')).toBeTruthy();
  });

  it('should emit cancel event when Cancel button is clicked', () => {
    spyOn(component.cancel, 'emit');
    const compiled = fixture.nativeElement as HTMLElement;
    const cancelBtn = compiled.querySelector('.btn-cancel-gen') as HTMLButtonElement;
    
    cancelBtn.click();
    expect(component.cancel.emit).toHaveBeenCalled();
  });

  it('should enter error state when triggerError is called', () => {
    component.triggerError('Error de servidor simulado');
    fixture.detectChanges();

    expect(component.isError()).toBeTrue();
    expect(component.errorMessage()).toBe('Error de servidor simulado');

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.error-state-box')).toBeTruthy();
    expect(compiled.querySelector('.error-desc')?.textContent).toContain('Error de servidor simulado');
  });

  it('should emit retry event when Reintentar button is clicked in error state', () => {
    spyOn(component.retry, 'emit');
    component.triggerError('Error de servidor simulado');
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const retryBtn = compiled.querySelector('.btn-retry') as HTMLButtonElement;
    
    retryBtn.click();
    expect(component.retry.emit).toHaveBeenCalled();
    expect(component.isError()).toBeFalse();
  });

  it('should render compact mode when compact is true', () => {
    component.compact = true;
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.loader-compact-box')).toBeTruthy();
    expect(compiled.querySelector('.generation-loader-container')).toBeNull();
  });
});
