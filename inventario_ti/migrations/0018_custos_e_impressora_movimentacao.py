from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('inventario_ti', '0017_impressoramonitorada_setor')]
    operations = [
        migrations.AddField(model_name='suprimentoti', name='valor_unitario', field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        migrations.AddField(model_name='movimentacaosuprimentoti', name='impressora_monitorada', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consumos_suprimentos', to='inventario_ti.impressoramonitorada')),
        migrations.AddField(model_name='movimentacaosuprimentoti', name='valor_unitario', field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        migrations.AddField(model_name='movimentacaosuprimentoti', name='valor_total', field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
    ]
