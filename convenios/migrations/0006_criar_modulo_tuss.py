from django.db import migrations


def criar_modulo_tuss(apps, schema_editor):
    Modulo = apps.get_model('modulos', 'Modulo')
    Group = apps.get_model('auth', 'Group')
    modulo, _ = Modulo.objects.update_or_create(
        nome='Código TUSS',
        defaults={
            'descricao': 'Consulta de procedimentos e códigos TUSS/MV',
            'categoria': 'assistencial', 'icone': '🔎', 'tag': 'TUSS',
            'link': '/portal/modulos/tuss/', 'palavras_chave': 'tuss procedimento exame codigo mv',
            'ativo': True, 'ordem': 15,
        },
    )
    for nome in ('TI Administrador', 'Recepção', 'Agendamento', 'Cadastro', 'Faturamento'):
        grupo, _ = Group.objects.get_or_create(name=nome)
        modulo.grupos_permitidos.add(grupo)


class Migration(migrations.Migration):
    dependencies = [('convenios', '0005_procedimentotuss'), ('modulos', '0001_initial')]
    operations = [migrations.RunPython(criar_modulo_tuss, migrations.RunPython.noop)]
