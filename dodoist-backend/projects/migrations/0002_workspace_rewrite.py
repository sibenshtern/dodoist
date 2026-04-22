import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


def backfill_workspace_member_roles(apps, schema_editor):
    WorkspaceMember = apps.get_model("projects", "WorkspaceMember")
    Workspace = apps.get_model("projects", "Workspace")
    for ws in Workspace.objects.all():
        WorkspaceMember.objects.filter(workspace=ws, user_id=ws.owner_id).update(role="OWNER")
        WorkspaceMember.objects.filter(workspace=ws).exclude(user_id=ws.owner_id).update(role="MEMBER")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- WorkspaceMember: add role + invited_by ---
        migrations.AddField(
            model_name="workspacemember",
            name="role",
            field=models.CharField(
                choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MEMBER", "Member")],
                default="MEMBER",
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name="workspacemember",
            name="invited_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="workspace_invites_sent",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Backfill roles from workspace.owner
        migrations.RunPython(backfill_workspace_member_roles, reverse_code=noop),

        # --- Workspace: soft-delete fields ---
        migrations.AddField(
            model_name="workspace",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="workspace",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deleted_workspaces",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="delete_scheduled_for",
            field=models.DateTimeField(blank=True, null=True),
        ),

        # --- Workspace: Meta indexes ---
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(fields=["owner", "is_personal"], name="ws_owner_personal_idx"),
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(fields=["delete_scheduled_for"], name="ws_delete_scheduled_idx"),
        ),

        # --- WorkspaceInvitation (new model) ---
        migrations.CreateModel(
            name="WorkspaceInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("kind", models.CharField(choices=[("EMAIL", "Email"), ("LINK", "Link")], max_length=5)),
                ("email", models.CharField(blank=True, default="", max_length=254)),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("role_to_grant", models.CharField(
                    choices=[("OWNER", "Owner"), ("ADMIN", "Admin"), ("MEMBER", "Member")],
                    default="MEMBER",
                    max_length=6,
                )),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("max_uses", models.PositiveIntegerField(blank=True, null=True)),
                ("use_count", models.PositiveIntegerField(default=0)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="workspace_invitations_accepted",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("invited_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="workspace_invitations_sent",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("workspace", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="invitations",
                    to="projects.workspace",
                )),
            ],
            options={"db_table": "workspace_invitations"},
        ),
        migrations.AddIndex(
            model_name="workspaceinvitation",
            index=models.Index(
                fields=["workspace", "accepted_at", "revoked_at"],
                name="wsinv_ws_state_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workspaceinvitation",
            index=models.Index(fields=["email"], name="wsinv_email_idx"),
        ),
    ]
