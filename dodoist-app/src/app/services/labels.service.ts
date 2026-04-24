import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Label {
  id: string;
  name: string;
  color: string;
  workspace: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class LabelsService {
  private readonly http = inject(HttpClient);

  list(workspaceSlug: string): Observable<Label[]> {
    return this.http.get<Label[]>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/labels/`,
    );
  }

  create(workspaceSlug: string, data: { name: string; color: string }): Observable<Label> {
    return this.http.post<Label>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/labels/`,
      data,
    );
  }

  update(workspaceSlug: string, labelId: string, data: { name?: string; color?: string }): Observable<Label> {
    return this.http.patch<Label>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/labels/${labelId}/`,
      data,
    );
  }

  delete(workspaceSlug: string, labelId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/workspaces/${workspaceSlug}/labels/${labelId}/`,
    );
  }
}
