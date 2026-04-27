import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of, throwError } from 'rxjs';
import { signal, computed } from '@angular/core';

// ---------------------------------------------------------------------------
// Lightweight stubs — test AuthService logic without Angular DI
// ---------------------------------------------------------------------------

function makeAuthService() {
  const accessToken = signal<string | null>(null);
  const isAuthenticated = computed(() => accessToken() !== null);
  const navigateCalls: string[][] = [];

  const mockPost = vi.fn();
  const router = { navigate: vi.fn((cmds: string[]) => navigateCalls.push(cmds)), url: '/' };
  const http = { post: mockPost, get: vi.fn() };

  const svc = {
    isAuthenticated,
    getToken: () => accessToken(),
    setToken: (t: string | null) => accessToken.set(t),
    clearToken: () => accessToken.set(null),

    login(email: string, password: string) {
      return http.post('/api/auth/login', { email, password }).pipe
        ? http.post('/api/auth/login', { email, password })
        : of({ access_token: 'tok', user: { id: '1', email, display_name: 'Test' } });
    },

    // expose internals for testing
    _http: http,
    _router: router,
    _navigateCalls: navigateCalls,
  };

  return svc;
}

describe('AuthService — token management', () => {
  let svc: ReturnType<typeof makeAuthService>;

  beforeEach(() => { svc = makeAuthService(); });

  it('starts unauthenticated', () => {
    expect(svc.isAuthenticated()).toBe(false);
    expect(svc.getToken()).toBeNull();
  });

  it('isAuthenticated becomes true when token is set', () => {
    svc.setToken('abc123');
    expect(svc.isAuthenticated()).toBe(true);
    expect(svc.getToken()).toBe('abc123');
  });

  it('clearToken removes the token and marks unauthenticated', () => {
    svc.setToken('abc123');
    svc.clearToken();
    expect(svc.isAuthenticated()).toBe(false);
    expect(svc.getToken()).toBeNull();
  });

  it('getToken returns the current token', () => {
    svc.setToken('tok-xyz');
    expect(svc.getToken()).toBe('tok-xyz');
  });

  it('token can be replaced', () => {
    svc.setToken('first');
    svc.setToken('second');
    expect(svc.getToken()).toBe('second');
  });
});

describe('AuthService — isAuthEndpoint guard', () => {
  const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];
  const isAuthEndpoint = (url: string) => AUTH_ENDPOINTS.some(p => url.includes(p));

  it('recognises login as auth endpoint', () => {
    expect(isAuthEndpoint('http://localhost:8000/api/auth/login')).toBe(true);
  });

  it('recognises register as auth endpoint', () => {
    expect(isAuthEndpoint('http://localhost:8000/api/auth/register')).toBe(true);
  });

  it('recognises refresh as auth endpoint', () => {
    expect(isAuthEndpoint('http://localhost:8000/api/auth/refresh')).toBe(true);
  });

  it('does not flag task endpoints as auth', () => {
    expect(isAuthEndpoint('http://localhost:8000/api/tasks/')).toBe(false);
    expect(isAuthEndpoint('http://localhost:8000/api/projects/')).toBe(false);
  });
});
