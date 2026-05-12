# Generated manually on 2026-05-07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangosimplemissionapp', '0093_followup_interaction_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='followup',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('completed', 'Completed'),
                    ('missed', 'Missed'),
                    ('rescheduled', 'Rescheduled')
                ],
                default='pending',
                max_length=20
            ),
        ),
    ]
