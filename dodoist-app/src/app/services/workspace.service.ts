import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UserBrief {
  id: string;
  display_name: string;
  email: string;
}

export interface WorkspaceDetail {
  id: string;
  slug: string;
  name: string;
  description: string;
  owner: UserBrief;
  plan: string;
  is_personal: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  delete_scheduled_for: string | null;
}

export interface WorkspaceMember {
  id: string;
  user: UserBrief;
  role: 'OWNER' | 'ADMIN' | 'MEMBER';
  joined_at: string;
}

export interface WorkspaceInvitation {
  id: string;
  kind: 'email' | 'link';
  email: string;
  role_to_grant: 'OWNER' | 'ADMIN' | 'MEMBER';
  invited_by: UserBrief | null;
  created_at: string;
  expires_at: string | null;
  max_uses: number | null;
  use_count: number;
  accepted_at: string | null;
  revoked_at: string | null;
}

@Injectable({ providedIn: 'root' })
export class WorkspaceService {
  private readonly http = inject(HttpClient);

  list(): Observable<WorkspaceDetail[]> {
    return this.http.get<WorkspaceDetail[]>(`${environment.apiBase}/api/workspaces/`);
  }

  get(slug: string): Observable<WorkspaceDetail> {
    return this.http.get<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/${slug}/`);
  }

  create(payload: { name: string; slug?: string; description?: string }): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/`, payload);
  }

  update(slug: string, data: { name?: string; description?: string }): Observable<WorkspaceDetail> {
    return this.http.patch<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/${slug}/`, data);
  }

  delete(slug: string): Observable<WorkspaceDetail> {
    return this.http.delete<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/${slug}/`);
  }

  restore(slug: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/${slug}/restore/`, {});
  }

  transferOwnership(slug: string, newOwnerId: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${environment.apiBase}/api/workspaces/${slug}/transfer/`, {
      new_owner_id: newOwnerId,
    });
  }

  leave(slug: string): Observable<void> {
    return this.http.post<void>(`${environment.apiBase}/api/workspaces/${slug}/leave/`, {});
  }

  listMembers(slug: string): Observable<WorkspaceMember[]> {
    return this.http.get<WorkspaceMember[]>(
      `${environment.apiBase}/api/workspaces/${slug}/members/`,
    );
  }

  addMember(slug: string, userId: string, role = 'MEMBER'): Observable<WorkspaceMember> {
    return this.http.post<WorkspaceMember>(
      `${environment.apiBase}/api/workspaces/${slug}/members/`,
      { user_id: userId, role },
    );
  }

  updateMemberRole(slug: string, userId: string, role: 'ADMIN' | 'MEMBER'): Observable<WorkspaceMember> {
    return this.http.patch<WorkspaceMember>(
      `${environment.apiBase}/api/workspaces/${slug}/members/${userId}/`,
      { role },
    );
  }

  removeMember(slug: string, userId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/workspaces/${slug}/members/${userId}/`,
    );
  }

  listInvitations(slug: string): Observable<WorkspaceInvitation[]> {
    return this.http.get<WorkspaceInvitation[]>(
      `${environment.apiBase}/api/workspaces/${slug}/invitations/`,
    );
  }

  createEmailInvite(slug: string, email: string, role: string): Observable<WorkspaceInvitation> {
    return this.http.post<WorkspaceInvitation>(
      `${environment.apiBase}/api/workspaces/${slug}/invitations/`,
      { kind: 'email', email, role_to_grant: role },
    );
  }

  revokeInvitation(slug: string, id: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/workspaces/${slug}/invitations/${id}/`,
    );
  }

  createInviteLink(
    slug: string,
    role: string,
    maxUses?: number | null,
    expiresAt?: string,
  ): Observable<{ token: string }> {
    return this.http.post<{ token: string }>(
      `${environment.apiBase}/api/workspaces/${slug}/invite-links/`,
      { role_to_grant: role, max_uses: maxUses ?? null, expires_at: expiresAt ?? null },
    );
  }

  acceptInvitation(token: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${environment.apiBase}/api/invitations/accept/`, { token });
  }

  listMyInvitations(): Observable<WorkspaceInvitation[]> {
    return this.http.get<WorkspaceInvitation[]>(`${environment.apiBase}/api/invitations/me/`);
  }
}
