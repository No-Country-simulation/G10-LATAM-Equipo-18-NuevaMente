import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LoginComponent } from './login.component';
import { NUEVAMENTE_API } from '../../../core/api/nuevamente-api';
import { MockNuevaMenteApiService } from '../../../core/api/mock-nuevamente-api.service';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: NUEVAMENTE_API, useClass: MockNuevaMenteApiService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create login component', () => {
    expect(component).toBeTruthy();
  });

  it('should validate demo email and password defaults', () => {
    expect(component.loginForm.valid).toBeTrue();
    expect(component.loginForm.value.email).toBe('demo@nuevamente.ai');
  });

  it('should toggle password visibility signal', () => {
    expect(component.showPassword()).toBeFalse();
    component.togglePasswordVisibility();
    expect(component.showPassword()).toBeTrue();
  });

  it('should emit loginSuccess on submit', (done) => {
    component.loginSuccess.subscribe((data) => {
      expect(data.email).toBe('demo@nuevamente.ai');
      done();
    });
    component.onSubmit();
  });
});
