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
  global_role: string;
  active_workspace?: { id: string; slug: string; name: string; is_personal: boolean } | null;
}

export interface UserPreferences {
  theme: string;
  language: string;
  notification_channels: { email: boolean; push: boolean; in_app: boolean };
  digest_frequency: string;
  default_view: string;
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
  readonly workspaces = signal<Workspace[]>([]);

  loadCurrentUser(): Observable<UserProfile> {
    return this.http
      .get<UserProfile>(`${environment.apiBase}/api/users/me`)
      .pipe(tap(user => {
        this.currentUser.set(user);
        if (user.active_workspace) {
          this.currentWorkspace.set({
            id: user.active_workspace.id,
            slug: user.active_workspace.slug,
            name: user.active_workspace.name,
            plan: '',
            is_personal: user.active_workspace.is_personal,
          });
        }
      }));
  }

  loadWorkspaces(): Observable<Workspace[]> {
    return this.http
      .get<Workspace[]>(`${environment.apiBase}/api/workspaces/`)
      .pipe(
        tap(workspaces => {
          this.workspaces.set(workspaces);
          if (!this.currentWorkspace()) {
            const personal = workspaces.find(w => w.is_personal) ?? workspaces[0] ?? null;
            this.currentWorkspace.set(personal);
          }
        }),
      );
  }

  switchWorkspace(workspace: Workspace): Observable<UserProfile> {
    return this.http
      .patch<UserProfile>(
        `${environment.apiBase}/api/users/me/active-workspace/`,
        { workspace_slug: workspace.slug },
      )
      .pipe(tap(user => {
        this.currentUser.set(user);
        this.currentWorkspace.set(workspace);
      }));
  }

  updateProfile(userId: string, data: Partial<Pick<UserProfile, 'display_name' | 'avatar_url' | 'timezone'>>): Observable<UserProfile> {
    return this.http.patch<UserProfile>(
      `${environment.apiBase}/api/users/${userId}/`,
      data,
    ).pipe(tap(user => this.currentUser.set(user)));
  }

  getPreferences(userId: string): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(
      `${environment.apiBase}/api/users/${userId}/preferences/`,
    );
  }

  updatePreferences(userId: string, data: Partial<UserPreferences>): Observable<UserPreferences> {
    return this.http.patch<UserPreferences>(
      `${environment.apiBase}/api/users/${userId}/preferences/`,
      data,
    );
  }

  changePassword(userId: string, currentPassword: string, newPassword: string): Observable<UserProfile> {
    return this.http.patch<UserProfile>(
      `${environment.apiBase}/api/users/${userId}/`,
      { current_password: currentPassword, new_password: newPassword },
    );
  }
}
