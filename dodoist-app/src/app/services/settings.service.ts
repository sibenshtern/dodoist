import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { UserService, UserProfile, UserPreferences } from './user.service';

export interface UserSession {
  id: string;
  ip_address: string | null;
  device_info: string;
  created_at: string;
  expires_at: string;
}

@Injectable({ providedIn: 'root' })
export class SettingsService {
  private readonly http = inject(HttpClient);
  private readonly userService = inject(UserService);

  updateProfile(userId: string, data: Partial<Pick<UserProfile, 'display_name' | 'timezone'>>): Observable<UserProfile> {
    return this.userService.updateProfile(userId, data);
  }

  getPreferences(userId: string): Observable<UserPreferences> {
    return this.userService.getPreferences(userId);
  }

  updatePreferences(userId: string, data: Partial<UserPreferences>): Observable<UserPreferences> {
    return this.userService.updatePreferences(userId, data);
  }

  changePassword(userId: string, currentPassword: string, newPassword: string): Observable<UserProfile> {
    return this.userService.changePassword(userId, currentPassword, newPassword);
  }

  uploadAvatar(userId: string, file: File): Observable<UserProfile> {
    const fd = new FormData();
    fd.append('avatar', file);
    return this.http.post<UserProfile>(
      `${environment.apiBase}/api/users/${userId}/avatar/`,
      fd,
    ).pipe(tap(user => this.userService.currentUser.set(user)));
  }

  listSessions(): Observable<UserSession[]> {
    return this.http.get<UserSession[]>(`${environment.apiBase}/api/auth/sessions/`);
  }

  revokeSession(sessionId: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiBase}/api/auth/sessions/${sessionId}/`);
  }
}
