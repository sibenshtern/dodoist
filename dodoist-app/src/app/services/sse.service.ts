import { inject, Injectable, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';
import { NotificationsService } from './notifications.service';
import { environment } from '../../environments/environment';

const BACKOFF_STEPS = [1_000, 2_000, 5_000, 15_000, 30_000];

@Injectable({ providedIn: 'root' })
export class SseService implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly notifService = inject(NotificationsService);

  private es: EventSource | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private retryIndex = 0;
  private running = false;

  start(): void {
    if (this.running) return;
    this.running = true;
    this.connect();
  }

  stop(): void {
    this.running = false;
    this.es?.close();
    this.es = null;
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  ngOnDestroy(): void {
    this.stop();
  }

  private async connect(): Promise<void> {
    if (!this.running) return;

    // Require an active access token — if there's none, retry after backoff.
    if (!this.authService.isAuthenticated()) {
      this.scheduleRetry();
      return;
    }

    try {
      const { token } = await firstValueFrom(
        this.http.post<{ token: string }>(
          `${environment.apiBase}/api/auth/sse-token/`,
          {},
        ),
      );

      const url = `${environment.apiBase}/api/events/?token=${encodeURIComponent(token)}`;
      const es = new EventSource(url);
      this.es = es;

      es.onopen = () => {
        this.retryIndex = 0;
        // Re-sync unread notifications on (re)connect.
        this.notifService.list({ limit: 50 }).subscribe({ error: console.error });
      };

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as { type: string; id: string };
          if (payload.type === 'notification') {
            // Refresh the notification list to pick up the new entry.
            this.notifService.list({ limit: 50 }).subscribe({ error: console.error });
          }
        } catch {
          // Ignore malformed frames.
        }
      };

      es.onerror = () => {
        es.close();
        this.es = null;
        if (this.running) {
          this.scheduleRetry();
        }
      };
    } catch {
      if (this.running) {
        this.scheduleRetry();
      }
    }
  }

  private scheduleRetry(): void {
    const delay = BACKOFF_STEPS[Math.min(this.retryIndex, BACKOFF_STEPS.length - 1)];
    this.retryIndex++;
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      this.connect();
    }, delay);
  }
}
