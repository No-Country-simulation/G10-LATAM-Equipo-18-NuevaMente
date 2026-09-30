import { ComponentFixture, TestBed } from '@angular/core';
import { RouterTestingModule } from '@angular/router/testing';
import { LoginComponent } from './login.component';
import { NUEVAMENTE_API } from '../../../core/api/nuevamente-api';
import { MockNuevaMenteApiService } from '../../../core/api/mock-nuevamente-api.service';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
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
    expect(component.loginForm.value.email).toBe('ana.martinez@empresa.com');
    expect(component.loginForm.value.password).toBe('Password123!');
  });

  it('should toggle password visibility signal', () => {
    expect(component.showPassword()).toBeFalse();
    component.togglePasswordVisibility();
    expect(component.showPassword()).toBeTrue();
  });

  it('should disable social login buttons when enableSocialLogin is false', () => {
    expect(component.enableSocialLogin).toBeFalse();
    const googleBtn = fixture.nativeElement.querySelector('.sso-btn');
    expect(googleBtn.disabled).toBeTrue();
  });
});
