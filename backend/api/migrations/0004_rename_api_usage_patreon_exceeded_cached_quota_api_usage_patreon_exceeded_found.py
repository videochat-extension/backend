# Generated by Django 4.2.4 on 2023-08-20 20:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_rename_api_usage_patreon_exceeded_quota_api_usage_patreon_exceeded_cached_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='quota',
            old_name='api_usage_patreon_exceeded_cached',
            new_name='api_usage_patreon_exceeded_found',
        ),
    ]
