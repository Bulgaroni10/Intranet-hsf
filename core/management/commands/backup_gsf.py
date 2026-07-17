import hashlib
import json
import re
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


PASTA_RE = re.compile(r"^\d{8}-\d{6}$")


def sha256_arquivo(caminho):
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


class Command(BaseCommand):
    help = "Cria backup consistente do SQLite e dos anexos da GSF Hub."

    def add_arguments(self, parser):
        parser.add_argument("--destino", default=r"C:\Backups\GSF-Hub")
        parser.add_argument("--retencao-dias", type=int, default=14)
        parser.add_argument("--sem-media", action="store_true")

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("Este comando usa a API de backup do SQLite. Para PostgreSQL, use pg_dump.")
        if options["retencao_dias"] < 1:
            raise CommandError("A retenção deve ser de pelo menos 1 dia.")

        raiz = Path(options["destino"]).resolve()
        raiz.mkdir(parents=True, exist_ok=True)
        agora = timezone.localtime()
        pasta = raiz / agora.strftime("%Y%m%d-%H%M%S")
        pasta.mkdir()

        banco_destino = pasta / "db.sqlite3"
        connection.ensure_connection()
        destino = sqlite3.connect(str(banco_destino))
        try:
            connection.connection.backup(destino)
        finally:
            destino.close()

        arquivos = {"db.sqlite3": {"tamanho": banco_destino.stat().st_size, "sha256": sha256_arquivo(banco_destino)}}
        media = Path(settings.MEDIA_ROOT)
        if not options["sem_media"] and media.exists():
            base_zip = pasta / "media"
            zip_criado = Path(shutil.make_archive(str(base_zip), "zip", root_dir=media))
            arquivos[zip_criado.name] = {"tamanho": zip_criado.stat().st_size, "sha256": sha256_arquivo(zip_criado)}

        manifesto = {
            "criado_em": agora.isoformat(),
            "banco": connection.vendor,
            "arquivos": arquivos,
        }
        (pasta / "manifesto.json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        limite = agora - timedelta(days=options["retencao_dias"])
        removidas = 0
        for candidata in raiz.iterdir():
            if not candidata.is_dir() or not PASTA_RE.match(candidata.name) or candidata == pasta:
                continue
            criada = timezone.make_aware(
                datetime.strptime(candidata.name, "%Y%m%d-%H%M%S"),
                timezone.get_current_timezone(),
            )
            if criada < limite:
                shutil.rmtree(candidata)
                removidas += 1

        self.stdout.write(self.style.SUCCESS(f"Backup concluído: {pasta}"))
        self.stdout.write(f"Pastas antigas removidas: {removidas}")
