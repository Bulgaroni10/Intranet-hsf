from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('gestao_acessos', '0003_dados_profissionais')]
    operations = [
        migrations.AddField(
            model_name='solicitacaoacesso', name='cargo',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='tipo_conselho',
            field=models.CharField(blank=True, choices=[('CRM', 'CRM'), ('COREN', 'COREN'), ('CREFITO', 'CREFITO'), ('CRP', 'CRP'), ('CRN', 'CRN'), ('CREFONO', 'CREFONO'), ('OUTRO', 'Outro')], max_length=20),
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='numero_conselho',
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='uf_conselho',
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AlterField(
            model_name='solicitacaoacesso', name='especialidade',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
