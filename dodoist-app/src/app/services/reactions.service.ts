import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Reaction {
  id: string;
  comment_id: string;
  user: { id: string; display_name: string };
  emoji: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ReactionsService {
  private readonly http = inject(HttpClient);

  add(commentId: string, emoji: string): Observable<Reaction> {
    return this.http.post<Reaction>(
      `${environment.apiBase}/api/comments/${commentId}/reactions/`,
      { emoji },
    );
  }

  remove(commentId: string, emoji: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/comments/${commentId}/reactions/${emoji}/`,
    );
  }
}
