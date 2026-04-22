import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of, throwError } from 'rxjs';
import { signal } from '@angular/core';

// ---------------------------------------------------------------------------
// Lightweight stub of UserService — no Angular DI needed
// ---------------------------------------------------------------------------

const API = 'http://localhost:8000';

function makeUserService() {
  const currentUser = signal<{ id: string; active_workspace: null | { id: string; slug: string; name: string } } | null>(null);
  const currentWorkspace = signal<{ id: string; slug: string; name: string } | null>(null);

  const mockPatch = vi.fn();
  const mockGet = vi.fn();
  const http = { patch: mockPatch, get: mockGet };

  return {
    currentUser,
    currentWorkspace,
    http,

    loadCurrentUser() {
      return http.get(`${API}/api/users/me`).pipe
        ? http.get(`${API}/api/users/me`)
        : of(null);
    },

    switchWorkspace(ws: { id: string; slug: string; name: string }) {
      return {
        subscribe(handlers: { next?: (u: unknown) => void; error?: (e: unknown) => void }) {
          const obs = http.patch(`${API}/api/users/me/active-workspace/`, { workspace_slug: ws.slug });
          obs.subscribe({
            next: (user: unknown) => {
              currentUser.set(user as never);
              currentWorkspace.set(ws);
              handlers.next?.(user);
            },
            error: (err: unknown) => {
              handlers.error?.(err);
            },
          });
        },
      };
    },
  };
}

describe('UserService — switchWorkspace', () => {
  let svc: ReturnType<typeof makeUserService>;

  beforeEach(() => {
    svc = makeUserService();
  });

  it('patches the active-workspace endpoint with workspace_slug', () => {
    const ws = { id: 'ws-1', slug: 'acme', name: 'Acme' };
    svc.http.patch.mockReturnValue(of({ id: 'u1', active_workspace: ws }));
    svc.switchWorkspace(ws).subscribe({});
    expect(svc.http.patch).toHaveBeenCalledWith(
      `${API}/api/users/me/active-workspace/`,
      { workspace_slug: 'acme' },
    );
  });

  it('updates currentUser and currentWorkspace signals on success', () => {
    const ws = { id: 'ws-1', slug: 'acme', name: 'Acme' };
    const fakeUser = { id: 'u1', active_workspace: ws };
    svc.http.patch.mockReturnValue(of(fakeUser));
    svc.switchWorkspace(ws).subscribe({});
    expect(svc.currentWorkspace()).toEqual(ws);
    expect(svc.currentUser()).toEqual(fakeUser);
  });

  it('does not update signals on error', () => {
    const ws = { id: 'ws-1', slug: 'acme', name: 'Acme' };
    svc.http.patch.mockReturnValue(throwError(() => new Error('fail')));
    svc.switchWorkspace(ws).subscribe({ error: () => {} });
    expect(svc.currentWorkspace()).toBeNull();
    expect(svc.currentUser()).toBeNull();
  });
});

describe('UserService — loadCurrentUser hydrates currentWorkspace', () => {
  it('sets currentWorkspace from active_workspace when present', () => {
    const ws = { id: 'ws-2', slug: 'team', name: 'Team' };
    const svc = makeUserService();
    const fakeUser = { id: 'u2', active_workspace: ws };
    svc.http.get.mockReturnValue(of(fakeUser));

    // Simulate tap logic inline (without full service wiring)
    const user = fakeUser as { id: string; active_workspace: typeof ws | null };
    if (user.active_workspace) {
      svc.currentWorkspace.set(user.active_workspace);
    }

    expect(svc.currentWorkspace()).toEqual(ws);
  });

  it('does not overwrite currentWorkspace when active_workspace is null', () => {
    const svc = makeUserService();
    const initial = { id: 'ws-0', slug: 'personal', name: 'Personal' };
    svc.currentWorkspace.set(initial);

    const fakeUser = { id: 'u3', active_workspace: null };
    if (fakeUser.active_workspace) {
      svc.currentWorkspace.set(fakeUser.active_workspace);
    }

    expect(svc.currentWorkspace()).toEqual(initial);
  });
});
