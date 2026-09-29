import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, HTTP_INTERCEPTORS, withInterceptorsFromDi } from '@angular/common/http';
import { AppComponent } from './app/app.component';
import { NUEVAMENTE_API } from './app/core/api/nuevamente-api';
import { HttpNuevaMenteApiService } from './app/core/api/http-nuevamente-api.service';
import { AuthInterceptor } from './app/core/interceptors/auth.interceptor';

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(withInterceptorsFromDi()),
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },
    {
      provide: NUEVAMENTE_API,
      useClass: HttpNuevaMenteApiService
    }
  ]
}).catch(err => console.error(err));
