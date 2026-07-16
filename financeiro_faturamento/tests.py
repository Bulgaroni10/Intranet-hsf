from datetime import date
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from usuarios.models import Unidade, Usuario
from .models import RegistroFinanceiro
from .forms import RegistroFinanceiroForm

class FinanceiroTests(TestCase):
    def setUp(self):
        self.u1 = Unidade.objects.create(nome='A', sigla='UA'); self.u2 = Unidade.objects.create(nome='B', sigla='UB')
        grupo = Group.objects.create(name='Financeiro')
        self.f1 = Usuario.objects.create_user(username='f1', password='123', unidade=self.u1); self.f1.groups.add(grupo)
        self.f2 = Usuario.objects.create_user(username='f2', password='123', unidade=self.u2); self.f2.groups.add(grupo)
        self.comum = Usuario.objects.create_user(username='comum', password='123', unidade=self.u1)

    def criar(self):
        return RegistroFinanceiro.objects.create(unidade=self.u1, criado_por=self.f1, area='financeiro', tipo='fechamento', titulo='Fechamento', competencia=date(2026, 7, 1), descricao='Teste')

    def test_usuario_comum_recebe_403(self):
        self.client.force_login(self.comum); self.assertEqual(self.client.get(reverse('financeiro_lista')).status_code, 403)

    def test_outra_unidade_nao_visualiza(self):
        item = self.criar(); self.client.force_login(self.f2)
        self.assertEqual(self.client.get(reverse('financeiro_detalhe', args=[item.pk])).status_code, 404)

    def test_grupo_autorizado_cria_registro(self):
        self.client.force_login(self.f1)
        resposta = self.client.post(reverse('financeiro_novo'), {'area':'financeiro','tipo':'fechamento','titulo':'Fechamento','competencia':'2026-07','prioridade':'normal','status':'pendente','descricao':'Teste'})
        self.assertEqual(resposta.status_code, 302); self.assertEqual(RegistroFinanceiro.objects.count(), 1)

    def test_responsaveis_somente_grupos_autorizados_da_unidade(self):
        gerente = Group.objects.create(name='Gerência')
        usuario_gerente = Usuario.objects.create_user(
            username='gerente', password='123', unidade=self.u1,
        )
        usuario_gerente.groups.add(gerente)
        form = RegistroFinanceiroForm(unidade=self.u1)
        responsaveis = form.fields['responsavel'].queryset
        self.assertIn(self.f1, responsaveis)
        self.assertIn(usuario_gerente, responsaveis)
        self.assertNotIn(self.f2, responsaveis)
        self.assertNotIn(self.comum, responsaveis)
