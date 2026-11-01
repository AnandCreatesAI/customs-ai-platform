from django.db import migrations, models


def backfill_placeholder_titles(apps, schema_editor):
    Conversation = apps.get_model('conversations', 'Conversation')
    Message = apps.get_model('conversations', 'Message')
    from apps.conversations.titles import (
        is_placeholder_conversation_title,
        title_from_user_message,
    )

    for conversation in Conversation.objects.all().iterator():
        if not is_placeholder_conversation_title(conversation.title):
            continue
        first_user = (
            Message.objects.filter(conversation_id=conversation.pk, role='user')
            .order_by('created_at', 'id')
            .first()
        )
        if not first_user:
            continue
        generated = title_from_user_message(first_user.content)
        if not generated or is_placeholder_conversation_title(generated):
            continue
        Conversation.objects.filter(pk=conversation.pk).update(title=generated)


class Migration(migrations.Migration):
    dependencies = [
        ('conversations', '0002_alter_message_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='title',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.RunPython(backfill_placeholder_titles, migrations.RunPython.noop),
    ]
