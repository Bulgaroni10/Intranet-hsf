import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Setor, Unidade

from .models import ComputadorInventario, ErroAgenteInventario, ImpressoraMonitorada, MonitoramentoActiveDirectory, MonitoramentoRede, MonitoramentoServidor, MovimentacaoPatrimonioTI, PatrimonioTI
from .services_ad import monitorar_active_directory
from .services_impressoras import atualizar_impressora
from .views import (
    agent_error,
    dashboard,
    erros_agentes,
    exportar_erros_agentes_csv,
    exportar_inventario_csv,
    heartbeat,
    novo_patrimonio,
    patrimonios,
)


class ParqueComputadoresTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.unidade = Unidade.objects.create(nome="Hospital Parque", sigla="HP")
        self.outra = Unidade.objects.create(nome="Outra Unidade", sigla="OU2")
        grupo = Group.objects.create(name="TI")
        self.usuario = get_user_model().objects.create_user("parque.ti", unidade=self.unidade)
        self.usuario.groups.add(grupo)

    def test_dashboard_exibe_usuario_ip_status_e_apenas_unidade_permitida(self):
        ComputadorInventario.objects.create(
            hostname="PC-PARQUE", usuario="maria.silva", ip_local="192.0.2.20", unidade=self.unidade,
            ultimo_contato=timezone.now(),
        )
        ComputadorInventario.objects.create(hostname="PC-OUTRA", unidade=self.outra)
        request = self.factory.get("/portal/modulos/inventario-ti/")
        request.user = self.usuario
        resposta = dashboard(request)
        conteudo = resposta.content.decode()
        self.assertContains(resposta, "PC-PARQUE")
        self.assertIn("maria.silva", conteudo)
        self.assertIn("192.0.2.20", conteudo)
        self.assertIn("ONLINE", conteudo)
        self.assertNotIn("PC-OUTRA", conteudo)

    def test_filtro_destaca_agente_desatualizado(self):
        ComputadorInventario.objects.create(hostname="PC-ATUAL", unidade=self.unidade, agent_version="2.1.0")
        ComputadorInventario.objects.create(hostname="PC-ANTIGO", unidade=self.unidade, agent_version="2.0.0")
        request = self.factory.get("/portal/modulos/inventario-ti/", {"saude": "agente_desatualizado"})
        request.user = self.usuario
        resposta = dashboard(request)
        conteudo = resposta.content.decode()
        self.assertIn("PC-ANTIGO", conteudo)
        self.assertNotIn("PC-ATUAL", conteudo)

    def test_dashboard_exibe_motivo_da_pendencia_patrimonial(self):
        ComputadorInventario.objects.create(
            hostname="PC-SEM-SERIAL",
            unidade=self.unidade,
            serial="-",
        )
        ComputadorInventario.objects.create(
            hostname="PC-NAO-CADASTRADO",
            unidade=self.unidade,
            serial="SERIAL-INEXISTENTE",
        )

        request = self.factory.get("/portal/modulos/inventario-ti/")
        request.user = self.usuario
        resposta = dashboard(request)
        conteudo = resposta.content.decode()

        self.assertIn("Serial não informado pelo equipamento", conteudo)
        self.assertIn("Serial ainda não cadastrado no patrimônio", conteudo)


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


class MonitoramentoServidorTests(TestCase):
    def test_limites_normais_nao_geram_alerta(self):
        item = MonitoramentoServidor(cpu_percentual=50, memoria_percentual=70, disco_percentual=80)
        self.assertFalse(item.possui_alerta)

    def test_disco_acima_de_85_porcento_gera_alerta(self):
        item = MonitoramentoServidor(cpu_percentual=20, memoria_percentual=30, disco_percentual=85)
        self.assertTrue(item.possui_alerta)


class MonitoramentoRedeTests(TestCase):
    def test_todos_componentes_online_nao_geram_alerta(self):
        item = MonitoramentoRede(gateway_ok=True, dns_ok=True, switch_ok=True)
        self.assertFalse(item.possui_alerta)

    def test_queda_do_gateway_gera_alerta(self):
        item = MonitoramentoRede(gateway_ok=False, dns_ok=True, switch_ok=True)
        self.assertTrue(item.possui_alerta)


class QrCodePatrimonioTests(TestCase):
    def setUp(self):
        self.unidade = Unidade.objects.create(nome="Hospital QR", sigla="QR")
        grupo = Group.objects.create(name="TI")
        self.usuario = get_user_model().objects.create_user("qr.ti", password="teste", unidade=self.unidade)
        self.usuario.groups.add(grupo)
        self.patrimonio = PatrimonioTI.objects.create(codigo="PAT-QR-001", unidade=self.unidade)
        self.client.force_login(self.usuario)

    def test_qr_code_svg_aponta_para_detalhe_protegido(self):
        resposta = self.client.get(reverse("inventario_ti_patrimonio_qr", args=[self.patrimonio.id]))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", resposta.content)

    def test_etiqueta_renderiza_codigo_do_patrimonio(self):
        resposta = self.client.get(reverse("inventario_ti_patrimonio_etiqueta", args=[self.patrimonio.id]))
        self.assertContains(resposta, "PAT-QR-001")


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

    def test_heartbeat_vincula_patrimonio_unico_pelo_serial(self):
        patrimonio = PatrimonioTI.objects.create(
            codigo="PAT-001",
            tipo="computador",
            unidade=self.unidade,
            serial="SERIAL1",
        )

        response = self.postar_heartbeat(self.payload)
        computador = ComputadorInventario.objects.get(hostname="PC-TESTE")
        patrimonio.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(patrimonio.computador, computador)
        self.assertEqual(computador.patrimonio, "PAT-001")
        self.assertTrue(
            patrimonio.movimentacoes.filter(tipo="ajuste", observacao__icontains="automatico").exists()
        )

    def test_heartbeat_nao_vincula_quando_serial_e_duplicado(self):
        PatrimonioTI.objects.create(codigo="PAT-001", unidade=self.unidade, serial="SERIAL1")
        PatrimonioTI.objects.create(codigo="PAT-002", unidade=self.unidade, serial="serial1")

        self.postar_heartbeat(self.payload)

        computador = ComputadorInventario.objects.get(hostname="PC-TESTE")
        self.assertFalse(PatrimonioTI.objects.filter(computador=computador).exists())
        self.assertEqual(computador.patrimonio, "-")

    def test_heartbeat_nao_vincula_serial_de_outra_unidade(self):
        outra = Unidade.objects.create(nome="Outra Unidade", sigla="OU")
        PatrimonioTI.objects.create(codigo="PAT-OUTRA", unidade=outra, serial="SERIAL1")

        self.postar_heartbeat(self.payload)

        computador = ComputadorInventario.objects.get(hostname="PC-TESTE")
        self.assertFalse(PatrimonioTI.objects.filter(computador=computador).exists())


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
        self.client.force_login(self.user)

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

    def test_importacao_csv_cadastra_patrimonio_e_movimentacao(self):
        Setor.objects.create(nome="TI")
        conteudo = (
            "codigo;tipo;status;unidade;setor;responsavel;fabricante;modelo;serial;observacao\n"
            "PAT-CSV-1;computador;em_uso;HT;TI;Suporte;Dell;OptiPlex;SERIAL-CSV-1;Importado\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("patrimonios.csv", conteudo, content_type="text/csv")

        resposta = self.client.post(
            reverse("inventario_ti_patrimonios_importar"),
            {"arquivo": arquivo},
        )

        patrimonio = PatrimonioTI.objects.get(codigo="PAT-CSV-1")
        self.assertRedirects(resposta, reverse("inventario_ti_patrimonios"))
        self.assertEqual(patrimonio.serial, "SERIAL-CSV-1")
        self.assertEqual(patrimonio.setor.nome, "TI")
        self.assertTrue(patrimonio.movimentacoes.filter(tipo="cadastro").exists())

    def test_importacao_csv_vincula_computador_existente_imediatamente(self):
        computador = ComputadorInventario.objects.create(
            hostname="PC-JA-DESCOBERTO",
            unidade=self.unidade,
            serial="SERIAL-JA-DESCOBERTO",
        )
        conteudo = (
            "codigo;tipo;status;unidade;setor;serial\n"
            "PAT-AUTO;computador;em_uso;HT;;SERIAL-JA-DESCOBERTO\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("patrimonios.csv", conteudo, content_type="text/csv")

        resposta = self.client.post(
            reverse("inventario_ti_patrimonios_importar"),
            {"arquivo": arquivo},
            follow=True,
        )

        computador.refresh_from_db()
        patrimonio = PatrimonioTI.objects.get(codigo="PAT-AUTO")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(patrimonio.computador, computador)
        self.assertEqual(computador.patrimonio, "PAT-AUTO")

    def test_importacao_csv_com_erro_nao_grava_parcialmente(self):
        conteudo = (
            "codigo;tipo;status;unidade;setor;serial\n"
            "PAT-VALIDO;computador;em_uso;HT;;SERIAL-1\n"
            "PAT-INVALIDO;tipo-inexistente;em_uso;HT;;SERIAL-2\n"
        ).encode("utf-8")
        arquivo = SimpleUploadedFile("patrimonios.csv", conteudo, content_type="text/csv")

        resposta = self.client.post(
            reverse("inventario_ti_patrimonios_importar"),
            {"arquivo": arquivo},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(PatrimonioTI.objects.filter(codigo__in=["PAT-VALIDO", "PAT-INVALIDO"]).exists())
