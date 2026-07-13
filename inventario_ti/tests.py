import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from usuarios.models import Unidade

from .models import ComputadorInventario, ErroAgenteInventario, ImpressoraMonitorada, MonitoramentoActiveDirectory, MovimentacaoPatrimonioTI, PatrimonioTI
from .services_ad import monitorar_active_directory
from .services_impressoras import atualizar_impressora
from .views import (
    agent_error,
    erros_agentes,
    exportar_erros_agentes_csv,
    exportar_inventario_csv,
    heartbeat,
    novo_patrimonio,
    patrimonios,
)


class _RespostaImpressoraFake:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limite):
        return (
            b'<html><head><title>Brother MFC-L6902DW</title></head>'
            b'<div id="moni_data"><span class="moniWarning">Substituir Cilindro</span></div>'
            b'<img class="tonerremain" height="30" /></html>'
        )


class MonitoramentoImpressoraTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome="Hospital", sigla="IMP")
        grupo = Group.objects.create(name="TI")
        self.usuario = get_user_model().objects.create_user("tecnico.ti", unidade=self.unidade)
        self.usuario.groups.add(grupo)
        self.impressora = ImpressoraMonitorada.objects.create(
            unidade=self.unidade, ip="192.0.2.10", modelo_informado="Modelo incorreto", local="Recepcao"
        )

    @patch("inventario_ti.services_impressoras.urlopen", return_value=_RespostaImpressoraFake())
    def test_coleta_corrige_modelo_e_cria_alerta_individual(self, _urlopen):
        atualizar_impressora(self.impressora)
        self.impressora.refresh_from_db()
        self.assertTrue(self.impressora.online)
        self.assertEqual(self.impressora.modelo_detectado, "MFC-L6902DW")
        self.assertEqual(self.impressora.toner_percentual, 50)
        self.assertTrue(self.impressora.possui_alerta)
        self.assertTrue(self.usuario.notificacoes.filter(origem="impressora_monitorada", lida=False).exists())

    @patch("inventario_ti.services_impressoras.consultar_snmp", return_value="")
    @patch("inventario_ti.services_impressoras.urlopen", side_effect=TimeoutError("timeout"))
    def test_falha_de_coleta_marca_impressora_offline(self, _urlopen, _snmp):
        atualizar_impressora(self.impressora)
        self.impressora.refresh_from_db()
        self.assertFalse(self.impressora.online)
        self.assertEqual(self.impressora.status_dispositivo, "Sem comunicação")

    @patch("inventario_ti.services_impressoras.consultar_snmp", return_value="Brother NC-8900h")
    @patch("inventario_ti.services_impressoras.urlopen", side_effect=TimeoutError("timeout"))
    def test_snmp_e_usado_quando_painel_web_nao_responde(self, _urlopen, _snmp):
        atualizar_impressora(self.impressora)
        self.impressora.refresh_from_db()
        self.assertTrue(self.impressora.online)
        self.assertEqual(self.impressora.status_dispositivo, "Online via SNMP")

    @patch("inventario_ti.services_impressoras.consultar_snmp", return_value="HPE OfficeConnect Switch")
    @patch("inventario_ti.services_impressoras.urlopen", side_effect=TimeoutError("timeout"))
    def test_dispositivo_nao_brother_gera_alerta_de_cadastro(self, _urlopen, _snmp):
        atualizar_impressora(self.impressora)
        self.impressora.refresh_from_db()
        self.assertFalse(self.impressora.online)
        self.assertIn("não pertence", self.impressora.status_dispositivo)


class MonitoramentoActiveDirectoryTests(TestCase):
    def setUp(self):
        grupo = Group.objects.create(name="TI")
        self.usuario = get_user_model().objects.create_user("analista.ti")
        self.usuario.groups.add(grupo)

    @patch("inventario_ti.services_ad.socket.gethostbyname", return_value="192.0.2.30")
    @patch("inventario_ti.services_ad._porta_aberta", return_value=4)
    def test_servicos_disponiveis_nao_geram_alerta(self, _porta, _dns):
        item = monitorar_active_directory("dc.example.test")
        self.assertTrue(item.online)
        self.assertTrue(item.ldap_ok)
        self.assertEqual(item.latencia_ms, 4)
        self.assertFalse(self.usuario.notificacoes.filter(origem="active_directory", lida=False).exists())

    @patch("inventario_ti.services_ad.socket.gethostbyname", return_value="192.0.2.30")
    @patch("inventario_ti.services_ad._porta_aberta", side_effect=OSError("indisponível"))
    def test_falha_dos_servicos_gera_alerta_para_ti(self, _porta, _dns):
        item = monitorar_active_directory("dc.example.test")
        self.assertFalse(item.online)
        self.assertTrue(item.possui_alerta)
        self.assertTrue(self.usuario.notificacoes.filter(origem="active_directory", lida=False).exists())


class HeartbeatHistoricoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Teste", sigla="HT")
        self.payload = {
            "hostname": "PC-TESTE",
            "unit_code": "HT",
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


class AgentErrorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Teste", sigla="HT")

    def postar_erro(self, payload):
        request = self.factory.post(
            "/api/inventario/agent-error/",
            data=json.dumps(payload),
            content_type="application/json",
            REMOTE_ADDR="127.0.0.1",
        )

        return agent_error(request)

    def test_agent_error_cria_registro_sem_computador(self):
        response = self.postar_erro({
            "hostname": "PC-SEM-CADASTRO",
            "unit_code": "HT",
            "agent_version": "2.1.0",
            "categoria": "coleta",
            "mensagem": "Falha ao coletar dados.",
            "detalhe": "stacktrace",
        })

        erro = ErroAgenteInventario.objects.get(hostname="PC-SEM-CADASTRO")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(erro.computador)
        self.assertEqual(erro.categoria, "coleta")

    def test_agent_error_vincula_computador_e_cria_historico(self):
        computador = ComputadorInventario.objects.create(hostname="PC-TESTE", unidade=self.unidade)

        response = self.postar_erro({
            "hostname": "PC-TESTE",
            "unit_code": "HT",
            "agent_version": "2.1.0",
            "categoria": "coleta",
            "mensagem": "Falha ao coletar dados.",
        })

        erro = ErroAgenteInventario.objects.get(hostname="PC-TESTE")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(erro.computador, computador)
        self.assertEqual(computador.historicos.filter(campo="agent_error").count(), 1)


class PainelErrosAgentesTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Teste", sigla="HT")
        grupo = Group.objects.create(name="TI Suporte")
        self.user = get_user_model().objects.create_user(
            username="tecnico",
            password="teste",
            unidade=self.unidade,
        )
        self.user.groups.add(grupo)

    def test_painel_erros_agentes_renderiza_para_ti(self):
        ErroAgenteInventario.objects.create(
            unidade=self.unidade,
            hostname="PC-TESTE",
            agent_version="2.1.0",
            categoria="coleta",
            mensagem="Falha ao coletar dados.",
        )

        request = self.factory.get("/portal/modulos/inventario-ti/erros-agentes/")
        request.user = self.user

        response = erros_agentes(request)

        self.assertEqual(response.status_code, 200)

    def test_painel_erros_agentes_filtra_por_categoria(self):
        ErroAgenteInventario.objects.create(
            unidade=self.unidade,
            hostname="PC-TESTE",
            agent_version="2.1.0",
            categoria="coleta",
            mensagem="Falha ao coletar dados.",
        )
        ErroAgenteInventario.objects.create(
            unidade=self.unidade,
            hostname="PC-TESTE-2",
            agent_version="2.1.0",
            categoria="rede",
            mensagem="Falha de rede.",
        )

        request = self.factory.get(
            "/portal/modulos/inventario-ti/erros-agentes/",
            {"categoria": "coleta"},
        )
        request.user = self.user

        response = erros_agentes(request)
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("PC-TESTE", html)
        self.assertNotIn("PC-TESTE-2", html)


class ExportacaoCsvTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Teste", sigla="HT")
        grupo = Group.objects.create(name="TI Suporte")
        self.user = get_user_model().objects.create_user(
            username="exportador",
            password="teste",
            unidade=self.unidade,
        )
        self.user.groups.add(grupo)

    def test_exportar_inventario_csv_respeita_filtro_busca(self):
        ComputadorInventario.objects.create(hostname="PC-CSV-1", usuario="usuario1", unidade=self.unidade)
        ComputadorInventario.objects.create(hostname="PC-CSV-2", usuario="usuario2", unidade=self.unidade)

        request = self.factory.get(
            "/portal/modulos/inventario-ti/exportar-csv/",
            {"busca": "PC-CSV-1"},
        )
        request.user = self.user

        response = exportar_inventario_csv(request)
        conteudo = response.content.decode("utf-8-sig")

        self.assertEqual(response.status_code, 200)
        self.assertIn("PC-CSV-1", conteudo)
        self.assertNotIn("PC-CSV-2", conteudo)

    def test_exportar_inventario_csv_nao_mistura_unidades(self):
        outra_unidade = Unidade.objects.create(nome="Outra Unidade", sigla="OU")
        ComputadorInventario.objects.create(hostname="PC-HT", usuario="usuario1", unidade=self.unidade)
        ComputadorInventario.objects.create(hostname="PC-OU", usuario="usuario2", unidade=outra_unidade)

        request = self.factory.get("/portal/modulos/inventario-ti/exportar-csv/")
        request.user = self.user

        response = exportar_inventario_csv(request)
        conteudo = response.content.decode("utf-8-sig")

        self.assertIn("PC-HT", conteudo)
        self.assertNotIn("PC-OU", conteudo)

    def test_exportar_erros_agentes_csv_respeita_filtro_categoria(self):
        ErroAgenteInventario.objects.create(
            unidade=self.unidade,
            hostname="PC-ERRO-1",
            agent_version="2.1.0",
            categoria="coleta",
            mensagem="Falha ao coletar dados.",
        )
        ErroAgenteInventario.objects.create(
            unidade=self.unidade,
            hostname="PC-ERRO-2",
            agent_version="2.1.0",
            categoria="rede",
            mensagem="Falha de rede.",
        )

        request = self.factory.get(
            "/portal/modulos/inventario-ti/erros-agentes/exportar-csv/",
            {"categoria": "coleta"},
        )
        request.user = self.user

        response = exportar_erros_agentes_csv(request)
        conteudo = response.content.decode("utf-8-sig")

        self.assertEqual(response.status_code, 200)
        self.assertIn("PC-ERRO-1", conteudo)
        self.assertNotIn("PC-ERRO-2", conteudo)


class PatrimonioTITests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Teste", sigla="HT")
        grupo = Group.objects.create(name="TI Suporte")
        self.user = get_user_model().objects.create_user(
            username="patrimonio",
            password="teste",
            unidade=self.unidade,
        )
        self.user.groups.add(grupo)

    def test_lista_patrimonios_renderiza_para_ti(self):
        PatrimonioTI.objects.create(codigo="PAT-001", tipo="computador", unidade=self.unidade)

        request = self.factory.get("/portal/modulos/inventario-ti/patrimonios/")
        request.user = self.user

        response = patrimonios(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("PAT-001", response.content.decode())

    def test_novo_patrimonio_vincula_computador_e_registra_movimentacao(self):
        computador = ComputadorInventario.objects.create(hostname="PC-PAT", unidade=self.unidade)

        request = self.factory.post(
            "/portal/modulos/inventario-ti/patrimonios/novo/",
            {
                "codigo": "PAT-002",
                "tipo": "computador",
                "status": "em_uso",
                "computador": str(computador.id),
                "responsavel": "TI",
                "ativo": "on",
            },
        )
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)

        response = novo_patrimonio(request)
        computador.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(computador.patrimonio, "PAT-002")
        self.assertTrue(PatrimonioTI.objects.filter(codigo="PAT-002", computador=computador).exists())
        self.assertEqual(MovimentacaoPatrimonioTI.objects.filter(patrimonio__codigo="PAT-002").count(), 1)
