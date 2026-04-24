import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Project {
  id: string;
  name: string;
  key: string;
  type: string;
  status: string;
  color: string;
  description: string;
  is_private: boolean;
  member_count: number;
  current_user_role: string | null;
  active_sprint: { id: string; name: string; status: string; start_date: string | null; end_date: string | null } | null;
  created_at: string;
  archived_at: string | null;
}

export interface ProjectMember {
  id: string;
  user: { id: string; display_name: string; email: string; avatar_url: string };
  role: string;
  joined_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  key: string;
  type: string;
  description?: string;
  color?: string;
  is_private?: boolean;
}

export interface ProjectUpdatePayload {
  name?: string;
  description?: string;
  color?: string;
  is_private?: boolean;
}

@Injectable({ providedIn: 'root' })
export class ProjectsService {
  private readonly http = inject(HttpClient);

  list(workspaceSlug: string): Observable<Project[]> {
    return this.http.get<Project[]>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/projects/`,
    );
  }

  get(projectId: string): Observable<Project> {
    return this.http.get<Project>(
      `${environment.apiBase}/api/projects/${projectId}/`,
    );
  }

  create(workspaceSlug: string, data: ProjectCreatePayload): Observable<Project> {
    return this.http.post<Project>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/projects/`,
      data,
    );
  }

  update(projectId: string, data: ProjectUpdatePayload): Observable<Project> {
    return this.http.patch<Project>(
      `${environment.apiBase}/api/projects/${projectId}/`,
      data,
    );
  }

  archive(projectId: string): Observable<Project> {
    return this.http.post<Project>(
      `${environment.apiBase}/api/projects/${projectId}/archive/`,
      {},
    );
  }

  unarchive(projectId: string): Observable<Project> {
    return this.http.post<Project>(
      `${environment.apiBase}/api/projects/${projectId}/unarchive/`,
      {},
    );
  }

  getMembers(projectId: string): Observable<ProjectMember[]> {
    return this.http.get<ProjectMember[]>(
      `${environment.apiBase}/api/projects/${projectId}/members/`,
    );
  }

  addMember(projectId: string, userId: string, role: string): Observable<ProjectMember> {
    return this.http.post<ProjectMember>(
      `${environment.apiBase}/api/projects/${projectId}/members/`,
      { user_id: userId, role },
    );
  }

  updateMemberRole(projectId: string, userId: string, role: string): Observable<ProjectMember> {
    return this.http.patch<ProjectMember>(
      `${environment.apiBase}/api/projects/${projectId}/members/${userId}/`,
      { role },
    );
  }

  removeMember(projectId: string, userId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/projects/${projectId}/members/${userId}/`,
    );
  }
}
