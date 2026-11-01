import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('conversations', '0003_conversation_title_defaults'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='is_pinned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(
                fields=['user', 'is_pinned', 'updated_at'],
                name='conversatio_user_id_6f0b0d_idx',
            ),
        ),
        migrations.CreateModel(
            name='MessageFeedback',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'rating',
                    models.SmallIntegerField(
                        choices=[(1, 'Up'), (-1, 'Down')],
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'message',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='feedback_entries',
                        to='conversations.message',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='message_feedback',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'updated_at'], name='conversatio_user_id_8a1fbf_idx'),
                    models.Index(fields=['message'], name='conversatio_message_0d0f8a_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('message', 'user'),
                        name='conversations_messagefeedback_message_user_uniq',
                    ),
                ],
            },
        ),
    ]
