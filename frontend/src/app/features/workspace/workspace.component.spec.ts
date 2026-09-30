import { ComponentFixture, TestBed } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { WorkspaceComponent } from './workspace.component';
import { NUEVAMENTE_API } from '../../core/api/nuevamente-api';
import { StateService } from '../../core/services/state.service';
import { ExportService } from '../../core/services/export.service';

describe('WorkspaceComponent', () => {
  let component: WorkspaceComponent;
  let fixture: ComponentFixture<WorkspaceComponent>;

  const mockApi = {
    adaptContent: () => of({
      metadatos: {
        perfil_aplicado: 'Desarrollador',
        formato_generado: 'Flashcards',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Tecnico',
        nivel_cantidad: 'Amplio',
        items_solicitados: 40,
        items_generados: 30,
        aviso_cantidad: 'Tu documento dio para 30 tarjetas. Con un documento más extenso podrás generar más.',
        tiempo_estimado_estudio_minutos: 15,
        conceptos_clave: ['A', 'B', 'C', 'D', 'E', 'F', 'G']
      },
      contenido_adaptado: {
        titulo: 'VCN en OCI',
        introduccion_contextualizada: 'Intro',
        items: Array(30).fill({ frente: 'F', dorso: 'D' })
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.95,
        claridad_pedagogica: 'Alta',
        observaciones: 'Fidelidad verificada'
      }
    }),
    parsePdf: () => of({ texto_extraido: 'Contenido extraido' })
  };

  const mockStateService = {
    addProjectFromResponse: jasmine.createSpy('addProjectFromResponse')
  };

  const mockExportService = {
    exportMarkdown: jasmine.createSpy('exportMarkdown'),
    exportPdfDidactico: jasmine.createSpy('exportPdfDidactico'),
    exportAnkiCsv: jasmine.createSpy('exportAnkiCsv')
  };

  const mockRouter = {
    navigate: jasmine.createSpy('navigate')
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkspaceComponent, ReactiveFormsModule],
      providers: [
        { provide: NUEVAMENTE_API, useValue: mockApi },
        { provide: StateService, useValue: mockStateService },
        { provide: ExportService, useValue: mockExportService },
        { provide: Router, useValue: mockRouter }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(WorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create WorkspaceComponent', () => {
    expect(component).toBeTruthy();
  });

  it('should update dynamic quantity hint text when selecting level', () => {
    component.selectNivelCantidad('Amplio');
    fixture.detectChanges();

    expect(component.currentQuantityHint()).toContain('≈ 40 tarjetas');
    expect(component.effectiveTargetCount()).toBe(40);
  });

  it('should detect quantity cap notice when generated < requested', () => {
    component.currentResponse.set({
      metadatos: {
        items_solicitados: 40,
        items_generados: 30,
        aviso_cantidad: 'Tu documento dio para 30 tarjetas. Con un documento más extenso podrás generar más.'
      }
    } as any);

    expect(component.hasQuantityCapNotice()).toBeTrue();
    expect(component.quantityCapNoticeText()).toContain('30 tarjetas');
  });

  it('should reset form and return to input view', () => {
    component.currentResponse.set({} as any);
    component.resetForm();

    expect(component.currentResponse()).toBeNull();
    expect(component.isPipelineRunning()).toBeFalse();
  });
});
