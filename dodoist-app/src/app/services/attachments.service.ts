import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Attachment {
  id: string;
  filename: string;
  file_size_bytes: number;
  mime_type: string;
  download_url: string;
  uploaded_by: { id: string; display_name: string; email: string };
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AttachmentsService {
  private readonly http = inject(HttpClient);

  list(taskId: string): Observable<Attachment[]> {
    return this.http
      .get<{ results: Attachment[] }>(`${environment.apiBase}/api/tasks/${taskId}/attachments/`)
      .pipe(map(r => r.results));
  }

  upload(taskId: string, file: File): Observable<Attachment> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<Attachment>(
      `${environment.apiBase}/api/tasks/${taskId}/attachments/`,
      form,
    );
  }

  delete(attachmentId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/attachments/${attachmentId}/`,
    );
  }

  isImage(mimeType: string): boolean {
    return mimeType.startsWith('image/');
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
}
