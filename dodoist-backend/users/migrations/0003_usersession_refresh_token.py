import secrets
import django.utils.timezone
from django.db import migrations, models


def clear_old_sessions(apps, schema_editor):
    """
    All existing sessions used the old 30-day single-token scheme and are now
    invalid under the new access+refresh token architecture. Clear them so the
    UNIQUE constraint on refresh_token_hash can be applied cleanly.
    """
    UserSession = apps.get_model('users', 'UserSession')
    UserSession.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_reaction_timelog_notification'),
    ]

    operations = [
        migrations.RunPython(clear_old_sessions, migrations.RunPython.noop),
        migrations.AddField(
            model_name='usersession',
            name='refresh_token_hash',
            field=models.CharField(default='', max_length=255, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='usersession',
            name='refresh_expires_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
