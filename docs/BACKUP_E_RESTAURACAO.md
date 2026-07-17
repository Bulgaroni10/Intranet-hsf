# Backup e restauração da GSF Hub

## Política atual

- backup diário às 02:00;
- banco SQLite copiado pela API de backup, sem interromper a intranet;
- pasta `media/` compactada junto com os anexos;
- retenção local padrão de 14 dias;
- destino padrão: `C:\Backups\GSF-Hub`;
- log: `C:\ProgramData\GSF\logs\backup-gsf.log`.

Uma cópia no mesmo disco protege contra erro lógico, mas não contra falha do disco ou da VM. O diretório deve também ser replicado para armazenamento externo controlado pela TI.

## Instalação

```powershell
cd C:\Projetos\intranet_gsf
powershell.exe -ExecutionPolicy Bypass -File scripts\instalar_backup_gsf.ps1
```

## Validação

```powershell
Get-ScheduledTaskInfo -TaskName 'GSF-Backup-Diario' |
    Select-Object LastRunTime, LastTaskResult, NextRunTime
Get-ChildItem C:\Backups\GSF-Hub | Sort-Object Name -Descending | Select-Object -First 3
Get-Content C:\ProgramData\GSF\logs\backup-gsf.log -Tail 30
```

`LastTaskResult` deve ser `0`. Cada pasta contém `db.sqlite3`, `media.zip` e `manifesto.json` com tamanho e SHA-256.

## Restauração controlada

1. anuncie a indisponibilidade e pare `IntranetGSF`;
2. faça uma cópia do estado atual antes de substituir qualquer arquivo;
3. valide os hashes do `manifesto.json`;
4. substitua `db.sqlite3` pelo backup escolhido;
5. restaure `media.zip` para a pasta `media/`, preservando permissões;
6. execute `manage.py migrate` e `manage.py check`;
7. inicie o serviço e valide os dois endpoints `/health/`.

Nunca restaure diretamente em produção sem preservar o estado atual. Faça um teste periódico de restauração em uma pasta ou ambiente separado.
