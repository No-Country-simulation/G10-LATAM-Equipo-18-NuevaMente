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
        formato_generado: 'Tutorial',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Tecnico',
        tiempo_estimado_estudio_minutos: 4.5,
        conceptos_clave: ['A', 'B', 'C', 'D', 'E', 'F', 'G']
      },
      contenido_adaptado: {
        titulo: 'VCN en OCI',
        introduccion_contextualizada: 'Intro',
        items: []
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

  it('should format study time correctly', () => {
    component.currentResponse.set({
      metadatos: { tiempo_estimado_estudio_minutos: 4.5 }
    } as any);
    expect(component.formattedStudyTime()).toBe('⏱ 4 min 30 s');
  });

  it('should toggle concept cloud expansion', () => {
    component.currentResponse.set({
      metadatos: { conceptos_clave: ['1', '2', '3', '4', '5', '6', '7', '8'] }
    } as any);
    expect(component.visibleConcepts().length).toBe(6);
    expect(component.hiddenConceptsCount()).toBe(2);

    component.isConceptsExpanded.set(true);
    expect(component.visibleConcepts().length).toBe(8);
  });

  it('should reset form and return to input view', () => {
    component.currentResponse.set({} as any);
    component.resetForm();

    expect(component.currentResponse()).toBeNull();
    expect(component.isPipelineRunning()).toBeFalse();
  });
});
