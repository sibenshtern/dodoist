import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Notification {
  id: string;
  type: string;
  message: string;
  task_id: string | null;
  project_id: string | null;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  actor: { id: string; display_name: string } | null;
}

@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBase}/api/notifications`;

  readonly notifications = signal<Notification[]>([]);
  readonly unreadCount = computed(
    () => this.notifications().filter(n => !n.is_read).length,
  );
  readonly latest = computed(() => this.notifications().slice(0, 5));

  list(params: { is_read?: boolean; type?: string; limit?: number } = {}): Observable<Notification[]> {
    let httpParams = new HttpParams();
    if (params.is_read !== undefined) httpParams = httpParams.set('is_read', String(params.is_read));
    if (params.type) httpParams = httpParams.set('type', params.type);
    if (params.limit) httpParams = httpParams.set('limit', String(params.limit));

    return this.http.get<Notification[]>(this.base + '/', { params: httpParams }).pipe(
      tap(list => this.notifications.set(list)),
    );
  }

  markRead(id: string): Observable<Notification> {
    return this.http.patch<Notification>(`${this.base}/${id}/`, { is_read: true }).pipe(
      tap(updated => {
        this.notifications.update(list =>
          list.map(n => (n.id === id ? updated : n)),
        );
      }),
    );
  }

  markAllRead(): Observable<{ marked_count: number }> {
    return this.http.post<{ marked_count: number }>(`${this.base}/read-all/`, {}).pipe(
      tap(() => {
        this.notifications.update(list =>
          list.map(n => ({ ...n, is_read: true })),
        );
      }),
    );
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}/`).pipe(
      tap(() => {
        this.notifications.update(list => list.filter(n => n.id !== id));
      }),
    );
  }
}
