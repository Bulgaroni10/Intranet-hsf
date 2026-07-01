# Generated manually for intranet chat groups
# Migration segura para SQLite, evitando erro de coluna duplicada.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def coluna_existe(cursor, tabela, coluna):
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = [linha[1] for linha in cursor.fetchall()]
    return coluna in colunas


def aplicar_colunas_com_seguranca(apps, schema_editor):
    cursor = schema_editor.connection.cursor()

    tabela = "conversas_conversachat"

    if not coluna_existe(cursor, tabela, "tipo"):
        cursor.execute(
            "ALTER TABLE conversas_conversachat "
            "ADD COLUMN tipo varchar(20) NOT NULL DEFAULT 'individual'"
        )

    if not coluna_existe(cursor, tabela, "nome_grupo"):
        cursor.execute(
            "ALTER TABLE conversas_conversachat "
            "ADD COLUMN nome_grupo varchar(120) NOT NULL DEFAULT ''"
        )

    if not coluna_existe(cursor, tabela, "criado_por_id"):
        cursor.execute(
            "ALTER TABLE conversas_conversachat "
            "ADD COLUMN criado_por_id bigint NULL"
        )

    cursor.execute(
        """
        UPDATE conversas_conversachat
        SET tipo = 'individual'
        WHERE tipo IS NULL OR tipo = ''
        """
    )

    cursor.execute(
        """
        UPDATE conversas_conversachat
        SET nome_grupo = ''
        WHERE nome_grupo IS NULL
        """
    )

    cursor.execute(
        """
        UPDATE conversas_conversachat
        SET criado_por_id = NULL
        WHERE criado_por_id IS NOT NULL
        AND criado_por_id NOT IN (
            SELECT id FROM usuarios_usuario
        )
        """
    )


def desfazer_colunas_com_seguranca(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("conversas", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    aplicar_colunas_com_seguranca,
                    desfazer_colunas_com_seguranca,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="conversachat",
                    name="tipo",
                    field=models.CharField(
                        choices=[
                            ("individual", "Individual"),
                            ("grupo", "Grupo"),
                        ],
                        default="individual",
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name="conversachat",
                    name="nome_grupo",
                    field=models.CharField(
                        blank=True,
                        max_length=120,
                    ),
                ),
                migrations.AddField(
                    model_name="conversachat",
                    name="criado_por",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="conversas_chat_criadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]