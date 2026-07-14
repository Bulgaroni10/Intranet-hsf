# Monitoramento de impressoras no GSF NOC

Este documento explica como cadastrar, testar e manter impressoras no NOC da GSF Hub.

## Resposta rápida: onde o monitoramento deve rodar?

O monitoramento deve rodar no **servidor da intranet**, onde estão o Django, o banco da GSF Hub e a tarefa agendada `GSF-Monitorar-Impressoras`.

Não é necessário instalar nada no servidor de impressão da unidade. O GSF Hub não consulta filas, drivers ou compartilhamentos do Windows: ele acessa diretamente o endereço IP de cada impressora.

O servidor de impressão pode continuar sendo usado normalmente para impressão, mas não participa da coleta do NOC.

```text
Impressora Brother (IP fixo)
        │ HTTP/HTTPS e, opcionalmente, SNMP
        ▼
Servidor da intranet / tarefa agendada
        │ atualiza o banco do Django
        ▼
Portal, notificações da TI e tela do NOC
```

Para impressoras de outra unidade, o servidor central da intranet precisa ter rota e permissão de rede até a VLAN daquela unidade. Se não conseguir alcançar o IP, a impressora aparecerá offline mesmo estando ligada.

## O que é necessário em cada impressora

- IP fixo ou reserva DHCP permanente;
- painel web acessível por HTTP na porta TCP 80 ou HTTPS na porta TCP 443;
- rota entre o servidor da intranet e o IP da impressora;
- preferencialmente SNMP v2 habilitado na porta UDP 161, comunidade de leitura `public`;
- unidade e local corretos no cadastro da GSF Hub.

O monitoramento atual foi preparado para impressoras Brother. Ele não precisa da senha administrativa para consultar a página pública de status. Certificados HTTPS autoassinados são aceitos apenas nessa comunicação interna, e o coletor ignora proxies do Windows ao acessar os IPs cadastrados.

O SNMP é opcional para disponibilidade e toner quando a página web já fornece essas informações. Ele é recomendado para obter contadores adicionais, especialmente cilindro/tambor. Alguns modelos não disponibilizam percentual de cilindro nem mesmo via SNMP; nesses casos o NOC ainda identifica mensagens como `Subst. tambor`, `Tambor!` ou `Substituir Cilindro`.

## Responsabilidade dos servidores

### Servidor da intranet

Deve:

- possuir o projeto em `C:\Projetos\intranet_gsf`;
- usar o Python em `C:\Projetos\venv_intranet\Scripts\python.exe`;
- alcançar os IPs das impressoras;
- executar `manage.py monitorar_noc` automaticamente;
- manter o serviço `IntranetGSF` funcionando;
- armazenar o cadastro, o último estado e as notificações.

### Servidor de impressão

Não precisa:

- executar scripts da GSF Hub;
- ter Python ou agente instalado;
- compartilhar credenciais com a intranet;
- estar ligado para o NOC consultar uma impressora, desde que a rede e a própria impressora estejam disponíveis.

Ele continua responsável somente pelas filas, drivers e trabalhos de impressão da unidade.

## Cadastro inicial do HSFOS

O projeto possui uma carga idempotente da frota conhecida do HSFOS. No servidor da intranet:

```powershell
cd C:\Projetos\intranet_gsf
C:\Projetos\venv_intranet\Scripts\python.exe manage.py cadastrar_impressoras_hsfos
```

O comando pode ser executado novamente: ele atualiza os registros existentes pelo IP sem duplicá-los.

Para cadastrar uma impressora diferente, use **Django Admin → Impressoras monitoradas → Adicionar**, informando:

- unidade;
- IP;
- modelo informado, se conhecido;
- setor/local;
- ativo.

O `modelo_detectado` será preenchido automaticamente na primeira coleta e prevalecerá sobre o modelo informado.

## Teste de rede antes do cadastro

Os testes devem ser executados no servidor da intranet, não no computador do usuário nem necessariamente no servidor de impressão:

```powershell
Test-NetConnection 192.168.0.59 -Port 80
Test-NetConnection 192.168.0.59 -Port 443
```

É suficiente que pelo menos uma das portas web esteja acessível. `TcpTestSucceeded : True` confirma apenas a abertura da porta; a coleta direta confirma se a impressora realmente entrega a página esperada.

Teste direto de uma impressora já cadastrada:

```powershell
cd C:\Projetos\intranet_gsf

C:\Projetos\venv_intranet\Scripts\python.exe manage.py shell -c "from inventario_ti.models import ImpressoraMonitorada as I; from inventario_ti.services_impressoras import consultar_impressora; x=I.objects.get(ip='192.168.0.59'); print(consultar_impressora(x))"
```

Exemplo de resposta válida:

```text
{'modelo_detectado': 'HL-L6402DW', 'status_dispositivo': 'Pronta', 'toner_percentual': 18}
```

## Primeira coleta

Para consultar somente as impressoras:

```powershell
cd C:\Projetos\intranet_gsf
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_impressoras
```

Para atualizar todas as fontes do NOC, incluindo impressoras, AD, rede e capacidade do servidor:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_noc
```

Uma linha `online` confirma que o estado foi gravado. Depois da coleta, o NOC atualiza a tela automaticamente em aproximadamente 30 segundos.

## Instalação da coleta automática

Abra o PowerShell como administrador no servidor da intranet e execute:

```powershell
powershell.exe -ExecutionPolicy Bypass `
    -File C:\Projetos\intranet_gsf\scripts\instalar_monitoramento_impressoras.ps1
```

O instalador cria ou atualiza a tarefa `GSF-Monitorar-Impressoras`, executada como `SYSTEM` a cada cinco minutos. Ele também realiza uma primeira coleta e impede execuções simultâneas.

Validar a tarefa:

```powershell
Get-ScheduledTask -TaskName 'GSF-Monitorar-Impressoras' |
    Select-Object TaskName, State

Get-ScheduledTaskInfo -TaskName 'GSF-Monitorar-Impressoras' |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
```

`LastTaskResult` igual a `0` indica execução concluída com sucesso.

Executar manualmente para teste:

```powershell
Start-ScheduledTask -TaskName 'GSF-Monitorar-Impressoras'
```

## Como o status aparece no NOC

- bolinha verde: a impressora respondeu por web ou SNMP;
- bolinha vermelha: não houve comunicação na última coleta;
- toner e cilindro são mostrados quando o equipamento disponibiliza percentual;
- toner ou cilindro em 20% ou menos gera alerta para a TI;
- mensagens de manutenção também geram alerta;
- uma impressora pode estar online e, ao mesmo tempo, possuir alerta de toner ou tambor.

Os alertas aparecem no NOC, na área principal do portal e nas notificações dos usuários da TI vinculados à mesma unidade.

## Diagnóstico de problemas

### A impressora abre no navegador, mas aparece offline

Faça o teste a partir do servidor da intranet. Abrir no computador do usuário não prova que o servidor possui a mesma rota ou liberação de firewall.

```powershell
Test-NetConnection IP_DA_IMPRESSORA -Port 80
Test-NetConnection IP_DA_IMPRESSORA -Port 443
```

Depois execute uma coleta e consulte o erro salvo:

```powershell
C:\Projetos\venv_intranet\Scripts\python.exe manage.py shell -c "from inventario_ti.models import ImpressoraMonitorada as I; x=I.objects.get(ip='IP_DA_IMPRESSORA'); print(x.online, x.status_dispositivo, x.ultimo_erro, x.ultima_consulta)"
```

### `timed out` ou `handshake operation timed out`

- confirme as portas 80 e 443;
- confirme rota/VLAN e ACL entre o servidor e a impressora;
- confirme que o painel web está habilitado;
- execute o teste direto pelo Python;
- verifique se o servidor está com a versão atual do código.

O coletor tenta HTTP e HTTPS diretamente, aceita o certificado interno da impressora e não utiliza proxy.

### `Sem comunicação`, mas aparece toner antigo

O nível exibido pode ser o último valor conhecido. O status online/offline e o horário da última consulta determinam se o dado é atual.

### O percentual do cilindro fica vazio

- habilite SNMP v2 somente para leitura;
- permita UDP 161 entre servidor da intranet e impressora;
- use a comunidade `public`, que é a configuração atual do coletor;
- confirme se o modelo publica cilindro/tambor na Printer-MIB.

Se o modelo não publicar o contador, o alerta textual de troca de tambor continuará funcionando.

### O modelo cadastrado está errado

O NOC usa primeiro o modelo detectado no painel da impressora. Execute nova coleta; não confie apenas no driver instalado no servidor de impressão.

### A tarefa não está atualizando

```powershell
Get-ScheduledTask -TaskName 'GSF-Monitorar-Impressoras'
Get-ScheduledTaskInfo -TaskName 'GSF-Monitorar-Impressoras'
```

Também execute manualmente:

```powershell
cd C:\Projetos\intranet_gsf
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_noc
```

## Inclusão de uma nova unidade

1. Cadastre a unidade na Administração da GSF Hub.
2. Confirme que o servidor da intranet alcança a rede das impressoras da unidade.
3. Libere TCP 80/443 e, se utilizado, UDP 161 entre as redes.
4. Cadastre cada impressora com IP fixo, unidade e local.
5. Execute `monitorar_impressoras` manualmente.
6. Confirme modelo, status, toner e horário no NOC.
7. A tarefa central já fará as próximas coletas; não crie outra tarefa no servidor de impressão.

Se a unidade não possuir conectividade roteada até o servidor central, a arquitetura atual não conseguirá monitorá-la. Nesse cenário será necessário liberar a comunicação entre unidades ou desenvolver um coletor remoto seguro para enviar os resultados à GSF Hub.

## Atualização do código em produção

Depois de alterações no monitoramento:

```powershell
cd C:\Projetos\intranet_gsf
git pull origin main
C:\Projetos\venv_intranet\Scripts\python.exe manage.py check
C:\Projetos\venv_intranet\Scripts\python.exe manage.py monitorar_impressoras
Restart-Service IntranetGSF
```

Não é necessário reiniciar o servidor de impressão.

## Referências técnicas do projeto

- serviço de coleta: `inventario_ti/services_impressoras.py`;
- cadastro e estado: `inventario_ti/models.py`, modelo `ImpressoraMonitorada`;
- coleta manual: `inventario_ti/management/commands/monitorar_impressoras.py`;
- coleta completa: `inventario_ti/management/commands/monitorar_noc.py`;
- carga inicial HSFOS: `inventario_ti/management/commands/cadastrar_impressoras_hsfos.py`;
- tarefa agendada: `scripts/instalar_monitoramento_impressoras.ps1`;
- tela: `core/templates/core/noc.html`.

Migration principal: `inventario_ti.0006_impressoramonitorada`.
