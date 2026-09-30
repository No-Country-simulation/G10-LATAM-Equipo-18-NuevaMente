import { TestBed } from '@angular/core/testing';
import { MockAuthApiService } from './mock-auth-api.service';

describe('MockAuthApiService', () => {
  let service: MockAuthApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [MockAuthApiService]
    });
    service = TestBed.inject(MockAuthApiService);
  });

  it('should authenticate demo user with correct credentials', (done) => {
    service.login('ana.martinez@empresa.com', 'Password123!').subscribe({
      next: (res) => {
        expect(res.status).toBe('exito');
        expect(res.user?.email).toBe('ana.martinez@empresa.com');
        expect(res.access_token).toBeDefined();
        done();
      }
    });
  });

  it('should fail with generic error "Credenciales incorrectas" for wrong password', (done) => {
    service.login('ana.martinez@empresa.com', 'WrongPassword123!').subscribe({
      next: () => fail('Should have failed'),
      error: (err) => {
        expect(err.error.detail).toBe('Credenciales incorrectas');
        done();
      }
    });
  });

  it('should fail with same generic error "Credenciales incorrectas" for non-existent email', (done) => {
    service.login('nonexistent@empresa.com', 'Password123!').subscribe({
      next: () => fail('Should have failed'),
      error: (err) => {
        expect(err.error.detail).toBe('Credenciales incorrectas');
        done();
      }
    });
  });

  it('should reject registration if password does not meet complexity rules', (done) => {
    service.register('Carlos Dev', 'carlos@empresa.com', 'weakpass').subscribe({
      next: () => fail('Should have failed'),
      error: (err) => {
        expect(err.error.detail).toContain('8 caracteres');
        done();
      }
    });
  });

  it('should reject registration if email is duplicate', (done) => {
    service.register('Ana Fake', 'ana.martinez@empresa.com', 'Password123!').subscribe({
      next: () => fail('Should have failed'),
      error: (err) => {
        expect(err.error.detail).toBe('El correo electrónico ya está registrado.');
        done();
      }
    });
  });

  it('should register valid new user and persist metadata without tokens in localStorage', (done) => {
    const testEmail = `newuser_${Date.now()}@empresa.com`;
    service.register('Nuevo Usuario', testEmail, 'Password123!').subscribe({
      next: (res) => {
        expect(res.status).toBe('exito');
        expect(res.user?.email).toBe(testEmail);

        // Verify tokens are NOT stored in localStorage
        const savedUsers = localStorage.getItem('nuevamente_mock_users') || '';
        expect(savedUsers).not.toContain('access_token');
        done();
      }
    });
  });

  it('should throw OAUTH_NOT_CONFIGURED error when calling startOAuth and NOT create a session', (done) => {
    service.startOAuth('Google').subscribe({
      next: () => fail('Should have failed'),
      error: (err) => {
        expect(err.error.detail).toBe('OAUTH_NOT_CONFIGURED');
        done();
      }
    });
  });
});
