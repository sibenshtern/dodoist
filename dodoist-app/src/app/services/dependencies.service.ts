import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TaskDependency {
  id: string;
  task_id: string;
  depends_on_task: { id: string; title: string; status: string; type: string };
  type: string;
  created_by: { id: string; display_name: string };
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class DependenciesService {
  private readonly http = inject(HttpClient);

  list(taskId: string): Observable<TaskDependency[]> {
    return this.http.get<TaskDependency[]>(
      `${environment.apiBase}/api/tasks/${taskId}/dependencies/`,
    );
  }

  add(taskId: string, dependsOnId: string, type: string): Observable<TaskDependency> {
    return this.http.post<TaskDependency>(
      `${environment.apiBase}/api/tasks/${taskId}/dependencies/`,
      { depends_on_task_id: dependsOnId, type },
    );
  }

  update(dependencyId: string, type: string): Observable<TaskDependency> {
    return this.http.patch<TaskDependency>(
      `${environment.apiBase}/api/dependencies/${dependencyId}/`,
      { type },
    );
  }

  delete(dependencyId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/dependencies/${dependencyId}/`,
    );
  }
}
