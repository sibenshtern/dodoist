import { computed, inject, Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap, catchError, EMPTY, retry } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
}

interface AuthResponse {
  access_token: string;
  expires_in: number;
  user: AuthUser;
}

interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // Access token lives in memory only — never in localStorage.
  // The refresh token is stored in an HttpOnly cookie managed by the browser.
  private readonly accessToken = signal<string | null>(null);

  readonly isAuthenticated = computed(() => this.accessToken() !== null);

  getToken(): string | null {
    return this.accessToken();
  }

  register(
    email: string,
    password: string,
    displayName: string,
    timezone: string,
    inviteToken?: string,
  ): Observable<AuthResponse> {
    const body: Record<string, string> = { email, password, display_name: displayName, timezone };
    if (inviteToken) body['invite_token'] = inviteToken;
    return this.http
      .post<AuthResponse>(
        `${environment.apiBase}/api/auth/register`,
        body,
        { withCredentials: true },
      )
      .pipe(tap(response => this.accessToken.set(response.access_token)));
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(
        `${environment.apiBase}/api/auth/login`,
        { email, password },
        { withCredentials: true },
      )
      .pipe(tap(response => this.accessToken.set(response.access_token)));
  }

  logout(): void {
    // Clear local state immediately so the UI reacts right away.
    this.accessToken.set(null);
    this.http
      .post(`${environment.apiBase}/api/auth/logout`, {}, { withCredentials: true })
      .pipe(
        retry(2),
        catchError(err => {
          console.error('Logout API call failed after retries', err);
          return EMPTY;
        }),
      )
      .subscribe();
    this.router.navigate(['/login']);
  }

  refreshAccessToken(): Observable<RefreshResponse> {
    return this.http
      .post<RefreshResponse>(
        `${environment.apiBase}/api/auth/refresh`,
        {},
        { withCredentials: true },
      )
      .pipe(tap(response => this.accessToken.set(response.access_token)));
  }

  clearToken(): void {
    this.accessToken.set(null);
  }

  verifyEmail(token: string): Observable<{ detail: string; email: string }> {
    return this.http.post<{ detail: string; email: string }>(
      `${environment.apiBase}/api/auth/verify-email`,
      {},
      { headers: new HttpHeaders({ 'X-Verification-Token': token }) },
    );
  }

  resendVerification(): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${environment.apiBase}/api/auth/resend-verification`,
      {},
      { withCredentials: true },
    );
  }

  forgotPassword(email: string): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${environment.apiBase}/api/auth/forgot-password`,
      { email },
    );
  }

  resetPassword(token: string, newPassword: string): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(
      `${environment.apiBase}/api/auth/reset-password`,
      {},
      {
        headers: new HttpHeaders({
          'X-Reset-Token': token,
          'X-New-Password': newPassword,
        }),
      },
    );
  }
}
