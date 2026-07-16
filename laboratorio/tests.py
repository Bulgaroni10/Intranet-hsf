from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from usuarios.models import Unidade, Usuario
from .models import DocumentoExame, ExameLaboratorial

class LaboratorioTests(TestCase):
    def setUp(self):
        self.u1=Unidade.objects.create(nome='A',sigla='UA'); self.u2=Unidade.objects.create(nome='B',sigla='UB')
        lab,_=Group.objects.get_or_create(name='Laboratório'); rec,_=Group.objects.get_or_create(name='Recepção')
        self.lab=Usuario.objects.create_user(username='lab',password='123',unidade=self.u1); self.lab.groups.add(lab)
        self.rec=Usuario.objects.create_user(username='rec',password='123',unidade=self.u1); self.rec.groups.add(rec)
        self.outro=Usuario.objects.create_user(username='outro',password='123',unidade=self.u2); self.outro.groups.add(lab)
        self.comum=Usuario.objects.create_user(username='comum',password='123',unidade=self.u1)
    def criar(self): return ExameLaboratorial.objects.create(unidade=self.u1,criado_por=self.lab,nome='Hemograma',categoria='hematologia',material='Sangue')
    def test_laboratorio_cadastra(self):
        self.client.force_login(self.lab); r=self.client.post(reverse('laboratorio_novo'),{'nome':'Hemograma','categoria':'hematologia','material':'Sangue','ativo':'on'})
        self.assertEqual(r.status_code,302); self.assertEqual(ExameLaboratorial.objects.count(),1)
    def test_recepcao_consulta_mas_nao_edita(self):
        e=self.criar(); self.client.force_login(self.rec)
        self.assertEqual(self.client.get(reverse('laboratorio_detalhe',args=[e.pk])).status_code,200)
        self.assertEqual(self.client.get(reverse('laboratorio_editar',args=[e.pk])).status_code,403)
    def test_unidade_nao_visualiza_outra(self):
        e=self.criar(); self.client.force_login(self.outro)
        self.assertEqual(self.client.get(reverse('laboratorio_detalhe',args=[e.pk])).status_code,404)
    def test_usuario_sem_grupo_recebe_403(self):
        self.client.force_login(self.comum); self.assertEqual(self.client.get(reverse('laboratorio_lista')).status_code,403)

    def test_documento_de_outra_unidade_nao_pode_ser_baixado(self):
        exame = self.criar()
        documento = DocumentoExame.objects.create(
            exame=exame,
            arquivo='laboratorio/teste/ficha.pdf',
            nome_original='ficha.pdf',
            tipo_mime='application/pdf',
            tamanho=10,
            enviado_por=self.lab,
        )
        self.client.force_login(self.outro)
        resposta = self.client.get(reverse('laboratorio_documento', args=[documento.pk]))
        self.assertEqual(resposta.status_code, 403)
