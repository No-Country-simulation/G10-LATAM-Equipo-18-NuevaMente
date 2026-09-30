import { ComponentFixture, TestBed } from '@angular/core';
import { TrashComponent } from './trash.component';
import { StateService } from '../../core/services/state.service';
import { NUEVAMENTE_API } from '../../core/api/nuevamente-api';
import { MockNuevaMenteApiService } from '../../core/api/mock-nuevamente-api.service';

describe('TrashComponent', () => {
  let component: TrashComponent;
  let fixture: ComponentFixture<TrashComponent>;
  let stateService: StateService;

  beforeEach(async () => {
    localStorage.clear();

    await TestBed.configureTestingModule({
      imports: [TrashComponent],
      providers: [
        StateService,
        { provide: NUEVAMENTE_API, useClass: MockNuevaMenteApiService }
      ]
    }).compileComponents();

    stateService = TestBed.inject(StateService);

    // Setup mock project in library then move to trash
    const proj = stateService.addProjectFromResponse(
      {
        documento_titulo: 'Documento Test Papelera',
        documento_contenido: 'Contenido test',
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Tutorial',
        nicho_sector: 'General',
        nivel_detalle: 'Didactico'
      },
      {
        status: 'exito',
        metadatos: { perfil_aplicado: 'Desarrollador', formato_generado: 'Tutorial', tiempo_estimado_estudio_minutos: 10, conceptos_clave: ['Test'] },
        contenido_adaptado: { titulo: 'Documento Test Papelera', introduccion_contextualizada: 'Intro', items: [] },
        evaluacion_calidad: { anclaje_fuente_score: 0.95, claridad_pedagogica: 'Alta', observaciones: 'Ok' },
        almacenamiento_oci: { bucket: 'test', objeto_id: 'test.json', status_upload: 'completado' }
      }
    );
    stateService.moveToTrash(proj.id);

    fixture = TestBed.createComponent(TrashComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should create TrashComponent', () => {
    expect(component).toBeTruthy();
  });

  it('should render retention info banner with dynamic retention days', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const bannerText = compiled.querySelector('.banner-text p')?.textContent;
    expect(bannerText).toContain('Los elementos se eliminan automáticamente tras 15 días');
  });

  it('should display trashed items in the table', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const rows = compiled.querySelectorAll('.trash-table tbody tr');
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain('Documento Test Papelera');
  });

  it('should restore item to library when Restaurar is clicked', () => {
    expect(stateService.getTrashProjects().length).toBe(1);
    expect(stateService.getLibraryProjects().length).toBe(0);

    component.restoreSingle(component.projectsList()[0]);
    fixture.detectChanges();

    expect(stateService.getTrashProjects().length).toBe(0);
    expect(stateService.getLibraryProjects().length).toBe(1);
  });

  it('should open confirmation dialog when Eliminar definitivamente is clicked', () => {
    expect(component.confirmModal().isOpen).toBeFalse();

    const compiled = fixture.nativeElement as HTMLElement;
    const deleteBtn = compiled.querySelector('.btn-delete-perm') as HTMLButtonElement;
    deleteBtn.click();
    fixture.detectChanges();

    expect(component.confirmModal().isOpen).toBeTrue();
    expect(component.confirmModal().title).toContain('¿Eliminar definitivamente este documento?');
  });

  it('should delete permanently when confirmation modal action is executed', () => {
    const proj = component.projectsList()[0];
    component.openDeleteConfirmModal(proj);
    fixture.detectChanges();

    component.executeModalAction();
    fixture.detectChanges();

    expect(stateService.getTrashProjects().length).toBe(0);
    expect(stateService.getLibraryProjects().length).toBe(0);
  });

  it('should empty entire trash when empty trash confirmation is executed', () => {
    component.openEmptyTrashModal();
    fixture.detectChanges();

    component.executeModalAction();
    fixture.detectChanges();

    expect(stateService.getTrashProjects().length).toBe(0);
  });

  it('should auto-purge items older than 15 days on initialization', () => {
    // Add expired item (purgeAt set 16 days ago)
    const oldProj = stateService.addProjectFromResponse(
      { documento_titulo: 'Documento Expirado', documento_contenido: 'test', perfil_destinatario: 'Ejecutivo', formato_salida: 'Quiz', nicho_sector: 'General', nivel_detalle: 'Conciso' },
      { status: 'exito', metadatos: { perfil_aplicado: 'Ejecutivo', formato_generado: 'Quiz', tiempo_estimado_estudio_minutos: 5, conceptos_clave: [] }, contenido_adaptado: { titulo: 'Expirado', introduccion_contextualizada: '', items: [] }, evaluacion_calidad: { anclaje_fuente_score: 0.9, claridad_pedagogica: 'Alta', observaciones: '' }, almacenamiento_oci: { bucket: 'b', objeto_id: 'o', status_upload: 'completado' } }
    );
    stateService.moveToTrash(oldProj.id);

    // Manipulate purgeAt date to 16 days ago
    const trashed = stateService.getTrashProjects().find(p => p.id === oldProj.id);
    if (trashed) {
      const past = new Date(Date.now() - 16 * 24 * 60 * 60 * 1000).toISOString();
      trashed.purgeAt = past;
    }

    // Trigger auto-purge
    stateService.purgeExpiredProjects();
    const activeTrash = stateService.getTrashProjects();

    expect(activeTrash.some(p => p.id === oldProj.id)).toBeFalse();
  });
});
