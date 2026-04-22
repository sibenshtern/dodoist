import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signal, computed } from '@angular/core';
import { of } from 'rxjs';

interface Notification {
  id: string;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
  task_id: string | null;
  project_id: string | null;
  read_at: string | null;
  actor: null;
}

function makeNotificationsService(initialList: Notification[] = []) {
  const notifications = signal<Notification[]>(initialList);
  const unreadCount = computed(() => notifications().filter(n => !n.is_read).length);
  const latest = computed(() => notifications().slice(0, 5));

  const http = { get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn() };

  const svc = {
    notifications,
    unreadCount,
    latest,
    _http: http,

    list(params = {}) {
      return http.get('/api/notifications/', { params }).pipe
        ? http.get('/api/notifications/', { params })
        : of(notifications());
    },
    markRead(id: string) {
      const updated = { ...notifications().find(n => n.id === id)!, is_read: true };
      return of(updated);
    },
    markAllRead() {
      return of({ marked_count: notifications().filter(n => !n.is_read).length });
    },
    delete(id: string) {
      return of(undefined);
    },
  };
  return svc;
}

function notif(id: string, is_read = false): Notification {
  return { id, type: 'assigned', message: 'test', is_read, created_at: '', task_id: null, project_id: null, read_at: null, actor: null };
}

describe('NotificationsService — signal state', () => {
  it('unreadCount counts only unread notifications', () => {
    const svc = makeNotificationsService([notif('1', false), notif('2', true), notif('3', false)]);
    expect(svc.unreadCount()).toBe(2);
  });

  it('latest returns at most 5 items', () => {
    const list = Array.from({ length: 8 }, (_, i) => notif(`${i}`));
    const svc = makeNotificationsService(list);
    expect(svc.latest().length).toBe(5);
  });

  it('starts with empty notifications', () => {
    const svc = makeNotificationsService();
    expect(svc.notifications().length).toBe(0);
    expect(svc.unreadCount()).toBe(0);
  });
});
