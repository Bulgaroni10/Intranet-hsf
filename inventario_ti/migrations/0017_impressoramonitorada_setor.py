from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('inventario_ti', '0016_corrigir_ip_consultorio_1')]
    operations = [
        migrations.AddField(
            model_name='impressoramonitorada', name='setor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='impressoras_monitoradas', to='usuarios.setor',
            ),
        ),
    ]
