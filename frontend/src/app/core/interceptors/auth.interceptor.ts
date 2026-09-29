import { Injectable, inject } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, switchMap, filter, take } from 'rxjs/operators';
import { AuthStore } from '../store/auth.store';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private authStore = inject(AuthStore);
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = this.authStore.accessToken();
    let authReq = req;

    if (token && !req.headers.has('Authorization')) {
      authReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    }

    return next.handle(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401 && !req.url.includes('/auth/login') && !req.url.includes('/auth/refresh')) {
          return this.handle401Error(authReq, next);
        }
        return throwError(() => error);
      })
    );
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      return this.authStore.getAuthApi().refreshToken().pipe(
        switchMap((res) => {
          this.isRefreshing = false;
          if (res.access_token && res.user) {
            this.authStore.setSession(res.access_token, res.user);
            this.refreshTokenSubject.next(res.access_token);
            return next.handle(request.clone({
              setHeaders: { Authorization: `Bearer ${res.access_token}` }
            }));
          }
          this.authStore.triggerSessionExpired();
          return throwError(() => new Error('Refresh failed'));
        }),
        catchError((err) => {
          this.isRefreshing = false;
          this.authStore.triggerSessionExpired();
          return throwError(() => err);
        })
      );
    } else {
      return this.refreshTokenSubject.pipe(
        filter(token => token !== null),
        take(1),
        switchMap((token) => {
          return next.handle(request.clone({
            setHeaders: { Authorization: `Bearer ${token}` }
          }));
        })
      );
    }
  }
}
