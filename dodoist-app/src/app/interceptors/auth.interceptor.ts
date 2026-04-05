import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError, timeout } from 'rxjs';
import { AuthService } from '../services/auth.service';

const REQUEST_TIMEOUT_MS = 15_000;

// Auth endpoints must never trigger the 401→refresh flow
const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];

function isAuthEndpoint(url: string): boolean {
  return AUTH_ENDPOINTS.some(path => url.includes(path));
}

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const token = authService.getToken();
  const authenticatedRequest = token
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  return next(authenticatedRequest).pipe(
    timeout(REQUEST_TIMEOUT_MS),
    catchError((err) => {
      if (!(err instanceof HttpErrorResponse)) {
        return throwError(() => err);
      }

      // Don't intercept 401s from auth endpoints — let the component handle them
      if (err.status === 401 && !isAuthEndpoint(request.url)) {
        // Attempt silent token refresh using the HttpOnly cookie
        return authService.refreshAccessToken().pipe(
          switchMap(refreshed => {
            const retried = request.clone({
              setHeaders: { Authorization: `Bearer ${refreshed.access_token}` },
            });
            return next(retried);
          }),
          catchError(() => {
            // Refresh failed — session is gone, send to login
            authService.clearToken();
            const returnUrl = router.url;
            router.navigate(['/login'], { queryParams: returnUrl !== '/login' ? { returnUrl } : {} });
            return throwError(() => err);
          }),
        );
      }

      return throwError(() => err);
    }),
  );
};
