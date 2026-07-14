#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [string]$Unidade = 'HSFOS'
)

$ErrorActionPreference = 'Stop'
$managePy = Join-Path $Projeto 'manage.py'
$regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\IntranetGSF\Parameters'
$logDir = 'C:\ProgramData\GSF\logs'
$logFile = Join-Path $logDir ("sincronizacao-mv-{0}.log" -f (Get-Date -Format 'yyyy-MM'))

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

$obrigatorias = @('GSF_MV_DB_USER', 'GSF_MV_DB_PASSWORD', 'GSF_MV_DB_DSN')
$ausentes = @($obrigatorias | Where-Object { -not [Environment]::GetEnvironmentVariable($_, 'Process') })
if ($ausentes.Count -gt 0) {
    throw "Configuração Oracle ausente no serviço IntranetGSF: $($ausentes -join ', ')"
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$inicio = "[{0}] Início da sincronização MV da unidade {1}." -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Unidade
Add-Content -LiteralPath $logFile -Value $inicio -Encoding UTF8

$saida = & $Python $managePy sincronizar_convenios_mv --unidade $Unidade 2>&1
$codigoSaida = $LASTEXITCODE
$saida | ForEach-Object { Add-Content -LiteralPath $logFile -Value $_ -Encoding UTF8 }

$fim = "[{0}] Fim da sincronização. Código de saída: {1}." -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $codigoSaida
Add-Content -LiteralPath $logFile -Value $fim -Encoding UTF8

if ($codigoSaida -ne 0) {
    throw "A sincronização MV terminou com código $codigoSaida. Consulte $logFile."
}

$saida

