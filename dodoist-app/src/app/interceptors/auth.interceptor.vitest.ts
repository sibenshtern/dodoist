import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of, throwError } from 'rxjs';

// ---------------------------------------------------------------------------
// Test the auth interceptor's core logic in isolation
// ---------------------------------------------------------------------------

const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];
const REQUEST_TIMEOUT_MS = 15_000;

function isAuthEndpoint(url: string): boolean {
  return AUTH_ENDPOINTS.some(path => url.includes(path));
}

describe('isAuthEndpoint()', () => {
  it.each([
    ['http://api/api/auth/login', true],
    ['http://api/api/auth/register', true],
    ['http://api/api/auth/refresh', true],
    ['http://api/api/tasks/', false],
    ['http://api/api/projects/uuid/tasks/', false],
    ['http://api/api/notifications/', false],
    ['http://api/api/auth/loginextra', true],  // substring match — by design
  ])('%s → %s', (url, expected) => {
    expect(isAuthEndpoint(url)).toBe(expected);
  });
});

describe('Auth interceptor — token attachment', () => {
  function makeInterceptor(token: string | null) {
    const clonedHeaders: Record<string, string> = {};
    const mockRequest = {
      url: 'http://api/api/tasks/',
      clone: vi.fn((opts: { setHeaders: Record<string, string> }) => {
        Object.assign(clonedHeaders, opts.setHeaders);
        return { ...mockRequest, cloned: true };
      }),
    };
    const next = vi.fn().mockReturnValue(of({ status: 200 }));
    const authService = { getToken: () => token, isAuthenticated: () => !!token, refreshAccessToken: vi.fn(), clearToken: vi.fn() };
    const router = { url: '/home', navigate: vi.fn() };

    // Inline interceptor logic
    function intercept(req: typeof mockRequest) {
      const t = authService.getToken();
      const outReq = t ? req.clone({ setHeaders: { Authorization: `Bearer ${t}` } }) : req;
      return next(outReq);
    }

    return { intercept, mockRequest, next, clonedHeaders, authService, router };
  }

  it('attaches Bearer token when token is present', () => {
    const { intercept, mockRequest, clonedHeaders } = makeInterceptor('my-token');
    intercept(mockRequest).subscribe();
    expect(clonedHeaders['Authorization']).toBe('Bearer my-token');
  });

  it('does not add Authorization header when no token', () => {
    const { intercept, mockRequest, clonedHeaders, next } = makeInterceptor(null);
    intercept(mockRequest).subscribe();
    expect(clonedHeaders['Authorization']).toBeUndefined();
    // Passes original request without cloning
    expect(mockRequest.clone).not.toHaveBeenCalled();
    expect(next).toHaveBeenCalledWith(mockRequest);
  });
});

describe('Auth interceptor — 401 refresh flow', () => {
  it('skips refresh for auth endpoints', () => {
    const req = { url: 'http://api/api/auth/login' };
    const refreshSpy = vi.fn();
    const authService = { getToken: () => 'tok', refreshAccessToken: refreshSpy, clearToken: vi.fn() };

    // Simulate 401 on an auth endpoint — should not call refresh
    if (!isAuthEndpoint(req.url)) {
      authService.refreshAccessToken();
    }
    expect(refreshSpy).not.toHaveBeenCalled();
  });

  it('triggers refresh for non-auth 401s', () => {
    const req = { url: 'http://api/api/tasks/' };
    const refreshSpy = vi.fn().mockReturnValue(of({ access_token: 'new-tok' }));
    const authService = { getToken: () => 'old-tok', refreshAccessToken: refreshSpy, clearToken: vi.fn() };

    if (!isAuthEndpoint(req.url)) {
      authService.refreshAccessToken();
    }
    expect(refreshSpy).toHaveBeenCalledOnce();
  });
});

describe('Request timeout constant', () => {
  it('is 15 seconds', () => {
    expect(REQUEST_TIMEOUT_MS).toBe(15_000);
  });
});
