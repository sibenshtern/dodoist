import django.db.models.deletion

from django.db import migrations, models


def backfill_active_workspace(apps, schema_editor):
    User = apps.get_model("users", "User")
    Workspace = apps.get_model("projects", "Workspace")
    for user in User.objects.all():
        personal = Workspace.objects.filter(owner=user, is_personal=True).first()
        if personal:
            user.active_workspace = personal
            user.save(update_fields=["active_workspace"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_add_email_verification_and_password_reset"),
        ("projects", "0002_workspace_rewrite"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="active_workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="projects.workspace",
            ),
        ),
        migrations.RunPython(backfill_active_workspace, reverse_code=noop),
    ]
