import { ComponentFixture, TestBed } from '@angular/core';
import { JsonDrawerComponent } from './json-drawer.component';
import { AdaptationResponse } from '../../core/models/adaptation.model';

describe('JsonDrawerComponent', () => {
  let component: JsonDrawerComponent;
  let fixture: ComponentFixture<JsonDrawerComponent>;

  const mockResponse: AdaptationResponse = {
    metadatos: {
      perfil_aplicado: 'Desarrollador',
      formato_generado: 'Tutorial',
      nicho_sector: 'Fintech',
      nivel_detalle: 'Tecnico',
      tiempo_estimado_estudio_minutos: 5,
      conceptos_clave: ['API', 'JSON']
    },
    contenido_adaptado: {
      titulo: 'Test Title',
      introduccion_contextualizada: 'Test Intro',
      items: []
    },
    evaluacion_calidad: {
      anclaje_fuente_score: 0.95,
      claridad_pedagogica: 'Alta',
      observaciones: 'OK'
    },
    almacenamiento_oci: {
      bucket: 'test-bucket',
      objeto_id: 'obj-123',
      status_upload: 'completado'
    }
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [JsonDrawerComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(JsonDrawerComponent);
    component = fixture.componentInstance;
  });

  it('should create component', () => {
    expect(component).toBeTruthy();
  });

  it('should format JSON string when data is provided', () => {
    fixture.componentRef.setInput('data', mockResponse);
    fixture.detectChanges();

    expect(component.formattedJson()).toContain('"perfil_aplicado": "Desarrollador"');
  });

  it('should emit closeDrawer on backdrop click', () => {
    fixture.componentRef.setInput('isOpen', true);
    fixture.detectChanges();

    spyOn(component.closeDrawer, 'emit');
    const overlay = fixture.nativeElement.querySelector('.drawer-overlay');
    overlay.click();

    expect(component.closeDrawer.emit).toHaveBeenCalled();
  });

  it('should emit closeDrawer on Escape key press', () => {
    fixture.componentRef.setInput('isOpen', true);
    fixture.detectChanges();

    spyOn(component.closeDrawer, 'emit');
    component.onEscapePress();

    expect(component.closeDrawer.emit).toHaveBeenCalled();
  });
});
