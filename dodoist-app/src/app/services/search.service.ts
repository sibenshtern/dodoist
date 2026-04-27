import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface SearchTask {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: string;
  project: string;
  project_name: string;
  project_color: string;
  assigned_to: { id: string; display_name: string; email: string } | null;
  due_date: string | null;
  is_private: boolean;
}

@Injectable({ providedIn: 'root' })
export class SearchService {
  private readonly http = inject(HttpClient);

  search(q: string): Observable<SearchTask[]> {
    const params = new HttpParams().set('q', q);
    return this.http.get<SearchTask[]>(`${environment.apiBase}/api/tasks/search/`, { params });
  }
}
