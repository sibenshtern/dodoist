from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_add_email_verification_and_password_reset"),
    ]

    operations = [
        # Email verification token expiry
        migrations.AddField(
            model_name="user",
            name="verification_token_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Index on access token hash — every authenticated request does a lookup here
        migrations.AlterField(
            model_name="usersession",
            name="token_hash",
            field=models.CharField(db_index=True, max_length=255),
        ),
        # Stores the previously-used refresh hash for reuse-detection
        migrations.AddField(
            model_name="usersession",
            name="previous_refresh_token_hash",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
