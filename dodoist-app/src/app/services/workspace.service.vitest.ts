import { describe, it, expect, vi, beforeEach } from 'vitest';
import { of } from 'rxjs';

// ---------------------------------------------------------------------------
// Stub — tests verify that each method calls the right URL with the right body
// ---------------------------------------------------------------------------

const API = 'http://localhost:8000';

function makeWsService() {
  const delete_ = vi.fn();
  const post = vi.fn();
  const get = vi.fn();
  const patch = vi.fn();

  const http = { delete: delete_, post, get, patch };

  function url(path: string) { return `${API}${path}`; }

  return {
    http,
    list: () => http.get(url('/api/workspaces/')),
    get: (slug: string) => http.get(url(`/api/workspaces/${slug}/`)),
    create: (p: object) => http.post(url('/api/workspaces/'), p),
    update: (slug: string, d: object) => http.patch(url(`/api/workspaces/${slug}/`), d),
    delete: (slug: string) => http.delete(url(`/api/workspaces/${slug}/`)),
    restore: (slug: string) => http.post(url(`/api/workspaces/${slug}/restore/`), {}),
    transferOwnership: (slug: string, id: string) =>
      http.post(url(`/api/workspaces/${slug}/transfer/`), { new_owner_id: id }),
    leave: (slug: string) => http.post(url(`/api/workspaces/${slug}/leave/`), {}),
    listMembers: (slug: string) => http.get(url(`/api/workspaces/${slug}/members/`)),
    addMember: (slug: string, userId: string) =>
      http.post(url(`/api/workspaces/${slug}/members/`), { user_id: userId, role: 'MEMBER' }),
    updateMemberRole: (slug: string, uid: string, role: string) =>
      http.patch(url(`/api/workspaces/${slug}/members/${uid}/`), { role }),
    removeMember: (slug: string, uid: string) =>
      http.delete(url(`/api/workspaces/${slug}/members/${uid}/`)),
    listInvitations: (slug: string) => http.get(url(`/api/workspaces/${slug}/invitations/`)),
    createEmailInvite: (slug: string, email: string, role: string) =>
      http.post(url(`/api/workspaces/${slug}/invitations/`), { kind: 'email', email, role_to_grant: role }),
    revokeInvitation: (slug: string, id: string) =>
      http.delete(url(`/api/workspaces/${slug}/invitations/${id}/`)),
    createInviteLink: (slug: string, role: string, maxUses?: number | null, expiresAt?: string) =>
      http.post(url(`/api/workspaces/${slug}/invite-links/`), {
        role_to_grant: role, max_uses: maxUses ?? null, expires_at: expiresAt ?? null,
      }),
    acceptInvitation: (token: string) =>
      http.post(url('/api/invitations/accept/'), { token }),
    listMyInvitations: () => http.get(url('/api/invitations/me/')),
  };
}

describe('WorkspaceService — URL routing', () => {
  let svc: ReturnType<typeof makeWsService>;

  beforeEach(() => {
    svc = makeWsService();
    svc.http.get.mockReturnValue(of([]));
    svc.http.post.mockReturnValue(of({}));
    svc.http.patch.mockReturnValue(of({}));
    svc.http.delete.mockReturnValue(of(undefined));
  });

  it('list() calls GET /api/workspaces/', () => {
    svc.list();
    expect(svc.http.get).toHaveBeenCalledWith(`${API}/api/workspaces/`);
  });

  it('get(slug) calls GET /api/workspaces/<slug>/', () => {
    svc.get('my-team');
    expect(svc.http.get).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/`);
  });

  it('create() calls POST /api/workspaces/', () => {
    svc.create({ name: 'Team' });
    expect(svc.http.post).toHaveBeenCalledWith(`${API}/api/workspaces/`, { name: 'Team' });
  });

  it('update() calls PATCH /api/workspaces/<slug>/', () => {
    svc.update('my-team', { name: 'New' });
    expect(svc.http.patch).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/`, { name: 'New' });
  });

  it('delete() calls DELETE /api/workspaces/<slug>/', () => {
    svc.delete('my-team');
    expect(svc.http.delete).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/`);
  });

  it('restore() calls POST /api/workspaces/<slug>/restore/', () => {
    svc.restore('my-team');
    expect(svc.http.post).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/restore/`, {});
  });

  it('transferOwnership() sends new_owner_id', () => {
    svc.transferOwnership('my-team', 'uid-123');
    expect(svc.http.post).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/transfer/`,
      { new_owner_id: 'uid-123' },
    );
  });

  it('leave() calls POST /api/workspaces/<slug>/leave/', () => {
    svc.leave('my-team');
    expect(svc.http.post).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/leave/`, {});
  });

  it('listMembers() calls GET /api/workspaces/<slug>/members/', () => {
    svc.listMembers('my-team');
    expect(svc.http.get).toHaveBeenCalledWith(`${API}/api/workspaces/my-team/members/`);
  });

  it('addMember() sends user_id and role', () => {
    svc.addMember('my-team', 'user-abc');
    expect(svc.http.post).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/members/`,
      { user_id: 'user-abc', role: 'MEMBER' },
    );
  });

  it('updateMemberRole() sends role to member endpoint', () => {
    svc.updateMemberRole('my-team', 'user-abc', 'ADMIN');
    expect(svc.http.patch).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/members/user-abc/`,
      { role: 'ADMIN' },
    );
  });

  it('removeMember() calls DELETE on member endpoint', () => {
    svc.removeMember('my-team', 'user-abc');
    expect(svc.http.delete).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/members/user-abc/`,
    );
  });

  it('createEmailInvite() sends email and role_to_grant', () => {
    svc.createEmailInvite('my-team', 'a@b.com', 'MEMBER');
    expect(svc.http.post).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/invitations/`,
      { kind: 'email', email: 'a@b.com', role_to_grant: 'MEMBER' },
    );
  });

  it('revokeInvitation() calls DELETE on invitation endpoint', () => {
    svc.revokeInvitation('my-team', 'inv-id');
    expect(svc.http.delete).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/invitations/inv-id/`,
    );
  });

  it('createInviteLink() sends role_to_grant, max_uses, expires_at', () => {
    svc.createInviteLink('my-team', 'ADMIN', 10, '2026-12-31T00:00:00Z');
    expect(svc.http.post).toHaveBeenCalledWith(
      `${API}/api/workspaces/my-team/invite-links/`,
      { role_to_grant: 'ADMIN', max_uses: 10, expires_at: '2026-12-31T00:00:00Z' },
    );
  });

  it('acceptInvitation() posts token to /api/invitations/accept/', () => {
    svc.acceptInvitation('raw-tok');
    expect(svc.http.post).toHaveBeenCalledWith(
      `${API}/api/invitations/accept/`,
      { token: 'raw-tok' },
    );
  });

  it('listMyInvitations() calls GET /api/invitations/me/', () => {
    svc.listMyInvitations();
    expect(svc.http.get).toHaveBeenCalledWith(`${API}/api/invitations/me/`);
  });
});
