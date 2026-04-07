import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string;
  timezone: string;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  plan: string;
  is_personal: boolean;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly http = inject(HttpClient);

  readonly currentUser = signal<UserProfile | null>(null);
  readonly currentWorkspace = signal<Workspace | null>(null);

  loadCurrentUser(): Observable<UserProfile> {
    return this.http
      .get<UserProfile>(`${environment.apiBase}/api/users/me`)
      .pipe(tap(user => this.currentUser.set(user)));
  }

  loadWorkspaces(): Observable<Workspace[]> {
    return this.http
      .get<Workspace[]>(`${environment.apiBase}/api/workspaces/`)
      .pipe(
        tap(workspaces => {
          const personal = workspaces.find(w => w.is_personal) ?? workspaces[0] ?? null;
          this.currentWorkspace.set(personal);
        }),
      );
  }
}
