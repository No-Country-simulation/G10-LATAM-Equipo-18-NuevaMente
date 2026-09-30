import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';
import { LoginComponent } from './features/auth/login/login.component';
import { WorkspaceComponent } from './features/workspace/workspace.component';
import { LibraryComponent } from './features/library/library.component';

export const routes: Routes = [
  // Public (Guest) Auth Routes
  {
    path: 'auth/login',
    component: LoginComponent,
    canActivate: [guestGuard],
    canMatch: [guestGuard]
  },
  {
    path: 'auth/register',
    component: LoginComponent,
    canActivate: [guestGuard],
    canMatch: [guestGuard]
  },
  {
    path: 'auth/verify',
    component: LoginComponent,
    canActivate: [guestGuard],
    canMatch: [guestGuard]
  },
  {
    path: 'auth/forgot',
    component: LoginComponent,
    canActivate: [guestGuard],
    canMatch: [guestGuard]
  },
  {
    path: 'auth/reset',
    component: LoginComponent,
    canActivate: [guestGuard],
    canMatch: [guestGuard]
  },
  {
    path: 'login',
    redirectTo: 'auth/login',
    pathMatch: 'full'
  },

  // Public Legal / Terms / Info / 404 Routes
  {
    path: 'terms',
    component: LoginComponent
  },
  {
    path: 'privacy',
    component: LoginComponent
  },
  {
    path: '404',
    component: LoginComponent
  },

  // Internal Protected Routes
  {
    path: 'workspace',
    component: WorkspaceComponent,
    canActivate: [authGuard],
    canMatch: [authGuard]
  },
  {
    path: 'library',
    component: LibraryComponent,
    canActivate: [authGuard],
    canMatch: [authGuard]
  },

  // Redirects
  {
    path: '',
    redirectTo: 'workspace',
    pathMatch: 'full'
  },
  {
    path: '**',
    redirectTo: 'auth/login'
  }
];
