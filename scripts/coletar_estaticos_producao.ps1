[CmdletBinding()]
param(
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe'
)

$ErrorActionPreference = 'Stop'
$managePy = Join-Path $Projeto 'manage.py'

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python do ambiente virtual não encontrado: $Python"
}
if (-not (Test-Path -LiteralPath $managePy)) {
    throw "Projeto Django não encontrado: $managePy"
}

$debugAnterior = $env:GSF_DEBUG
$secretAnterior = $env:GSF_SECRET_KEY

try {
    $env:GSF_DEBUG = 'false'
    if (-not $env:GSF_SECRET_KEY) {
        $env:GSF_SECRET_KEY = 'somente-para-coleta-de-estaticos-nao-usada-pelo-servico'
    }

    & $Python $managePy collectstatic --noinput --clear
    if ($LASTEXITCODE -ne 0) {
        throw "collectstatic terminou com código $LASTEXITCODE."
    }

    & $Python $managePy shell -c "from django.contrib.staticfiles.storage import staticfiles_storage; print(staticfiles_storage.url('core/css/home.css')); print(staticfiles_storage.url('core/css/noc.css'))"
    if ($LASTEXITCODE -ne 0) {
        throw 'O manifesto foi gerado, mas a validação dos arquivos obrigatórios falhou.'
    }
}
finally {
    if ($null -eq $debugAnterior) { Remove-Item Env:GSF_DEBUG -ErrorAction SilentlyContinue } else { $env:GSF_DEBUG = $debugAnterior }
    if ($null -eq $secretAnterior) { Remove-Item Env:GSF_SECRET_KEY -ErrorAction SilentlyContinue } else { $env:GSF_SECRET_KEY = $secretAnterior }
}
