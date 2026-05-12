# Generated manually on 2026-05-07

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('djangosimplemissionapp', '0094_followup_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='followup',
            name='interaction_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
