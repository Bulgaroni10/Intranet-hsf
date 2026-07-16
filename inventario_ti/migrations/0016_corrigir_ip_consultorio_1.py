from django.db import migrations


def corrigir_ip(apps, schema_editor):
    Impressora = apps.get_model('inventario_ti', 'ImpressoraMonitorada')
    antiga = Impressora.objects.filter(ip='192.168.0.201').first()
    nova = Impressora.objects.filter(ip='192.168.0.94').first()
    if antiga and not nova:
        antiga.ip = '192.168.0.94'
        antiga.local = 'CONSULTÓRIO 1'
        antiga.ativo = True
        antiga.online = False
        antiga.status_dispositivo = 'Aguardando coleta no IP corrigido'
        antiga.ultimo_erro = ''
        antiga.save()
    elif antiga and nova:
        antiga.ativo = False
        antiga.status_dispositivo = 'Desativada: IP corrigido para 192.168.0.94'
        antiga.save(update_fields=['ativo', 'status_dispositivo'])
        nova.local = 'CONSULTÓRIO 1'
        nova.ativo = True
        nova.save(update_fields=['local', 'ativo'])


class Migration(migrations.Migration):
    dependencies = [('inventario_ti', '0015_anexomovimentacaosuprimento')]
    operations = [migrations.RunPython(corrigir_ip, migrations.RunPython.noop)]
