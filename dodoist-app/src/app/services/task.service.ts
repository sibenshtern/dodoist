import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaskLabel {
  id: string;
  name: string;
  color: string;
}

export interface TaskUser {
  id: string;
  display_name: string;
  email: string;
}

export interface Task {
  id: string;
  project: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  story_points: number | null;
  due_date: string | null;
  is_overdue: boolean;
  is_private: boolean;
  assigned_to: TaskUser | null;
  created_by: TaskUser;
  labels: TaskLabel[];
}

export interface TaskDetail extends Task {
  description: unknown | null;
  parent_task: string | null;
  sprint: string | null;
  board_column: string | null;
  story_points: number | null;
  start_date: string | null;
  reminder_at: string | null;
  position: number;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface TaskCreatePayload {
  title: string;
  task_type: string;
  priority: string;
  is_private: boolean;
  project_id?: string;
  status?: string;
  description?: unknown;
  assigned_to_id?: string;
  sprint_id?: string;
  parent_task_id?: string;
  story_points?: number;
  due_date?: string;
  start_date?: string;
  reminder_at?: string;
}

export interface Comment {
  id: string;
  task_id: string;
  author: TaskUser & { avatar_url: string };
  parent_comment_id: string | null;
  body: unknown;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export interface TimeLog {
  id: string;
  user: TaskUser;
  logged_minutes: number;
  logged_date: string;
  description: string;
  created_at: string;
}

export interface ActivityLogEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  actor: { id: string; display_name: string };
  action: string;
  old_value: unknown | null;
  new_value: unknown | null;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class TaskService {
  private readonly http = inject(HttpClient);

  getMyTasks(statuses?: string[]): Observable<Task[]> {
    const params = statuses?.length
      ? new HttpParams().set('status', statuses.join(','))
      : undefined;
    return this.http.get<Task[]>(`${environment.apiBase}/api/tasks/my/`, { params });
  }

  updateTask(taskId: string, patch: Partial<Pick<Task, 'status' | 'priority'>> & { title?: string; assigned_to_id?: string | null; description?: unknown }): Observable<Task> {
    return this.http.patch<Task>(`${environment.apiBase}/api/tasks/${taskId}/`, patch);
  }

  createTask(payload: TaskCreatePayload): Observable<Task> {
    return this.http.post<Task>(`${environment.apiBase}/api/tasks/`, payload);
  }

  addLabel(taskId: string, labelId: string): Observable<void> {
    return this.http.post<void>(
      `${environment.apiBase}/api/tasks/${taskId}/labels/`,
      { label_id: labelId },
    );
  }

  getTask(id: string): Observable<TaskDetail> {
    return this.http.get<TaskDetail>(`${environment.apiBase}/api/tasks/${id}/`);
  }

  deleteTask(id: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/tasks/${id}/`);
  }

  restoreTask(id: string): Observable<TaskDetail> {
    return this.http.post<TaskDetail>(`${environment.apiBase}/api/tasks/${id}/restore/`, {});
  }

  moveToColumn(taskId: string, columnId: string): Observable<TaskDetail> {
    return this.http.post<TaskDetail>(
      `${environment.apiBase}/api/tasks/${taskId}/move-column/`,
      { column_id: columnId },
    );
  }

  getComments(taskId: string): Observable<Comment[]> {
    return this.http.get<Comment[]>(`${environment.apiBase}/api/tasks/${taskId}/comments/`);
  }

  addComment(taskId: string, body: unknown, parentId?: string): Observable<Comment> {
    return this.http.post<Comment>(
      `${environment.apiBase}/api/tasks/${taskId}/comments/`,
      { body, ...(parentId ? { parent_comment_id: parentId } : {}) },
    );
  }

  updateComment(commentId: string, body: unknown): Observable<Comment> {
    return this.http.patch<Comment>(`${environment.apiBase}/api/comments/${commentId}/`, { body });
  }

  deleteComment(commentId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/comments/${commentId}/`);
  }

  getTimeLogs(taskId: string): Observable<{ data: TimeLog[]; meta: { total_minutes: number } }> {
    return this.http.get<{ data: TimeLog[]; meta: { total_minutes: number } }>(
      `${environment.apiBase}/api/tasks/${taskId}/time-logs/`,
    );
  }

  addTimeLog(taskId: string, payload: { logged_minutes: number; logged_date: string; description?: string }): Observable<TimeLog> {
    return this.http.post<TimeLog>(`${environment.apiBase}/api/tasks/${taskId}/time-logs/`, payload);
  }

  deleteTimeLog(logId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/time-logs/${logId}/`);
  }

  getActivity(taskId: string): Observable<ActivityLogEntry[]> {
    return this.http.get<ActivityLogEntry[]>(`${environment.apiBase}/api/tasks/${taskId}/activity/`);
  }

  addReaction(commentId: string, emoji: string): Observable<void> {
    return this.http.post<void>(`${environment.apiBase}/api/comments/${commentId}/reactions/`, { emoji });
  }

  removeReaction(commentId: string, emoji: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/comments/${commentId}/reactions/${emoji}/`);
  }

  getWorkspaceProjects(slug: string): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiBase}/api/workspaces/${slug}/projects/`);
  }

  getWorkspaceLabels(slug: string): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiBase}/api/workspaces/${slug}/labels/`);
  }

  getProjectMembers(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiBase}/api/projects/${projectId}/members/`);
  }

  getProjectSprints(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(`${environment.apiBase}/api/projects/${projectId}/sprints/?status=active,planned`);
  }
}
