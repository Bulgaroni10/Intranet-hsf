from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from modulos.models import Modulo


class Command(BaseCommand):
    help = 'Cria os módulos iniciais da intranet.'

    def handle(self, *args, **options):
        modulos = [
            {
                'nome': 'MV / Sistema Hospitalar',
                'descricao': 'Manuais, convênios e contingência',
                'categoria': 'assistencial',
                'icone': '🏥',
                'tag': 'MV',
                'ordem': 10,
                'palavras': 'mv sistema hospitalar recepção convênios contingência atendimento',
                'grupos': ['TI Administrador', 'Recepção', 'Agendamento', 'Cadastro', 'Farmácia', 'Laboratório', 'Enfermagem', 'Médico'],
            },
            {
                'nome': 'Prontuário Eletrônico',
                'descricao': 'Manuais e plano de contingência',
                'categoria': 'assistencial',
                'icone': '📋',
                'tag': 'PEP',
                'ordem': 20,
                'palavras': 'pep prontuário eletrônico médicos enfermagem evolução prescrição',
                'grupos': ['TI Administrador', 'Médico', 'Enfermagem', 'Farmácia'],
            },
            {
                'nome': 'Agendamento',
                'descricao': 'Escalas, especialidades e convênios',
                'categoria': 'assistencial',
                'icone': '📅',
                'tag': '',
                'ordem': 30,
                'palavras': 'agendamento escalas médicos especialidades consultas convênios',
                'grupos': ['TI Administrador', 'Recepção', 'Agendamento', 'Cadastro', 'Gerência'],
            },
            {
                'nome': 'Laboratório',
                'descricao': 'Exames, prazos e manuais',
                'categoria': 'assistencial',
                'icone': '🧪',
                'tag': '',
                'ordem': 40,
                'palavras': 'laboratório exames matrix coleta resultado',
                'grupos': ['TI Administrador', 'Laboratório', 'Recepção', 'Médico', 'Enfermagem'],
            },
            {
                'nome': 'Farmácia',
                'descricao': 'Medicamentos, manuais e PDFs',
                'categoria': 'assistencial',
                'icone': '💊',
                'tag': '',
                'ordem': 50,
                'palavras': 'farmácia medicamentos estoque controlados livro mv',
                'grupos': ['TI Administrador', 'Farmácia', 'Enfermagem', 'Médico'],
            },
            {
                'nome': 'IDCE / Laudos',
                'descricao': 'Manuais médicos e recepção',
                'categoria': 'assistencial',
                'icone': '🩻',
                'tag': 'IDCE',
                'ordem': 60,
                'palavras': 'idce laudos imagens exames médicos recepção',
                'grupos': ['TI Administrador', 'Médico', 'Recepção', 'Agendamento'],
            },
            {
                'nome': 'Doctor ID',
                'descricao': 'Escalas médicas e plantões',
                'categoria': 'assistencial',
                'icone': '🩺',
                'tag': 'Doctor ID',
                'ordem': 70,
                'palavras': 'doctor id escalas médicas plantão corpo clínico',
                'grupos': ['TI Administrador', 'Médico', 'Gerência', 'Diretoria', 'Responsável Técnico'],
            },
            {
                'nome': 'Cadastro',
                'descricao': 'Solicitações e orientações',
                'categoria': 'assistencial',
                'icone': '🧾',
                'tag': '',
                'ordem': 80,
                'palavras': 'cadastro convênios exames procedimentos mv',
                'grupos': ['TI Administrador', 'Cadastro', 'Gerência', 'Responsável Técnico', 'Diretoria'],
            },
            {
                'nome': 'Recursos Humanos',
                'descricao': 'Benefícios, contatos e dúvidas',
                'categoria': 'administrativo',
                'icone': '👥',
                'tag': 'RH',
                'ordem': 10,
                'palavras': 'rh recursos humanos salário vt va vr benefícios dúvidas',
                'grupos': [],
                'link': '/portal/recursos-humanos/',
            },
            {
                'nome': 'Financeiro / Faturamento',
                'descricao': 'Rotinas e manuais internos',
                'categoria': 'administrativo',
                'icone': '💰',
                'tag': '',
                'ordem': 20,
                'palavras': 'financeiro faturamento contas manuais mv',
                'grupos': ['TI Administrador', 'Financeiro', 'Faturamento', 'Gerência', 'Diretoria'],
            },
            {
                'nome': 'Suprimentos / Compras',
                'descricao': 'Solicitações e status',
                'categoria': 'administrativo',
                'icone': '📦',
                'tag': '',
                'ordem': 30,
                'palavras': 'suprimentos compras pedidos solicitações fornecedores',
                'grupos': ['TI Administrador', 'Suprimentos', 'Gerência', 'Diretoria', 'Responsável Técnico'],
            },
            {
                'nome': 'Documentos e Protocolos',
                'descricao': 'POPs, normas e PDFs',
                'categoria': 'administrativo',
                'icone': '📄',
                'tag': '',
                'ordem': 40,
                'palavras': 'documentos protocolos pop manuais pdf normas qualidade',
                'grupos': [],
            },
            {
                'nome': 'Ramais e Contatos',
                'descricao': 'Setores e unidades',
                'categoria': 'administrativo',
                'icone': '☎️',
                'tag': '',
                'ordem': 50,
                'palavras': 'ramais contatos telefone unidades setores',
                'grupos': [],
            },
            {
                'nome': 'Abrir Chamado de TI',
                'descricao': 'Suporte e solicitações',
                'categoria': 'tecnologia',
                'icone': '🖥️',
                'tag': 'TI',
                'ordem': 10,
                'palavras': 'abrir chamado ti suporte incidente solicitação',
                'grupos': [],
            },
            {
                'nome': 'Status dos Sistemas',
                'descricao': 'Disponibilidade e alertas',
                'categoria': 'tecnologia',
                'icone': '📊',
                'tag': '',
                'ordem': 20,
                'palavras': 'status sistemas mv pep idce rd nuria kflow doctor id',
                'grupos': [],
            },
            {
                'nome': 'Gestão de Acessos',
                'descricao': 'Usuários, grupos e permissões',
                'categoria': 'tecnologia',
                'icone': '🔐',
                'tag': '',
                'ordem': 30,
                'palavras': 'gestão acessos usuários permissões grupos senha reset',
                'grupos': [],
                'link': '/portal/gestao-acessos/',
            },
            {
                'nome': 'Segurança da Informação',
                'descricao': 'Políticas, redes e orientações',
                'categoria': 'tecnologia',
                'icone': '🛡️',
                'tag': '',
                'ordem': 40,
                'palavras': 'segurança informação lgpd phishing senhas ips vpn',
                'grupos': ['TI Administrador', 'TI Suporte', 'Diretoria', 'Gerência'],
            },
            {
                'nome': 'Acesso Remoto / VPN',
                'descricao': 'Contingência e configurações',
                'categoria': 'tecnologia',
                'icone': '🌐',
                'tag': '',
                'ordem': 50,
                'palavras': 'vpn acesso remoto openvpn contingência',
                'grupos': ['TI Administrador', 'TI Suporte', 'Gerência', 'Diretoria'],
                'link': '/portal/acesso-remoto/',
            },
            {
                'nome': 'Inventário de Ativos',
                'descricao': 'Equipamentos, impressoras e toners',
                'categoria': 'tecnologia',
                'icone': '🏷️',
                'tag': '',
                'ordem': 60,
                'palavras': 'inventário ativos computadores impressoras toners unidades patrimônio',
                'grupos': ['TI Administrador', 'TI Suporte', 'Gerência', 'Diretoria'],
            },
        ]

        for item in modulos:
            modulo, criado = Modulo.objects.get_or_create(
                nome=item['nome'],
                defaults={
                    'descricao': item['descricao'],
                    'categoria': item['categoria'],
                    'icone': item['icone'],
                    'tag': item['tag'],
                    'ordem': item['ordem'],
                    'palavras_chave': item['palavras'],
                    'ativo': True,
                    'link': item.get('link', '#'),
                }
            )

            if not criado:
                modulo.descricao = item['descricao']
                modulo.categoria = item['categoria']
                modulo.icone = item['icone']
                modulo.tag = item['tag']
                modulo.ordem = item['ordem']
                modulo.palavras_chave = item['palavras']
                modulo.link = item.get('link', modulo.link)
                modulo.ativo = True
                modulo.save()

            modulo.grupos_permitidos.clear()

            for nome_grupo in item['grupos']:
                grupo, _ = Group.objects.get_or_create(name=nome_grupo)
                modulo.grupos_permitidos.add(grupo)

            if criado:
                self.stdout.write(self.style.SUCCESS(f'Módulo criado: {modulo.nome}'))
            else:
                self.stdout.write(f'Módulo atualizado: {modulo.nome}')

        self.stdout.write(self.style.SUCCESS('Módulos iniciais criados/atualizados com sucesso.'))
