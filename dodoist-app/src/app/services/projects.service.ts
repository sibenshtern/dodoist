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
  active_sprint: { id: string; name: string; status: string } | null;
  created_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  key: string;
  type: string;
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

  create(workspaceSlug: string, data: ProjectCreatePayload): Observable<Project> {
    return this.http.post<Project>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/projects/`,
      data,
    );
  }
}
