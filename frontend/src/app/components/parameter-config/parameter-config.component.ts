import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-parameter-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="config-panel">
      <h3 class="title">⚙️ Criterios de Personalización Didáctica</h3>
      <div class="form-grid">
        <div class="form-group">
          <label>Perfil del Destinatario:</label>
          <select [(ngModel)]="perfil" class="select-input">
            <option value="Principiante">Principiante / Transición de Carrera</option>
            <option value="Desarrollador">Desarrollador Junior / Semi Senior</option>
            <option value="Arquitecto">Líder Técnico / Arquitecto</option>
            <option value="Ejecutivo">Gestor / Ejecutivo (No Técnico)</option>
          </select>
        </div>

        <div class="form-group">
          <label>Formato Pedagógico de Salida:</label>
          <select [(ngModel)]="formato" class="select-input">
            <option value="Flashcards">Flashcards de Memorización</option>
            <option value="Quiz">Quiz Interactivo con Justificaciones</option>
            <option value="Tutorial">Guía Práctica Paso a Paso (Tutorial)</option>
            <option value="TLDR">Resumen Ejecutivo (TL;DR)</option>
          </select>
        </div>

        <div class="form-group">
          <label>Nicho / Industria de Aplicación:</label>
          <select [(ngModel)]="nicho" class="select-input">
            <option value="General">General / Infraestructura Nube</option>
            <option value="Fintech">Fintech & Servicios Financieros</option>
            <option value="Salud">Salud & Biotecnología</option>
            <option value="E-commerce">E-commerce & Retail</option>
          </select>
        </div>
      </div>

      <button class="adapt-btn" (click)="onAdaptClick()">
        ⚡ Generar Contenido Adaptado con Gemini
      </button>
    </div>
  `,
  styles: [`
    .config-panel { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .title { font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-bottom: 1.25rem; }
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem; }
    .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
    label { font-size: 0.85rem; font-weight: 600; color: #475569; }
    .select-input { padding: 0.75rem; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 0.95rem; background: white; color: #0f172a; }
    .adapt-btn { width: 100%; padding: 0.9rem; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; border-radius: 8px; font-weight: 700; font-size: 1rem; cursor: pointer; transition: opacity 0.2s; }
    .adapt-btn:hover { opacity: 0.95; }
  `]
})
export class ParameterConfigComponent {
  perfil: string = 'Principiante';
  formato: string = 'Flashcards';
  nicho: string = 'General';

  @Output() configChanged = new EventEmitter<any>();

  onAdaptClick(): void {
    this.configChanged.emit({
      perfil_destinatario: this.perfil,
      formato_salida: this.formato,
      nicho_sector: this.nicho,
      nivel_detalle: 'Didactico'
    });
  }
}
