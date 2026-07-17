# GSF Hub — Intranet Hospitalar

Documentação central da intranet do Grupo São Francisco. Este arquivo indica como o sistema funciona, onde alterar cada recurso e como publicar, testar e diagnosticar a aplicação.

## Visão geral

A GSF Hub é uma aplicação Django multiunidade usada para comunicação, atendimento e operação hospitalar. Cada usuário acessa somente as unidades autorizadas pela TI e os dados funcionais devem permanecer isolados pela unidade ativa.

Produção: `http://intranet.osascohsf.hosp/`

Fluxo atual:

```text
Navegador -> IIS (proxy reverso) -> 127.0.0.1:8000 -> Waitress/Django (serviço IntranetGSF)
                                                       |-> banco principal
                                                       |-> arquivos em media/
                                                       |-> estáticos em staticfiles/
```

O servidor é Windows Server, a aplicação roda como serviço Windows gerenciado pelo NSSM e o IIS publica o endereço corporativo.

## Mapa dos módulos

| Área | Diretório principal | Responsabilidade |
|---|---|---|
| Portal, dashboard e NOC | `core/` | layout global, painel, notificações, favoritos, busca e NOC |
| Usuários e unidades | `usuarios/` | autenticação, unidade ativa, unidades permitidas e escopo |
| Solicitações TI | `solicitacoes_ti/` | chamados e atendimento da TI |
| Inventário TI | `inventario_ti/` | computadores, patrimônio, suprimentos, impressoras e monitoramento |
| Gestão de acessos | `gestao_acessos/` | admissão, alteração e remoção de acessos |
| Acesso remoto/VPN | `acesso_remoto/` | solicitações e controle de acesso remoto |
| Recursos Humanos | `recursos_humanos/` | rotinas internas de RH |
| Financeiro/Faturamento | `financeiro_faturamento/` | rotinas restritas aos grupos autorizados |
| Laboratório | `laboratorio/` | catálogo e informações de exames |
| Comunicação | `avisos/`, `conversas/`, `ramais_contatos/` | avisos, mensagens e ramais |
| Conhecimento | `documentos/`, `base_conhecimento/`, `conteudos/` | documentos, manuais e base interna |
| Sistemas hospitalares | `convenios/`, `status_sistemas/` | consultas MV/convênios e status dos sistemas |
| Auditoria e módulos | `auditoria/`, `modulos/` | rastreabilidade e catálogo/permissões dos módulos |

## Onde alterar cada coisa

| O que deseja alterar | Arquivo ou diretório |
|---|---|
| Configuração geral, banco, fuso, logs e segurança | `intranet_gsf/settings.py` |
| Rotas globais | `intranet_gsf/urls.py` |
| Rotas de um módulo | `<app>/urls.py` |
| Menu lateral | `core/templates/partials/sidebar.html` |
| Barra superior e notificações | `core/templates/partials/header.html` |
| Contexto global do usuário/menu | `core/context_processors.py` |
| Dashboard | `core/templates/core/dashboard.html` e `core/services/dashboard.py` |
| Tela NOC | templates/serviços de NOC em `core/` e estilos em `core/static/core/css/` |
| Tema escuro e layout global | `core/static/core/css/theme.css`, `gsf-ui.css` e `gsf-layout.css` |
| Modelo de uma informação | `<app>/models.py` |
| Validação de formulário | `<app>/forms.py` |
| Regra de negócio | `<app>/services*.py` |
| Página/endpoint | `<app>/views.py` ou módulos dentro de `views/`/`view_modules/` |
| HTML de um módulo | `<app>/templates/<app>/` |
| CSS específico | `<app>/static/<app>/` ou `core/static/core/css/` |
| Permissões e perfis centrais | `core/services/permissions.py` |
| Escopo por unidade | helpers em `usuarios/` e middleware `usuarios/middleware.py` |
| Modelo e API de notificações | `core/models.py`, `core/services/notifications.py`, `core/view_modules/notifications.py` |
| Monitoramento de impressoras | `inventario_ti/services_impressoras.py` e comando `monitorar_impressoras` |
| Alertas de estoque | `inventario_ti/services_suprimentos.py` |
| Agente dos computadores | `agentes/inventario_ti/` |
| Testes | `<app>/tests.py` ou `<app>/tests/` |
| Migração de banco após mudar modelo | `<app>/migrations/` |

Regra prática: não coloque regra de permissão somente no template. A view/queryset também deve validar o perfil e a unidade ativa.

## Ambiente local

```powershell
cd C:\Projetos\intranet_gsf
$env:GSF_DEBUG='true'
$env:GSF_SECRET_KEY='somente-desenvolvimento-local'
$env:GSF_ALLOWED_HOSTS='127.0.0.1,localhost,testserver'
C:\Projetos\venv_intranet\Scripts\python.exe manage.py migrate
C:\Projetos\venv_intranet\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

O arquivo `.env.example` é apenas referência; o projeto não o carrega automaticamente. Em produção, as variáveis ficam no ambiente do serviço Windows.

Variáveis essenciais:

- `GSF_DEBUG=false` em produção;
- `GSF_SECRET_KEY` longa, exclusiva e não versionada;
- `GSF_ALLOWED_HOSTS` com os nomes de acesso;
- `GSF_LOG_DIR` e `GSF_LOG_LEVEL`;
- `GSF_PRINTER_ADMIN_PASSWORD` para leitura autenticada da manutenção Brother;
- `GSF_DB_ENGINE` e credenciais do banco quando PostgreSQL for ativado;
- variáveis `GSF_MV_*` somente para a integração Oracle autorizada.

Nunca grave senhas, chaves ou credenciais no Git, em templates ou na documentação.

## Alteração de modelo e arquivos estáticos

Depois de alterar `models.py`:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py makemigrations
C:\Projetos\venv_intranet\Scripts\python.exe manage.py migrate
```

Depois de alterar CSS, JavaScript ou imagens:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py collectstatic --noinput --clear
```

## Testes antes de publicar

```powershell
cd C:\Projetos\intranet_gsf
C:\Projetos\venv_intranet\Scripts\python.exe manage.py check
C:\Projetos\venv_intranet\Scripts\python.exe manage.py makemigrations --check
C:\Projetos\venv_intranet\Scripts\python.exe manage.py test
```

Mudanças de escopo precisam testar explicitamente que um usuário da unidade A não consegue listar, abrir ou alterar dados da unidade B.

## Git e publicação

No computador de desenvolvimento:

```powershell
cd C:\Projetos\intranet_gsf
git status
git add .
git commit -m "Descreva a alteração"
git push origin main
```

No servidor:

```powershell
cd C:\Projetos\intranet_gsf
git status
git pull origin main
C:\Projetos\venv_intranet\Scripts\python.exe manage.py migrate
C:\Projetos\venv_intranet\Scripts\python.exe manage.py collectstatic --noinput
C:\Projetos\venv_intranet\Scripts\python.exe manage.py check
Restart-Service IntranetGSF
```

Valide depois da reinicialização:

```powershell
Start-Sleep -Seconds 3
Invoke-WebRequest http://127.0.0.1:8000/health/ -UseBasicParsing -TimeoutSec 15 |
    Select-Object StatusCode, Content
Invoke-WebRequest http://intranet.osascohsf.hosp/health/ -UseBasicParsing -TimeoutSec 15 |
    Select-Object StatusCode, Content
```

Execute cada bloco separadamente. O prompt `>>` significa que o PowerShell ainda espera o restante do comando; `Ctrl+C` cancela uma linha montada incorretamente.

## Monitoramentos e tarefas

Impressoras:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_impressoras
Get-ScheduledTaskInfo -TaskName 'GSF-Monitorar-Impressoras'
```

Agente de computadores:

```powershell
Get-ScheduledTask -TaskName 'GSF-Agent-Inventario'
Get-Content 'C:\ProgramData\GSF\Agent\logs\gsf-agent.log' -Tail 20
```

As impressoras não precisam estar instaladas no servidor de impressão: o servidor da intranet precisa alcançar o IP fixo da impressora por HTTP/HTTPS ou SNMP. Consulte `docs/MONITORAMENTO_IMPRESSORAS.md` para Brother, Kyocera e Ricoh.

## Diagnóstico rápido

```powershell
Get-Service IntranetGSF
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
Test-NetConnection 127.0.0.1 -Port 8000
Get-Content C:\Projetos\intranet_gsf\logs\gsf-hub.log -Tail 100
```

- Público 200 e loopback falhou uma vez: a aplicação está publicada; o teste local provavelmente ocorreu durante inicialização/reinício. Repita após alguns segundos e confira porta/log.
- Loopback 200 e público 502: o Django está saudável; verifique IIS/proxy.
- Ambos falham: verifique serviço, porta, ambiente e log.
- Não cole dois `Invoke-WebRequest` na mesma linha depois de `Select-Object`.

O procedimento detalhado está em `docs/RUNBOOK_INCIDENTES.md`.

## Banco, backup e limitações atuais

- A produção ainda deve ser tratada como SQLite até a migração PostgreSQL ser formalmente aprovada e executada.
- O ensaio PostgreSQL e sua documentação estão em `docs/MIGRACAO_POSTGRESQL.md`.
- Antes de operações no banco, pare escritas controladamente e faça cópia validada do banco e da pasta `media/`.
- Nunca apague manualmente arquivos `-journal`, `-wal` ou `-shm`.
- A sincronização pesada do MV permanece desativada enquanto puder afetar a disponibilidade.
- A ampliação de CPU/RAM do servidor está pausada, mas continua no roadmap de capacidade.

## Documentação complementar

- `docs/ARCHITECTURE.md`: arquitetura técnica e fluxo de requisição;
- `docs/PERMISSIONS.md`: isolamento por unidade e perfis;
- `docs/DEPLOY.md`: implantação;
- `docs/RUNBOOK_INCIDENTES.md`: atendimento de incidentes;
- `docs/MONITORAMENTO_IMPRESSORAS.md`: cadastro e coleta das impressoras;
- `docs/MIGRACAO_POSTGRESQL.md`: ensaio e migração do banco;
- `docs/BACKUP_E_RESTAURACAO.md`: backup diário e recuperação;
- `docs/SINCRONIZACAO_MV.md`: integração MV;
- `docs/DESIGN_SYSTEM.md`: padrão visual;
- `docs/ROADMAP.md` e `docs/BACKLOG.md`: evolução planejada.

Mantenha este README atualizado sempre que um módulo, tarefa agendada, variável de ambiente ou procedimento de implantação mudar.
