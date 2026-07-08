import json

from django.test import RequestFactory, TestCase

from .models import ComputadorInventario
from .views import heartbeat


class HeartbeatHistoricoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.payload = {
            "hostname": "PC-TESTE",
            "usuario": "usuario1",
            "ip_local": "10.0.0.10",
            "mac": "AA-BB-CC",
            "sistema": "Windows 11",
            "cpu": "Intel Core",
            "ram": "8 GB",
            "disco_total": "256 GB",
            "disco_livre": "120 GB",
            "disco_percentual": "53%",
            "fabricante": "Dell",
            "modelo": "OptiPlex",
            "serial": "SERIAL1",
            "agent_version": "2.0.0",
        }

    def postar_heartbeat(self, payload):
        request = self.factory.post(
            "/api/inventario/heartbeat/",
            data=json.dumps(payload),
            content_type="application/json",
            REMOTE_ADDR="127.0.0.1",
        )

        return heartbeat(request)

    def test_primeiro_heartbeat_cria_historico_de_cadastro(self):
        response = self.postar_heartbeat(self.payload)

        computador = ComputadorInventario.objects.get(hostname="PC-TESTE")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(computador.historicos.count(), 1)
        self.assertEqual(computador.historicos.first().tipo, "cadastro")

    def test_heartbeat_com_alteracao_registra_historico(self):
        self.postar_heartbeat(self.payload)

        payload_alterado = {
            **self.payload,
            "usuario": "usuario2",
            "disco_percentual": "91%",
        }

        response = self.postar_heartbeat(payload_alterado)
        computador = ComputadorInventario.objects.get(hostname="PC-TESTE")
        campos_alterados = set(
            computador.historicos.filter(tipo="alteracao").values_list("campo", flat=True)
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("usuario", campos_alterados)
        self.assertIn("disco_percentual", campos_alterados)
