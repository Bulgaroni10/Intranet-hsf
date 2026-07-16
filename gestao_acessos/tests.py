from django.contrib.auth.models import Group
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from usuarios.models import Setor, Unidade, Usuario
from .models import AnexoSolicitacaoAcesso, HistoricoSolicitacaoAcesso, SolicitacaoAcesso


class GestaoAcessosTests(TestCase):
    def setUp(self):
        self.unidade_a = Unidade.objects.create(nome='Hospital A', sigla='HA')
        self.unidade_b = Unidade.objects.create(nome='Hospital B', sigla='HB')
        self.setor = Setor.objects.create(nome='Recepção')
        self.usuario_a = Usuario.objects.create_user(
            'usuario.teste', password='senha', unidade=self.unidade_a, setor=self.setor,
        )
        self.usuario_b = Usuario.objects.create_user(
            'outro.usuario', password='senha', unidade=self.unidade_b, setor=self.setor,
        )
        grupo_ti = Group.objects.create(name='TI Suporte')
        self.ti_a = Usuario.objects.create_user(
            'tecnico.suporte', password='senha', unidade=self.unidade_a, setor=self.setor,
        )
        self.ti_a.groups.add(grupo_ti)

    def criar(self, unidade, solicitante):
        return SolicitacaoAcesso.objects.create(
            unidade=unidade, setor=self.setor, solicitante=solicitante,
            tipo='admissao', colaborador_nome='Colaborador Teste',
            sistemas='MV', justificativa='Admissão',
        )

    def test_usuario_cria_solicitacao_na_unidade_ativa(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(reverse('gestao_acessos_nova'), {
            'tipo': 'admissao', 'prioridade': 'normal',
            'colaborador_nome': 'Maria Silva', 'setor': self.setor.pk,
            'sistemas': 'MV\nE-mail', 'justificativa': 'Nova colaboradora',
        })
        self.assertEqual(resposta.status_code, 302)
        solicitacao = SolicitacaoAcesso.objects.get()
        self.assertEqual(solicitacao.unidade, self.unidade_a)
        self.assertEqual(solicitacao.solicitante, self.usuario_a)
        self.assertTrue(HistoricoSolicitacaoAcesso.objects.filter(solicitacao=solicitacao).exists())

    def test_usuario_nao_visualiza_solicitacao_de_outra_unidade(self):
        solicitacao = self.criar(self.unidade_b, self.usuario_b)
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse('gestao_acessos_detalhe', args=[solicitacao.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_ti_visualiza_e_atende_somente_unidade_ativa(self):
        propria = self.criar(self.unidade_a, self.usuario_a)
        outra = self.criar(self.unidade_b, self.usuario_b)
        self.client.force_login(self.ti_a)
        resposta = self.client.get(reverse('gestao_acessos_lista'))
        self.assertContains(resposta, f'#{propria.pk}')
        self.assertNotContains(resposta, f'#{outra.pk}')
        resposta = self.client.post(reverse('gestao_acessos_atender', args=[propria.pk]), {
            'status': 'em_execucao', 'observacao_ti': 'Em atendimento',
        })
        self.assertEqual(resposta.status_code, 302)
        propria.refresh_from_db()
        self.assertEqual(propria.status, 'em_execucao')
        self.assertEqual(propria.responsavel, self.ti_a)

    def test_usuario_comum_nao_atende(self):
        solicitacao = self.criar(self.unidade_a, self.usuario_a)
        self.client.force_login(self.usuario_a)
        self.client.post(reverse('gestao_acessos_atender', args=[solicitacao.pk]), {
            'status': 'concluida', 'observacao_ti': 'indevido',
        })
        solicitacao.refresh_from_db()
        self.assertEqual(solicitacao.status, 'pendente')

    def test_abertura_aceita_multiplos_anexos(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(reverse('gestao_acessos_nova'), {
            'tipo': 'admissao', 'prioridade': 'normal',
            'colaborador_nome': 'Maria Silva', 'setor': self.setor.pk,
            'sistemas': 'MV', 'justificativa': 'Nova colaboradora',
            'anexos': [
                SimpleUploadedFile('termo.pdf', b'%PDF-1.4', content_type='application/pdf'),
                SimpleUploadedFile('lista.csv', b'sistema,perfil', content_type='text/csv'),
            ],
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(AnexoSolicitacaoAcesso.objects.count(), 2)
        for anexo in AnexoSolicitacaoAcesso.objects.all():
            self.addCleanup(anexo.arquivo.delete, False)

    def test_anexo_bloqueia_executavel_e_download_de_outra_unidade(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(reverse('gestao_acessos_nova'), {
            'tipo': 'admissao', 'prioridade': 'normal',
            'colaborador_nome': 'Maria Silva', 'setor': self.setor.pk,
            'sistemas': 'MV', 'justificativa': 'Teste',
            'anexos': SimpleUploadedFile('programa.exe', b'MZ'),
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(SolicitacaoAcesso.objects.count(), 0)

        solicitacao = self.criar(self.unidade_b, self.usuario_b)
        anexo = AnexoSolicitacaoAcesso.objects.create(
            solicitacao=solicitacao,
            arquivo=SimpleUploadedFile('documento.pdf', b'%PDF-1.4'),
            nome_original='documento.pdf', enviado_por=self.usuario_b,
        )
        self.addCleanup(anexo.arquivo.delete, False)
        resposta = self.client.get(reverse('gestao_acessos_anexo', args=[anexo.pk]))
        self.assertEqual(resposta.status_code, 403)
