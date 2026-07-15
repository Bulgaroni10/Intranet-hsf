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

function Executar-Django {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Argumentos)

    & $Python (Join-Path $Projeto 'manage.py') @Argumentos
    if ($LASTEXITCODE -ne 0) {
        throw "Comando Django falhou: $($Argumentos -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python não encontrado: $Python"
}
if (-not (Test-Path -LiteralPath $Psql)) {
    throw "psql não encontrado: $Psql"
}

$senhaSegura = Read-Host 'Senha do usuário gsf_hub_app' -AsSecureString
$senha = $null
$pasta = Join-Path $Projeto 'migration_rehearsal'
$dump = Join-Path $pasta 'dados-gsf.json'
$auditoriaSqlite = Join-Path $pasta 'contagens-sqlite.json'
$auditoriaPostgres = Join-Path $pasta 'contagens-postgres.json'
$backupSqlite = Join-Path $pasta 'db.sqlite3.copia'
$exclusoes = @(
    'contenttypes.contenttype',
    'auth.permission',
    'admin.logentry',
    'sessions.session'
)

try {
    $senha = Converter-Senha $senhaSegura
    if ([string]::IsNullOrWhiteSpace($senha)) {
        throw 'A senha não pode ficar vazia.'
    }

    New-Item -ItemType Directory -Path $pasta -Force | Out-Null
    Remove-Item -LiteralPath $dump,$auditoriaSqlite,$auditoriaPostgres `
        -Force -ErrorAction SilentlyContinue
    Copy-Item -LiteralPath (Join-Path $Projeto 'db.sqlite3') `
        -Destination $backupSqlite -Force

    # Evita que o Python no Windows use cp1252/charmap ao serializar emojis e
    # outros caracteres Unicode existentes nos dados da intranet.
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:GSF_DEBUG = 'false'
    $env:GSF_SECRET_KEY = 'ensaio-local-postgresql-nao-utilizar-em-producao-123456789'
    $env:GSF_DB_ENGINE = 'sqlite'

    $argumentosAuditoria = @('auditar_migracao_banco', '--json', '--output', $auditoriaSqlite)
    foreach ($modelo in $exclusoes) {
        $argumentosAuditoria += @('--exclude', $modelo)
    }
    Executar-Django @argumentosAuditoria

    Executar-Django dumpdata --natural-foreign --natural-primary `
        --exclude contenttypes --exclude auth.permission `
        --exclude admin.logentry --exclude sessions `
        --indent 2 --output $dump

    $env:GSF_DB_ENGINE = 'postgresql'
    $env:GSF_DB_NAME = $Banco
    $env:GSF_DB_USER = $Usuario
    $env:GSF_DB_PASSWORD = $senha
    $env:GSF_DB_HOST = $Servidor
    $env:GSF_DB_PORT = [string]$Porta
    $env:PGPASSWORD = $senha

    $tabelaMigracoes = & $Psql -X -w -tA -h $Servidor -p $Porta `
        -U $Usuario -d $Banco -c "SELECT to_regclass('public.django_migrations');"
    if ($LASTEXITCODE -ne 0) {
        throw 'Não foi possível conectar ao PostgreSQL de homologação.'
    }
    if (-not [string]::IsNullOrWhiteSpace(($tabelaMigracoes -join ''))) {
        throw 'O banco de homologação já contém tabelas. Recrie-o antes de repetir o ensaio.'
    }

    Executar-Django migrate --noinput
    Executar-Django loaddata $dump

    $argumentosAuditoria = @('auditar_migracao_banco', '--json', '--output', $auditoriaPostgres)
    foreach ($modelo in $exclusoes) {
        $argumentosAuditoria += @('--exclude', $modelo)
    }
    Executar-Django @argumentosAuditoria
    Executar-Django check

    $origem = Get-Content -LiteralPath $auditoriaSqlite -Raw | ConvertFrom-Json
    $destino = Get-Content -LiteralPath $auditoriaPostgres -Raw | ConvertFrom-Json
    $diferencas = @()
    foreach ($propriedade in $origem.PSObject.Properties) {
        $quantidadeDestino = $destino.($propriedade.Name)
        if ($propriedade.Value -ne $quantidadeDestino) {
            $diferencas += "$($propriedade.Name): SQLite=$($propriedade.Value), PostgreSQL=$quantidadeDestino"
        }
    }

    if ($diferencas.Count -gt 0) {
        Write-Host 'Diferenças encontradas:' -ForegroundColor Red
        $diferencas | ForEach-Object { Write-Host $_ }
        throw 'As contagens não conferem.'
    }

    Write-Host ''
    Write-Host 'Ensaio concluído: todas as contagens conferem.' -ForegroundColor Green
    Write-Host "Artefatos: $pasta"
}
finally {
    Remove-Item Env:GSF_DEBUG,Env:GSF_SECRET_KEY,Env:GSF_DB_ENGINE `
        -ErrorAction SilentlyContinue
    Remove-Item Env:GSF_DB_NAME,Env:GSF_DB_USER,Env:GSF_DB_PASSWORD `
        -ErrorAction SilentlyContinue
    Remove-Item Env:GSF_DB_HOST,Env:GSF_DB_PORT,Env:PGPASSWORD `
        -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONUTF8,Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    $senha = $null
    $senhaSegura = $null
}
