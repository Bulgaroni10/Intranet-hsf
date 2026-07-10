from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from modulos.models import Modulo
from .models import ProcedimentoTUSS
from .services import buscar_procedimentos_tuss


class CatalogoTUSSTests(TestCase):
    def setUp(self):
        self.grupo = Group.objects.create(name='Recepção TUSS')
        self.modulo = Modulo.objects.get(nome='Código TUSS')
        self.modulo.grupos_permitidos.clear()
        self.modulo.grupos_permitidos.add(self.grupo)
        self.autorizado = get_user_model().objects.create_user('recepcao.teste')
        self.autorizado.groups.add(self.grupo)
        self.bloqueado = get_user_model().objects.create_user('outro.teste')
        ProcedimentoTUSS.objects.create(
            codigo_tuss='40302784', descricao='Exame de teste', grupo='Exames', codigo_mv='MV123'
        )

    def test_pesquisa_por_codigo_descricao_e_mv(self):
        for termo in ('40302784', 'exame', 'MV123'):
            self.assertEqual(buscar_procedimentos_tuss(busca=termo).count(), 1)

    def test_usuario_autorizado_acessa_catalogo(self):
        self.client.force_login(self.autorizado)
        self.assertEqual(self.client.get(reverse('catalogo_tuss')).status_code, 200)

    def test_usuario_sem_grupo_recebe_403(self):
        self.client.force_login(self.bloqueado)
        self.assertEqual(self.client.get(reverse('catalogo_tuss')).status_code, 403)

# Create your tests here.
