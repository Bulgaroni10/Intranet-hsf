import django.db.models.deletion
from django.db import migrations, models


ORIGENS_POR_UNIDADE = {
    'impressora_monitorada',
    'suprimento_estoque_baixo',
    'active_directory',
    'capacidade_servidor',
    'monitoramento_rede',
    'sincronizacao_mv',
}


def preencher_unidade_notificacoes_operacionais(apps, schema_editor):
    Notificacao = apps.get_model('core', 'NotificacaoUsuario')
    Unidade = apps.get_model('usuarios', 'Unidade')
    hsfos = Unidade.objects.filter(sigla__iexact='HSFOS').first()
    if hsfos:
        Notificacao.objects.filter(
            origem__in=ORIGENS_POR_UNIDADE - {'sincronizacao_mv'},
        ).update(unidade_id=hsfos.pk)
    for notificacao in Notificacao.objects.filter(origem='sincronizacao_mv'):
        if notificacao.objeto_id.isdigit() and Unidade.objects.filter(pk=int(notificacao.objeto_id)).exists():
            notificacao.unidade_id = int(notificacao.objeto_id)
            notificacao.save(update_fields=['unidade'])


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_favoritomodulo'),
        ('usuarios', '0004_preencher_codigos_mv_conhecidos'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacaousuario',
            name='unidade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notificacoes_usuarios', to='usuarios.unidade'),
        ),
        migrations.RunPython(preencher_unidade_notificacoes_operacionais, migrations.RunPython.noop),
    ]
