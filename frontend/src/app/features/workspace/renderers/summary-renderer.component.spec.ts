import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SummaryRendererComponent } from './summary-renderer.component';
import { ResumenEjecutivoItem } from '../../../core/models/adaptation.model';

describe('SummaryRendererComponent', () => {
  let component: SummaryRendererComponent;
  let fixture: ComponentFixture<SummaryRendererComponent>;

  const storedSummary = [
    'El sistema permite pagos directos entre pares sin intermediarios financieros. [1]',
    'La prueba de trabajo descarta el doble gasto sin una autoridad central. [2]',
    '',
    'Fuentes',
    'Bitcoin: A Peer-to-Peer Electronic Cash System',
    '[1] Bitcoin: A Peer-to-Peer Electronic Cash System (p. 1)',
    '[2] 3. Proof of Work (p. 4)'
  ].join('\n');

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SummaryRendererComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(SummaryRendererComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('items', []);
    fixture.detectChanges();
  });

  it('should render the stored summary as one paragraph per block', () => {
    fixture.componentRef.setInput('text', storedSummary);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const paragraphs = compiled.querySelectorAll('.summary-flow p');
    expect(paragraphs.length).toBe(2);
    expect(paragraphs[0].textContent).toContain('[1]');
    expect(paragraphs[1].textContent).toContain('[2]');
  });

  it('should render the reference list with the title once and one line per number', () => {
    fixture.componentRef.setInput('text', storedSummary);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.sources-header')?.textContent).toContain('Fuentes');
    expect(compiled.querySelector('.sources-general')?.textContent).toContain(
      'Bitcoin: A Peer-to-Peer Electronic Cash System'
    );

    const lines = compiled.querySelectorAll('.source-line');
    expect(lines.length).toBe(2);
    expect(lines[0].textContent).toContain('(p. 1)');
    expect(lines[1].textContent).toContain('3. Proof of Work');
  });

  it('should accept a localized reference header', () => {
    fixture.componentRef.setInput('text', storedSummary.replace('Fuentes', 'Fontes'));
    fixture.detectChanges();

    expect(component.sourcesHeader).toBe('Fontes');
    expect(component.sourceLines.length).toBe(2);
    expect(component.generalSource).toContain('Bitcoin');
  });

  it('should show the notice when the summary could not be generated', () => {
    fixture.componentRef.setInput('empty', true);
    fixture.componentRef.setInput(
      'text',
      'No se pudo generar un resumen con el contenido disponible en este documento.'
    );
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.summary-notice')).toBeTruthy();
    expect(compiled.querySelector('.summary-notice')?.textContent).toContain('No se pudo generar');
    expect(compiled.querySelector('.summary-flow')).toBeNull();
    expect(compiled.querySelector('.tldr-banner')).toBeNull();
  });

  it('should fall back to the structured items when there is no stored text', () => {
    const items: ResumenEjecutivoItem[] = [
      { punto_clave: 'Punto clave', impacto_negocio: 'Impacto operativo', fuentes: [] },
      { punto_clave: 'Segundo punto', impacto_negocio: 'Segundo impacto', fuentes: [] }
    ];
    fixture.componentRef.setInput('items', items);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const paragraphs = compiled.querySelectorAll('.summary-flow p');
    expect(paragraphs.length).toBe(2);
    expect(paragraphs[0].textContent).toContain('Punto clave');
  });

  it('should count the points verified against the source document', () => {
    const items: ResumenEjecutivoItem[] = [
      {
        punto_clave: 'Punto verificado',
        impacto_negocio: 'Impacto',
        fuentes: [{ chunk_id: 'parent_1', seccion: '1. Introducción', extracto: '...', verificado: true }]
      },
      {
        punto_clave: 'Punto sin verificar',
        impacto_negocio: 'Impacto',
        fuentes: [{ chunk_id: 'parent_2', seccion: '2. Transactions', extracto: '...', verificado: false }]
      }
    ];
    fixture.componentRef.setInput('items', items);
    fixture.detectChanges();

    expect(component.verifiedPointsCount).toBe(1);
  });
});
