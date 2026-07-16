from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gestao_acessos', '0002_anexos')]
    operations = [
        migrations.RenameField(
            model_name='solicitacaoacesso', old_name='colaborador_matricula', new_name='numero_conselho',
        ),
        migrations.RenameField(
            model_name='solicitacaoacesso', old_name='colaborador_cargo', new_name='especialidade',
        ),
        migrations.AddField(
            model_name='solicitacaoacesso', name='cpf', field=models.CharField(default='', max_length=14), preserve_default=False,
        ),
        migrations.AddField(
            model_name='solicitacaoacesso', name='tipo_conselho',
            field=models.CharField(choices=[('CRM', 'CRM'), ('COREN', 'COREN'), ('CREFITO', 'CREFITO'), ('CRP', 'CRP'), ('CRN', 'CRN'), ('CREFONO', 'CREFONO'), ('OUTRO', 'Outro')], default='OUTRO', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='solicitacaoacesso', name='uf_conselho', field=models.CharField(default='', max_length=2), preserve_default=False,
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='numero_conselho', field=models.CharField(max_length=60),
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='especialidade', field=models.CharField(max_length=150),
        ),
    ]
