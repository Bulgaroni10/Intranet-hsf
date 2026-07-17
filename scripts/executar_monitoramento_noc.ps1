#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe'
)

$ErrorActionPreference = 'Stop'
$managePy = Join-Path $Projeto 'manage.py'
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\IntranetGSF\Parameters'
$logDir = 'C:\ProgramData\GSF\logs'
$logFile = Join-Path $logDir 'monitoramento-noc.log'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}
if (-not (Test-Path -LiteralPath $managePy)) {
    throw "Projeto Django não encontrado: $managePy"
}

$ambiente = @(
    (Get-ItemProperty -Path $regPath -Name AppEnvironmentExtra -ErrorAction Stop).AppEnvironmentExtra
)
foreach ($linha in $ambiente) {
    if ($linha -and $linha.Contains('=')) {
        $partes = $linha.Split('=', 2)
        [Environment]::SetEnvironmentVariable($partes[0], $partes[1], 'Process')
    }
}

if (-not [Environment]::GetEnvironmentVariable('GSF_SECRET_KEY', 'Process')) {
    throw 'GSF_SECRET_KEY não foi encontrada no ambiente do serviço IntranetGSF.'
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$inicio = '[{0}] Início do monitoramento do NOC.' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Add-Content -LiteralPath $logFile -Value $inicio -Encoding UTF8

$saida = & $Python $managePy monitorar_noc 2>&1
$codigoSaida = $LASTEXITCODE
$saida | ForEach-Object { Add-Content -LiteralPath $logFile -Value $_ -Encoding UTF8 }

$fim = '[{0}] Fim do monitoramento. Código de saída: {1}.' -f (
    Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
), $codigoSaida
Add-Content -LiteralPath $logFile -Value $fim -Encoding UTF8

if ($codigoSaida -ne 0) {
    throw "O monitoramento terminou com código $codigoSaida. Consulte $logFile."
}

$saida
