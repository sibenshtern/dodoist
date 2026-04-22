import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TimeLog {
  id: string;
  user: { id: string; display_name: string; email: string };
  logged_minutes: number;
  logged_date: string;
  description: string;
  created_at: string;
}

export interface TimeLogListResponse {
  data: TimeLog[];
  meta: { total_minutes: number };
}

export interface TimeLogCreatePayload {
  logged_minutes: number;
  logged_date: string;
  description?: string;
}

@Injectable({ providedIn: 'root' })
export class TimeLogsService {
  private readonly http = inject(HttpClient);

  listForTask(taskId: string): Observable<TimeLogListResponse> {
    return this.http.get<TimeLogListResponse>(
      `${environment.apiBase}/api/tasks/${taskId}/time-logs/`,
    );
  }

  create(taskId: string, payload: TimeLogCreatePayload): Observable<TimeLog> {
    return this.http.post<TimeLog>(
      `${environment.apiBase}/api/tasks/${taskId}/time-logs/`,
      payload,
    );
  }

  update(logId: string, payload: Partial<TimeLogCreatePayload>): Observable<TimeLog> {
    return this.http.patch<TimeLog>(
      `${environment.apiBase}/api/time-logs/${logId}/`,
      payload,
    );
  }

  delete(logId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/time-logs/${logId}/`);
  }
}
