import { Injectable } from '@angular/core';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';

export interface RecentProject {
  id: string;
  nombre: string;
  descripcion: string;
  perfil: string;
  formato: string;
  estado: 'Completado' | 'En proceso' | 'Pendiente';
  fecha: string;
  typeIcon: string;
  request?: AdaptationRequest;
  response?: AdaptationResponse;
}

export interface UserMetrics {
  documentos: number;
  contenidos: number;
  ejecucionesRag: number;
  fuentes: number;
}

export interface UserProfile {
  name: string;
  email: string;
  avatarLetter: string;
  isLoggedIn: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class StateService {
  private user: UserProfile = {
    name: '',
    email: '',
    avatarLetter: '',
    isLoggedIn: false
  };

  private metrics: UserMetrics = {
    documentos: 0,
    contenidos: 0,
    ejecucionesRag: 0,
    fuentes: 0
  };

  private projects: RecentProject[] = [];

  constructor() {
    this.loadUserFromStorage();
    this.loadProjectsFromStorage();
  }

  private loadUserFromStorage(): void {
    try {
      const saved = localStorage.getItem('nuevamente_user');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.email && parsed.isLoggedIn) {
          this.user = parsed;
        }
      }
    } catch (e) {
      console.log('Error al cargar sesión de localStorage', e);
    }
  }

  private loadProjectsFromStorage(): void {
    try {
      const savedProjects = localStorage.getItem('nuevamente_projects');
      if (savedProjects) {
        const parsed = JSON.parse(savedProjects);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.projects = parsed;
          this.metrics.documentos = this.projects.length;
          this.metrics.contenidos = this.projects.length;
          this.metrics.ejecucionesRag = this.projects.length;
          this.metrics.fuentes = this.projects.length;
        }
      }
    } catch (e) {
      console.log('Error al cargar proyectos de localStorage', e);
    }
  }

  private saveProjectsToStorage(): void {
    try {
      localStorage.setItem('nuevamente_projects', JSON.stringify(this.projects));
    } catch (e) {
      console.log('Error al guardar proyectos en localStorage', e);
    }
  }

  getUser(): UserProfile {
    return this.user;
  }

  setUser(email: string, name?: string, token?: string): void {
    const cleanEmail = email && email.trim() ? email.trim() : 'usuario@empresa.com';
    let derivedName = name && name.trim() ? name.trim() : this.extractNameFromEmail(cleanEmail);
    if (!derivedName) {
      derivedName = 'Usuario Registrado';
    }

    const firstChar = derivedName.charAt(0).toUpperCase();

    this.user = {
      name: derivedName,
      email: cleanEmail,
      avatarLetter: firstChar || 'U',
      isLoggedIn: true
    };

    try {
      localStorage.setItem('nuevamente_user', JSON.stringify(this.user));
      if (token) {
        localStorage.setItem('nuevamente_jwt_token', token);
      }
    } catch (e) {
      console.log('Error al persistir sesión', e);
    }
  }

  logoutUser(): void {
    this.user = {
      name: '',
      email: '',
      avatarLetter: '',
      isLoggedIn: false
    };
    try {
      localStorage.removeItem('nuevamente_user');
      localStorage.removeItem('nuevamente_jwt_token');
    } catch (e) {
      console.log('Error al eliminar sesión', e);
    }
  }

  private extractNameFromEmail(email: string): string {
    if (!email) return 'Usuario';
    const parts = email.split('@');
    const raw = parts[0].replace(/[._-]/g, ' ');
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }

  getMetrics(): UserMetrics {
    return this.metrics;
  }

  getProjects(): RecentProject[] {
    return this.projects;
  }

  deleteProject(projectId: string): void {
    const index = this.projects.findIndex(p => p.id === projectId);
    if (index !== -1) {
      this.projects.splice(index, 1);
      this.metrics.documentos = Math.max(0, this.metrics.documentos - 1);
      this.metrics.contenidos = Math.max(0, this.metrics.contenidos - 1);
      this.metrics.ejecucionesRag = Math.max(0, this.metrics.ejecucionesRag - 1);
      this.metrics.fuentes = Math.max(0, this.metrics.fuentes - 1);
      this.saveProjectsToStorage();
    }
  }

  addProjectFromResponse(request: AdaptationRequest, response: AdaptationResponse): RecentProject {
    // 1. Update Metrics
    this.metrics.documentos += 1;
    this.metrics.contenidos += 1;
    this.metrics.ejecucionesRag += 1;
    this.metrics.fuentes += 1;

    // 2. Format Date
    const now = new Date();
    const formattedDate = `${now.getDate()} ${now.toLocaleString('es-ES', { month: 'short' })}. ${now.getFullYear()} ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    // 3. Determine Format Icon
    let formatCode = 'DOC';
    if (request.formato_salida.includes('Flashcard')) formatCode = 'FC';
    else if (request.formato_salida.includes('Quiz')) formatCode = 'QZ';
    else if (request.formato_salida.includes('Tutorial')) formatCode = 'TUT';
    else if (request.formato_salida.includes('TLDR') || request.formato_salida.includes('Resumen')) formatCode = 'TL';

    const newProject: RecentProject = {
      id: `proj-${Date.now()}`,
      nombre: request.documento_titulo || 'Documento Técnico Adaptado',
      descripcion: `Adaptación Didáctica (${request.perfil_destinatario})`,
      perfil: request.perfil_destinatario,
      formato: request.formato_salida,
      estado: 'Completado',
      fecha: formattedDate,
      typeIcon: formatCode,
      request: request,
      response: response
    };

    this.projects.unshift(newProject);
    this.saveProjectsToStorage();
    return newProject;
  }
}
