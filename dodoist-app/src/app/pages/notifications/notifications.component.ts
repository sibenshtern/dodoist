import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { NotificationsService, Notification } from '../../services/notifications.service';
import { DatePipe } from '@angular/common';

const TYPE_LABELS: Record<string, string> = {
  assigned: 'Assignment',
  mentioned: 'Mention',
  commented: 'Comment',
  status_changed: 'Status change',
  due_soon: 'Due soon',
  overdue: 'Overdue',
  invited: 'Invitation',
  role_changed: 'Role change',
};

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [TuiIcon, RouterLink, DatePipe],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss',
})
export class NotificationsComponent implements OnInit {
  readonly svc = inject(NotificationsService);

  ngOnInit(): void {
    this.svc.list({ limit: 100 }).subscribe({ error: console.error });
  }

  typeLabel(type: string): string {
    return TYPE_LABELS[type] ?? type;
  }

  markRead(n: Notification, event: Event): void {
    event.stopPropagation();
    if (!n.is_read) {
      this.svc.markRead(n.id).subscribe({ error: console.error });
    }
  }

  markAllRead(): void {
    this.svc.markAllRead().subscribe({ error: console.error });
  }

  remove(n: Notification, event: Event): void {
    event.stopPropagation();
    this.svc.delete(n.id).subscribe({ error: console.error });
  }
}
