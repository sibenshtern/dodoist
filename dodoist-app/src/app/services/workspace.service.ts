import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface WorkspaceDetail {
  id: string;
  slug: string;
  name: string;
  description: string;
  owner: { id: string; display_name: string; email: string };
  plan: string;
  is_personal: boolean;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  delete_scheduled_for?: string | null;
}

export interface WorkspaceMember {
  id: string;
  user: { id: string; display_name: string; email: string };
  role: 'OWNER' | 'ADMIN' | 'MEMBER';
  joined_at: string;
}

export interface WorkspaceInvitation {
  id: string;
  kind: 'email' | 'link';
  email: string;
  role_to_grant: string;
  invited_by: { id: string; display_name: string; email: string } | null;
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
  private readonly base = `${environment.apiBase}/api/workspaces`;

  list(): Observable<WorkspaceDetail[]> {
    return this.http.get<WorkspaceDetail[]>(`${this.base}/`);
  }

  create(data: { name: string; slug?: string; description?: string }): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.base}/`, data);
  }

  get(slug: string): Observable<WorkspaceDetail> {
    return this.http.get<WorkspaceDetail>(`${this.base}/${slug}/`);
  }

  update(slug: string, data: { name?: string; description?: string }): Observable<WorkspaceDetail> {
    return this.http.patch<WorkspaceDetail>(`${this.base}/${slug}/`, data);
  }

  listMembers(slug: string): Observable<WorkspaceMember[]> {
    return this.http.get<WorkspaceMember[]>(`${this.base}/${slug}/members/`);
  }

  addMember(slug: string, userId: string): Observable<WorkspaceMember> {
    return this.http.post<WorkspaceMember>(`${this.base}/${slug}/members/`, { user_id: userId });
  }

  removeMember(slug: string, userId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${slug}/members/${userId}/`);
  }

  updateMemberRole(slug: string, userId: string, role: 'ADMIN' | 'MEMBER'): Observable<WorkspaceMember> {
    return this.http.patch<WorkspaceMember>(`${this.base}/${slug}/members/${userId}/`, { role });
  }

  delete(slug: string): Observable<WorkspaceDetail> {
    return this.http.delete<WorkspaceDetail>(`${this.base}/${slug}/`);
  }

  restore(slug: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.base}/${slug}/restore/`, {});
  }

  transferOwnership(slug: string, newOwnerId: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${this.base}/${slug}/transfer/`, { new_owner_id: newOwnerId });
  }

  leave(slug: string): Observable<void> {
    return this.http.post<void>(`${this.base}/${slug}/leave/`, {});
  }

  listInvitations(slug: string): Observable<WorkspaceInvitation[]> {
    return this.http.get<WorkspaceInvitation[]>(`${this.base}/${slug}/invitations/`);
  }

  createEmailInvite(slug: string, email: string, role: string): Observable<WorkspaceInvitation> {
    return this.http.post<WorkspaceInvitation>(`${this.base}/${slug}/invitations/`, { email, role });
  }

  revokeInvitation(slug: string, id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${slug}/invitations/${id}/`);
  }

  createInviteLink(slug: string, role: string, maxUses?: number, expiresAt?: string): Observable<{ token: string }> {
    return this.http.post<{ token: string }>(`${this.base}/${slug}/invite-links/`, { role, max_uses: maxUses, expires_at: expiresAt });
  }

  acceptInvitation(token: string): Observable<WorkspaceDetail> {
    return this.http.post<WorkspaceDetail>(`${environment.apiBase}/api/invitations/accept/`, { token });
  }

  listMyInvitations(): Observable<WorkspaceInvitation[]> {
    return this.http.get<WorkspaceInvitation[]>(`${environment.apiBase}/api/invitations/me/`);
  }
}
