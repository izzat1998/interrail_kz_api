# Generated migration for adding TimeStampModel fields
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="user_type",
            field=models.CharField(
                choices=[
                    ("customer", "Customer"),
                    ("manager", "Manager"),
                    ("admin", "Admin"),
                ],
                default="customer",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="customuser",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        # Add database indexes
        migrations.RunSQL(
            sql=[
                'CREATE INDEX IF NOT EXISTS "accounts_customuser_date_joined_desc" ON "accounts_customuser" ("date_joined" DESC);',
                'CREATE INDEX IF NOT EXISTS "accounts_customuser_user_type" ON "accounts_customuser" ("user_type");',
                'CREATE INDEX IF NOT EXISTS "accounts_customuser_is_active" ON "accounts_customuser" ("is_active");',
                'CREATE INDEX IF NOT EXISTS "accounts_customuser_email" ON "accounts_customuser" ("email");',
                'CREATE INDEX IF NOT EXISTS "accounts_customuser_username" ON "accounts_customuser" ("username");',
            ],
            reverse_sql=[
                'DROP INDEX IF EXISTS "accounts_customuser_date_joined_desc";',
                'DROP INDEX IF EXISTS "accounts_customuser_user_type";',
                'DROP INDEX IF EXISTS "accounts_customuser_is_active";',
                'DROP INDEX IF EXISTS "accounts_customuser_email";',
                'DROP INDEX IF EXISTS "accounts_customuser_username";',
            ],
        ),
    ]
