from django.db import migrations, models
from django.db.models import F


def copiar_data_original(apps, schema_editor):
    notificacao = apps.get_model('core', 'NotificacaoUsuario')
    notificacao.objects.update(atualizado_em=F('criado_em'))


class Migration(migrations.Migration):
    dependencies = [('core', '0003_notificacaousuario_unidade')]

    operations = [
        migrations.AddField(
            model_name='notificacaousuario',
            name='atualizado_em',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(copiar_data_original, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='notificacaousuario',
            name='atualizado_em',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterModelOptions(
            name='notificacaousuario',
            options={'ordering': ['-atualizado_em', '-criado_em']},
        ),
    ]
