from django.db import migrations


def preencher_codigos_mv_conhecidos(apps, schema_editor):
    Unidade = apps.get_model('usuarios', 'Unidade')
    # Mapeamento usado pela intranet antiga (intranet-frontend/src/mock/mockUnidades.ts).
    codigos = {
        'HSFVF': 1,
        'HSFCT': 2,
        'HSFMA': 3,
        'HSFOS': 4,
        'HSFSR': 5,
    }
    for sigla, codigo in codigos.items():
        Unidade.objects.filter(sigla__iexact=sigla).update(codigo_mv=codigo)


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0003_unidade_codigo_mv')]

    operations = [
        migrations.RunPython(preencher_codigos_mv_conhecidos, migrations.RunPython.noop),
    ]
