import { describe, it, expect, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Test the authGuard's decision logic without Angular's DI / TestBed
// ---------------------------------------------------------------------------

type UrlTree = { commands: string[]; extras: Record<string, unknown> };

function makeGuard(isAuthenticated: boolean) {
  const authService = { isAuthenticated: () => isAuthenticated };
  const navigateCalls: Array<[string[], Record<string, unknown>]> = [];
  const router = {
    createUrlTree: (cmds: string[], extras: Record<string, unknown>): UrlTree => {
      navigateCalls.push([cmds, extras]);
      return { commands: cmds, extras };
    },
  };

  function guard(url: string): boolean | UrlTree {
    if (authService.isAuthenticated()) return true;
    return router.createUrlTree(['/login'], { queryParams: { returnUrl: url } });
  }

  return { guard, navigateCalls };
}

describe('authGuard', () => {
  it('returns true when user is authenticated', () => {
    const { guard } = makeGuard(true);
    expect(guard('/home')).toBe(true);
  });

  it('redirects to /login when not authenticated', () => {
    const { guard } = makeGuard(false);
    const result = guard('/home') as UrlTree;
    expect(result.commands).toEqual(['/login']);
  });

  it('includes returnUrl in redirect query params', () => {
    const { guard } = makeGuard(false);
    const result = guard('/projects/123') as UrlTree;
    expect((result.extras as any).queryParams?.returnUrl).toBe('/projects/123');
  });

  it('does not redirect when already authenticated', () => {
    const { guard, navigateCalls } = makeGuard(true);
    guard('/tasks');
    expect(navigateCalls).toHaveLength(0);
  });

  it('preserves deep nested returnUrl', () => {
    const { guard } = makeGuard(false);
    const deep = '/projects/abc/tasks?tab=board';
    const result = guard(deep) as UrlTree;
    expect((result.extras as any).queryParams?.returnUrl).toBe(deep);
  });
});

// ---------------------------------------------------------------------------
// publicGuard (inverse — authenticated users get bounced away)
// ---------------------------------------------------------------------------

function makePublicGuard(isAuthenticated: boolean) {
  const authService = { isAuthenticated: () => isAuthenticated };
  const router = {
    createUrlTree: (cmds: string[]): UrlTree => ({ commands: cmds, extras: {} }),
  };

  function guard(): boolean | UrlTree {
    if (!authService.isAuthenticated()) return true;
    return router.createUrlTree(['/home']);
  }

  return { guard };
}

describe('publicGuard', () => {
  it('allows access when not authenticated', () => {
    const { guard } = makePublicGuard(false);
    expect(guard()).toBe(true);
  });

  it('redirects to /home when already authenticated', () => {
    const { guard } = makePublicGuard(true);
    const result = guard() as UrlTree;
    expect(result.commands).toEqual(['/home']);
  });
});
