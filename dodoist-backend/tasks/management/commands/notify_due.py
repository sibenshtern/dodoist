from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Task
from users.models import Notification, NotificationType
from users.services import NotificationService


class Command(BaseCommand):
    help = "Create due_soon and overdue notifications for tasks approaching or past their due date."

    def handle(self, *args, **options):
        now = timezone.now()
        window_end = now + timezone.timedelta(hours=24)
        today = now.date()

        due_soon_qs = Task.objects.filter(
            due_date__gt=now,
            due_date__lte=window_end,
            deleted_at__isnull=True,
        ).exclude(status__in=["done", "cancelled"]).select_related("assigned_to", "created_by")

        due_soon_count = 0
        for task in due_soon_qs:
            recipients = {task.created_by}
            if task.assigned_to:
                recipients.add(task.assigned_to)
            for recipient in recipients:
                already = Notification.objects.filter(
                    recipient=recipient,
                    type=NotificationType.DUE_SOON,
                    task_id=task.pk,
                    created_at__date=today,
                ).exists()
                if not already:
                    NotificationService.create(
                        recipient=recipient,
                        notification_type=NotificationType.DUE_SOON,
                        message=f"Task '{task.title}' is due in less than 24 hours",
                        task_id=task.pk,
                        project_id=task.project_id,
                    )
                    due_soon_count += 1

        overdue_qs = Task.objects.filter(
            due_date__lt=now,
            deleted_at__isnull=True,
        ).exclude(status__in=["done", "cancelled"]).select_related("assigned_to", "created_by")

        overdue_count = 0
        for task in overdue_qs:
            recipients = {task.created_by}
            if task.assigned_to:
                recipients.add(task.assigned_to)
            for recipient in recipients:
                already = Notification.objects.filter(
                    recipient=recipient,
                    type=NotificationType.OVERDUE,
                    task_id=task.pk,
                    created_at__date=today,
                ).exists()
                if not already:
                    NotificationService.create(
                        recipient=recipient,
                        notification_type=NotificationType.OVERDUE,
                        message=f"Task '{task.title}' is overdue",
                        task_id=task.pk,
                        project_id=task.project_id,
                    )
                    overdue_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {due_soon_count} due_soon and {overdue_count} overdue notifications"
            )
        )
