import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaskSnapshot {
  id: string;
  project: string;
  sprint: string | null;
  snapshot_date: string;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  overdue_tasks: number;
  total_story_points: number;
  completed_story_points: number;
}

export interface ProjectSummary {
  total_tasks: number;
  open_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  total_story_points: number;
  completed_story_points: number;
  velocity: number;
  progress: number;
  active_sprint: string | null;
}

export interface MemberMetric {
  user: {
    id: string;
    display_name: string;
    email: string;
  };
  tasks_created: number;
  tasks_completed: number;
  tasks_assigned: number;
  comments_posted: number;
  logged_minutes: number;
}

export interface UserMetric {
  tasks_created: number;
  tasks_completed: number;
  tasks_assigned: number;
  comments_posted: number;
  logged_minutes: number;
}

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  getSnapshots(
    projectId: string,
    params?: { sprint_id?: string; since?: string; until?: string },
  ): Observable<TaskSnapshot[]> {
    let httpParams = new HttpParams();
    if (params?.sprint_id) httpParams = httpParams.set('sprint_id', params.sprint_id);
    if (params?.since) httpParams = httpParams.set('since', params.since);
    if (params?.until) httpParams = httpParams.set('until', params.until);
    return this.http.get<TaskSnapshot[]>(
      `${this.base}/api/projects/${projectId}/snapshots/`,
      { params: httpParams, withCredentials: true },
    );
  }

  getSummary(projectId: string): Observable<ProjectSummary> {
    return this.http.get<ProjectSummary>(
      `${this.base}/api/projects/${projectId}/metrics/summary/`,
      { withCredentials: true },
    );
  }

  getMemberMetrics(
    projectId: string,
    params?: { since?: string; until?: string },
  ): Observable<MemberMetric[]> {
    let httpParams = new HttpParams();
    if (params?.since) httpParams = httpParams.set('since', params.since);
    if (params?.until) httpParams = httpParams.set('until', params.until);
    return this.http.get<MemberMetric[]>(
      `${this.base}/api/projects/${projectId}/metrics/users/`,
      { params: httpParams, withCredentials: true },
    );
  }

  getMyMetrics(
    userId: string,
    params?: { since?: string; until?: string; project_id?: string },
  ): Observable<UserMetric> {
    let httpParams = new HttpParams();
    if (params?.since) httpParams = httpParams.set('since', params.since);
    if (params?.until) httpParams = httpParams.set('until', params.until);
    if (params?.project_id) httpParams = httpParams.set('project_id', params.project_id);
    return this.http.get<UserMetric>(
      `${this.base}/api/users/${userId}/metrics/`,
      { params: httpParams, withCredentials: true },
    );
  }
}
