#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [string]$Destino = 'C:\Backups\GSF-Hub',
    [int]$RetencaoDias = 14
)

$ErrorActionPreference = 'Stop'
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\IntranetGSF\Parameters'
$managePy = Join-Path $Projeto 'manage.py'
$logDir = 'C:\ProgramData\GSF\logs'
$logFile = Join-Path $logDir 'backup-gsf.log'

$ambiente = @((Get-ItemProperty -Path $regPath -Name AppEnvironmentExtra -ErrorAction Stop).AppEnvironmentExtra)
foreach ($linha in $ambiente) {
    if ($linha -and $linha.Contains('=')) {
        $partes = $linha.Split('=', 2)
        [Environment]::SetEnvironmentVariable($partes[0], $partes[1], 'Process')
    }
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$saida = & $Python $managePy backup_gsf --destino $Destino --retencao-dias $RetencaoDias 2>&1
$codigo = $LASTEXITCODE
Add-Content -LiteralPath $logFile -Value ("[{0}] Código {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $codigo) -Encoding UTF8
$saida | ForEach-Object { Add-Content -LiteralPath $logFile -Value $_ -Encoding UTF8 }
if ($codigo -ne 0) { throw "Backup falhou. Consulte $logFile." }
$saida
