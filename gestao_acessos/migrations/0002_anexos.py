import django.db.models.deletion
import gestao_acessos.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('gestao_acessos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AnexoSolicitacaoAcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to=gestao_acessos.models.caminho_anexo_acesso)),
                ('nome_original', models.CharField(max_length=255)),
                ('tipo_mime', models.CharField(default='application/octet-stream', max_length=150)),
                ('tamanho', models.PositiveBigIntegerField(default=0)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('enviado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('solicitacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='anexos', to='gestao_acessos.solicitacaoacesso')),
            ],
            options={'ordering': ['criado_em']},
        ),
    ]
