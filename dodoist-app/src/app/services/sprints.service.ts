import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Sprint {
  id: string;
  project_id: string;
  name: string;
  goal: string;
  status: 'planned' | 'active' | 'completed';
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface SprintDetail extends Sprint {
  task_stats: {
    total: number;
    completed: number;
    in_progress: number;
    total_story_points: number;
    completed_story_points: number;
  };
}

export interface SprintCreatePayload {
  name: string;
  goal?: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface SprintCompletePayload {
  incomplete_tasks_action: 'backlog' | 'next_sprint';
  next_sprint_id?: string | null;
}

@Injectable({ providedIn: 'root' })
export class SprintsService {
  private readonly http = inject(HttpClient);

  list(projectId: string): Observable<Sprint[]> {
    return this.http.get<Sprint[]>(
      `${environment.apiBase}/api/projects/${projectId}/sprints/`,
    );
  }

  getDetail(sprintId: string): Observable<SprintDetail> {
    return this.http.get<SprintDetail>(
      `${environment.apiBase}/api/sprints/${sprintId}/`,
    );
  }

  create(projectId: string, data: SprintCreatePayload): Observable<Sprint> {
    return this.http.post<Sprint>(
      `${environment.apiBase}/api/projects/${projectId}/sprints/`,
      data,
    );
  }

  update(sprintId: string, data: Partial<SprintCreatePayload>): Observable<Sprint> {
    return this.http.patch<Sprint>(
      `${environment.apiBase}/api/sprints/${sprintId}/`,
      data,
    );
  }

  delete(sprintId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/sprints/${sprintId}/`,
    );
  }

  start(sprintId: string): Observable<Sprint> {
    return this.http.post<Sprint>(
      `${environment.apiBase}/api/sprints/${sprintId}/start/`,
      {},
    );
  }

  complete(sprintId: string, data: SprintCompletePayload): Observable<Sprint> {
    return this.http.post<Sprint>(
      `${environment.apiBase}/api/sprints/${sprintId}/complete/`,
      data,
    );
  }

  addTask(sprintId: string, taskId: string): Observable<void> {
    return this.http.post<void>(
      `${environment.apiBase}/api/sprints/${sprintId}/tasks/`,
      { task_id: taskId },
    );
  }

  removeTask(sprintId: string, taskId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/sprints/${sprintId}/tasks/${taskId}/`,
    );
  }
}
