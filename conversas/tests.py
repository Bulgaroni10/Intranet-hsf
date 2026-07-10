import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import NotificacaoUsuario
from .models import AnexoMensagem, ConversaChat, MensagemChat


class ConversasSegurancaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.remetente = User.objects.create_user('remetente.teste')
        self.destinatario = User.objects.create_user('destinatario.teste')
        self.intruso = User.objects.create_user('intruso.teste')
        self.conversa = ConversaChat.objects.create(criado_por=self.remetente)
        self.conversa.participantes.add(self.remetente, self.destinatario)

    def test_envio_notifica_destinatario_e_nao_remetente(self):
        self.client.force_login(self.remetente)
        resposta = self.client.post(reverse('api_enviar_mensagem'), {
            'conversa_id': self.conversa.id, 'texto': 'Olá',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(NotificacaoUsuario.objects.filter(usuario=self.destinatario).count(), 1)
        self.assertFalse(NotificacaoUsuario.objects.filter(usuario=self.remetente).exists())

    def test_upload_permitido_e_download_restrito_a_participantes(self):
        self.client.force_login(self.remetente)
        arquivo = SimpleUploadedFile('guia.pdf', b'%PDF-1.4 teste', content_type='application/pdf')
        resposta = self.client.post(reverse('api_enviar_mensagem'), {
            'conversa_id': self.conversa.id, 'texto': '', 'arquivo': arquivo,
        })
        self.assertEqual(resposta.status_code, 200)
        anexo = AnexoMensagem.objects.get()

        self.client.force_login(self.destinatario)
        self.assertEqual(self.client.get(reverse('baixar_anexo_mensagem', args=[anexo.id])).status_code, 200)
        self.client.force_login(self.intruso)
        self.assertEqual(self.client.get(reverse('baixar_anexo_mensagem', args=[anexo.id])).status_code, 404)

    def test_extensao_perigosa_e_mime_incompativel_sao_bloqueados(self):
        self.client.force_login(self.remetente)
        for arquivo in (
            SimpleUploadedFile('malware.exe', b'MZ', content_type='application/x-msdownload'),
            SimpleUploadedFile('falso.pdf', b'exe', content_type='application/x-msdownload'),
        ):
            resposta = self.client.post(reverse('api_enviar_mensagem'), {
                'conversa_id': self.conversa.id, 'arquivo': arquivo,
            })
            self.assertEqual(resposta.status_code, 400)
        self.assertFalse(MensagemChat.objects.exists())
