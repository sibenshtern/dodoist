import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Board {
  id: string;
  project_id: string;
  name: string;
  type: string;
  is_default: boolean;
  created_at: string;
}

export interface BoardColumn {
  id: string;
  board_id: string;
  name: string;
  status_mapping: string;
  position: number;
  wip_limit: number | null;
}

export interface BoardColumnPayload {
  name: string;
  status_mapping: string;
  position: number;
  wip_limit?: number | null;
}

@Injectable({ providedIn: 'root' })
export class BoardsService {
  private readonly http = inject(HttpClient);

  listBoards(projectId: string): Observable<Board[]> {
    return this.http.get<Board[]>(
      `${environment.apiBase}/api/projects/${projectId}/boards/`,
    );
  }

  createBoard(projectId: string, data: { name: string; type: string; is_default?: boolean }): Observable<Board> {
    return this.http.post<Board>(
      `${environment.apiBase}/api/projects/${projectId}/boards/`,
      data,
    );
  }

  updateBoard(boardId: string, data: { name?: string; is_default?: boolean }): Observable<Board> {
    return this.http.patch<Board>(
      `${environment.apiBase}/api/boards/${boardId}/`,
      data,
    );
  }

  deleteBoard(boardId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/boards/${boardId}/`,
    );
  }

  getColumns(boardId: string): Observable<BoardColumn[]> {
    return this.http.get<BoardColumn[]>(
      `${environment.apiBase}/api/boards/${boardId}/columns/`,
    );
  }

  createColumn(boardId: string, data: BoardColumnPayload): Observable<BoardColumn> {
    return this.http.post<BoardColumn>(
      `${environment.apiBase}/api/boards/${boardId}/columns/`,
      data,
    );
  }

  updateColumn(boardId: string, columnId: string, data: Partial<BoardColumnPayload>): Observable<BoardColumn> {
    return this.http.patch<BoardColumn>(
      `${environment.apiBase}/api/boards/${boardId}/columns/${columnId}/`,
      data,
    );
  }

  deleteColumn(boardId: string, columnId: string): Observable<void> {
    return this.http.delete<void>(
      `${environment.apiBase}/api/boards/${boardId}/columns/${columnId}/`,
    );
  }
}
