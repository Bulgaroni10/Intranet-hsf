[CmdletBinding()]
param(
    [string]$Python = 'C:\Projetos\venv_intranet\Scripts\python.exe',
    [string]$Projeto = 'C:\Projetos\intranet_gsf',
    [string]$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$Banco = 'gsf_hub_homologacao',
    [string]$Usuario = 'gsf_hub_app',
    [string]$Servidor = '127.0.0.1',
    [int]$Porta = 5432
)

$ErrorActionPreference = 'Stop'

function Converter-Senha {
    param([Security.SecureString]$Senha)

    $ponte = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Senha)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponte)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponte)
    }
}

$senhaAdminSegura = Read-Host 'Senha do usuario postgres' -AsSecureString
$senhaAppSegura = Read-Host 'Senha do usuario gsf_hub_app' -AsSecureString
$senhaAdmin = $null
$senhaApp = $null
$permissaoConcedida = $false
$resultadoTestes = 1

try {
    $senhaAdmin = Converter-Senha $senhaAdminSegura
    $senhaApp = Converter-Senha $senhaAppSegura
    if ([string]::IsNullOrWhiteSpace($senhaAdmin) -or
        [string]::IsNullOrWhiteSpace($senhaApp)) {
        throw 'As senhas nao podem ficar vazias.'
    }

    $env:PGPASSWORD = $senhaAdmin
    & $Psql -X -w -v ON_ERROR_STOP=1 -h $Servidor -p $Porta -U postgres `
        -d postgres -c "ALTER ROLE $Usuario CREATEDB;" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'Nao foi possivel conceder CREATEDB temporariamente.'
    }
    $permissaoConcedida = $true

    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:GSF_DEBUG = 'false'
    $env:GSF_SECRET_KEY = 'testes-postgresql-homologacao-12345678901234567890'
    $env:GSF_DB_ENGINE = 'postgresql'
    $env:GSF_DB_NAME = $Banco
    $env:GSF_DB_USER = $Usuario
    $env:GSF_DB_PASSWORD = $senhaApp
    $env:GSF_DB_HOST = $Servidor
    $env:GSF_DB_PORT = [string]$Porta

    & $Python (Join-Path $Projeto 'manage.py') test --noinput
    $resultadoTestes = $LASTEXITCODE
}
finally {
    if ($permissaoConcedida) {
        $env:PGPASSWORD = $senhaAdmin
        & $Psql -X -w -v ON_ERROR_STOP=1 -h $Servidor -p $Porta -U postgres `
            -d postgres -c "ALTER ROLE $Usuario NOCREATEDB;" | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Warning 'Revogue manualmente CREATEDB do usuario gsf_hub_app.'
        }
    }

    Remove-Item Env:PGPASSWORD,Env:PYTHONUTF8,Env:PYTHONIOENCODING `
        -ErrorAction SilentlyContinue
    Remove-Item Env:GSF_DEBUG,Env:GSF_SECRET_KEY,Env:GSF_DB_ENGINE `
        -ErrorAction SilentlyContinue
    Remove-Item Env:GSF_DB_NAME,Env:GSF_DB_USER,Env:GSF_DB_PASSWORD `
        -ErrorAction SilentlyContinue
    Remove-Item Env:GSF_DB_HOST,Env:GSF_DB_PORT -ErrorAction SilentlyContinue
    $senhaAdmin = $null
    $senhaApp = $null
    $senhaAdminSegura = $null
    $senhaAppSegura = $null
}

if ($resultadoTestes -ne 0) {
    throw "Os testes no PostgreSQL falharam com codigo $resultadoTestes."
}

Write-Host 'Todos os testes passaram no PostgreSQL.' -ForegroundColor Green
