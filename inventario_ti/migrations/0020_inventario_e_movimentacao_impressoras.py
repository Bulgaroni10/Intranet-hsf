from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('inventario_ti', '0019_leituraimpressora'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='impressoramonitorada', name='ip',
            field=models.GenericIPAddressField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='impressoramonitorada', name='patrimonio',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='impressoramonitorada', name='numero_serie',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='impressoramonitorada', name='situacao',
            field=models.CharField(choices=[('estoque', 'Em estoque'), ('em_uso', 'Em uso'), ('manutencao', 'Em manutenção'), ('baixada', 'Baixada')], default='em_uso', max_length=20),
        ),
        migrations.AlterField(
            model_name='impressoramonitorada', name='local',
            field=models.CharField(blank=True, default='', max_length=180),
        ),
        migrations.CreateModel(
            name='MovimentacaoImpressora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('situacao_anterior', models.CharField(choices=[('estoque', 'Em estoque'), ('em_uso', 'Em uso'), ('manutencao', 'Em manutenção'), ('baixada', 'Baixada')], max_length=20)),
                ('situacao_nova', models.CharField(choices=[('estoque', 'Em estoque'), ('em_uso', 'Em uso'), ('manutencao', 'Em manutenção'), ('baixada', 'Baixada')], max_length=20)),
                ('ip_anterior', models.GenericIPAddressField(blank=True, null=True)),
                ('ip_novo', models.GenericIPAddressField(blank=True, null=True)),
                ('local_anterior', models.CharField(blank=True, default='', max_length=180)),
                ('local_novo', models.CharField(blank=True, default='', max_length=180)),
                ('observacao', models.TextField(blank=True, default='')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('impressora', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimentacoes', to='inventario_ti.impressoramonitorada')),
                ('setor_anterior', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_impressora_origem', to='usuarios.setor')),
                ('setor_novo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_impressora_destino', to='usuarios.setor')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_impressoras', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Movimentação de impressora', 'verbose_name_plural': 'Movimentações de impressoras', 'ordering': ['-criado_em']},
        ),
    ]
