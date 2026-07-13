# Distribuição do GSF Agent por GPO

## Gerar o executável

Em uma máquina Windows de desenvolvimento:

```powershell
.\build_agent.ps1
```

O build gera:

- `dist\GSFAgent.exe`, independente de uma instalação de Python no computador de destino;
- `dist\GSFAgent.exe.sha256`, usado para validar a integridade antes da instalação.

## Publicar

Copie os dois arquivos gerados e `instalar_gpo.ps1` para um compartilhamento que permita leitura ao grupo `Domain Computers`.

## Configurar a GPO

Use `instalar_gpo.ps1` como script de inicialização dos computadores da OU correspondente. Exemplo para o HSFOS:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "\\SERVIDOR\GSF-Agent\instalar_gpo.ps1" -Origem "\\SERVIDOR\GSF-Agent" -UnitCode "HSFOS"
```

O instalador:

- valida o SHA-256;
- copia para `C:\ProgramData\GSF\Agent`;
- cria o `config.json` da unidade;
- registra a tarefa `GSF-Agent-Inventario` no boot como `SYSTEM`;
- inicia o agente imediatamente;
- pode ser reaplicado para atualizar o executável sem duplicar a tarefa.

Não conceda permissão de escrita no compartilhamento aos computadores do domínio.
