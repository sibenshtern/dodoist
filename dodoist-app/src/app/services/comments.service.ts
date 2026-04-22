import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CommentAuthor {
  id: string;
  display_name: string;
  email: string;
  avatar_url: string;
}

export interface Comment {
  id: string;
  task_id: string;
  author: CommentAuthor;
  parent_comment_id: string | null;
  body: unknown;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class CommentsService {
  private readonly http = inject(HttpClient);

  list(taskId: string): Observable<Comment[]> {
    return this.http.get<Comment[]>(`${environment.apiBase}/api/tasks/${taskId}/comments/`);
  }

  get(commentId: string): Observable<Comment> {
    return this.http.get<Comment>(`${environment.apiBase}/api/comments/${commentId}/`);
  }

  create(taskId: string, body: unknown, parentId?: string): Observable<Comment> {
    return this.http.post<Comment>(
      `${environment.apiBase}/api/tasks/${taskId}/comments/`,
      { body, ...(parentId ? { parent_comment_id: parentId } : {}) },
    );
  }

  update(commentId: string, body: unknown): Observable<Comment> {
    return this.http.patch<Comment>(`${environment.apiBase}/api/comments/${commentId}/`, { body });
  }

  delete(commentId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/comments/${commentId}/`);
  }
}
