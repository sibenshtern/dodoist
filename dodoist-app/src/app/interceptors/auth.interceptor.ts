import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError, timeout } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

const REQUEST_TIMEOUT_MS = 15_000;

// Auth endpoints must never trigger the 401→refresh flow
const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];

const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

function isAuthEndpoint(url: string): boolean {
  return AUTH_ENDPOINTS.some(path => url.includes(path));
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const toast = inject(ToastService);

  const token = authService.getToken();

  let req = token
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  // Attach CSRF token on state-changing requests so Django's CsrfViewMiddleware
  // can protect the admin and any future session-auth endpoints.
  if (MUTATING_METHODS.has(req.method)) {
    const csrf = getCsrfToken();
    if (csrf) {
      req = req.clone({ setHeaders: { 'X-CSRFToken': csrf } });
    }
  }

  return next(req).pipe(
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

      // Surface server errors as a toast so components don't need per-component loadError signals.
      if (err.status >= 500) {
        toast.error('Server error. Please try again.');
      }

      return throwError(() => err);
    }),
  );
};
