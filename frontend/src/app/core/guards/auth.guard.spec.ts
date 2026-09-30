import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { authGuard, guestGuard, sanitizeReturnUrl } from './auth.guard';
import { AuthStore } from '../store/auth.store';
import { NUEVAMENTE_API } from '../api/nuevamente-api';
import { MockNuevaMenteApiService } from '../api/mock-nuevamente-api.service';

describe('AuthGuard & GuestGuard & ReturnUrl Sanitizer', () => {
  let authStore: AuthStore;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        AuthStore,
        { provide: Router, useValue: routerSpy },
        { provide: NUEVAMENTE_API, useClass: MockNuevaMenteApiService }
      ]
    });

    authStore = TestBed.inject(AuthStore);
  });

  describe('sanitizeReturnUrl', () => {
    it('should return /workspace for null, empty, or undefined', () => {
      expect(sanitizeReturnUrl(undefined)).toBe('/workspace');
      expect(sanitizeReturnUrl('')).toBe('/workspace');
    });

    it('should sanitize external absolute URLs to /workspace', () => {
      expect(sanitizeReturnUrl('http://malicious.com')).toBe('/workspace');
      expect(sanitizeReturnUrl('https://evil.com/login')).toBe('/workspace');
      expect(sanitizeReturnUrl('//evil.com')).toBe('/workspace');
    });

    it('should preserve valid relative URLs', () => {
      expect(sanitizeReturnUrl('/workspace')).toBe('/workspace');
      expect(sanitizeReturnUrl('/library')).toBe('/library');
    });
  });

  describe('authGuard', () => {
    it('should redirect unauthenticated users to /auth/login with returnUrl', async () => {
      authStore.handleLocalLogoutState();

      const route: any = {};
      const state: any = { url: '/library' };

      const result = await TestBed.runInInjectionContext(() => authGuard(route, state));

      expect(result).toBeFalse();
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login'], {
        queryParams: { returnUrl: '/library' }
      });
    });

    it('should allow authenticated users to access protected routes', async () => {
      authStore.setSession('test_token', { id: '1', email: 'test@empresa.com', name: 'Test User' });

      const route: any = {};
      const state: any = { url: '/workspace' };

      const result = await TestBed.runInInjectionContext(() => authGuard(route, state));

      expect(result).toBeTrue();
    });
  });

  describe('guestGuard', () => {
    it('should allow unauthenticated users to access login page', async () => {
      authStore.handleLocalLogoutState();

      const route: any = {};
      const state: any = { url: '/auth/login' };

      const result = await TestBed.runInInjectionContext(() => guestGuard(route, state));

      expect(result).toBeTrue();
    });

    it('should redirect authenticated users to /workspace', async () => {
      authStore.setSession('test_token', { id: '1', email: 'test@empresa.com', name: 'Test User' });

      const route: any = {};
      const state: any = { url: '/auth/login' };

      const result = await TestBed.runInInjectionContext(() => guestGuard(route, state));

      expect(result).toBeFalse();
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/workspace'], { replaceUrl: true });
    });
  });
});
