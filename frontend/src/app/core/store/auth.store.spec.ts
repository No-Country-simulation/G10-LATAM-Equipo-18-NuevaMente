import { TestBed } from '@angular/core';
import { Router } from '@angular/router';
import { AuthStore } from './auth.store';
import { NUEVAMENTE_API } from '../api/nuevamente-api';
import { MockNuevaMenteApiService } from '../api/mock-nuevamente-api.service';

describe('AuthStore', () => {
  let store: AuthStore;
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

    store = TestBed.inject(AuthStore);
  });

  it('should initialize unauthenticated state by default', () => {
    store.handleLocalLogoutState();
    expect(store.isAuthenticated()).toBeFalse();
    expect(store.user()).toBeNull();
    expect(store.accessToken()).toBeNull();
  });

  it('should set session tokens in memory only', () => {
    const testUser = { id: 'usr_1', email: 'test@empresa.com', name: 'Test User' };
    store.setSession('token_abc_123', testUser);

    expect(store.isAuthenticated()).toBeTrue();
    expect(store.accessToken()).toBe('token_abc_123');
    expect(store.user()?.email).toBe('test@empresa.com');
  });

  it('should clear memory state on logout and navigate to /auth/login', () => {
    store.setSession('token_abc_123', { id: 'usr_1', email: 'test@empresa.com', name: 'Test User' });
    store.logout();

    expect(store.isAuthenticated()).toBeFalse();
    expect(store.user()).toBeNull();
    expect(store.accessToken()).toBeNull();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login'], { replaceUrl: true });
  });
});
