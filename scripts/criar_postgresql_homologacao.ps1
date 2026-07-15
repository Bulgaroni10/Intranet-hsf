[CmdletBinding()]
param(
    [string]$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$Servidor = '127.0.0.1',
    [int]$Porta = 5432,
    [string]$Banco = 'gsf_hub_homologacao',
    [string]$Usuario = 'gsf_hub_app',
    [switch]$Recriar
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Psql)) {
    throw "psql não encontrado em: $Psql"
}

if ($Banco -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$') {
    throw 'Nome de banco inválido.'
}

if ($Usuario -notmatch '^[a-zA-Z_][a-zA-Z0-9_]*$') {
    throw 'Nome de usuário inválido.'
}
if ($Recriar -and $Banco -notmatch 'homolog') {
    throw 'A recriação é permitida somente para bancos de homologação.'
}

function Converter-Senha {
    param([Security.SecureString]$Senha)

    $ponteLocal = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Senha)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ponteLocal)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ponteLocal)
    }
}

$senhaAdminSegura = Read-Host 'Senha do usuário postgres' -AsSecureString
$senhaAppSegura = Read-Host 'Defina a senha do usuário gsf_hub_app' -AsSecureString
$senhaAppConfirmacao = Read-Host 'Confirme a senha do usuário gsf_hub_app' -AsSecureString

$senhaAdmin = $null
$senhaApp = $null
$senhaConfirmacao = $null

try {
    $senhaAdmin = Converter-Senha $senhaAdminSegura
    $senhaApp = Converter-Senha $senhaAppSegura
    $senhaConfirmacao = Converter-Senha $senhaAppConfirmacao

    if ([string]::IsNullOrWhiteSpace($senhaAdmin)) {
        throw 'A senha administrativa não pode ficar vazia.'
    }

    if ($senhaApp.Length -lt 16) {
        throw 'A senha da aplicação deve ter pelo menos 16 caracteres.'
    }

    if ($senhaApp -cne $senhaConfirmacao) {
        throw 'As senhas da aplicação não conferem.'
    }

    $env:PGPASSWORD = $senhaAdmin

    & $Psql -X -w -v ON_ERROR_STOP=1 -h $Servidor -p $Porta -U postgres -d postgres `
        -c 'SELECT current_database(), current_user;' | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'Não foi possível autenticar no PostgreSQL.'
    }

    $senhaSql = $senhaApp.Replace("'", "''")
    $sqlUsuario = @"
DO `$gsf`$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$Usuario') THEN
        CREATE ROLE $Usuario LOGIN PASSWORD '$senhaSql';
    ELSE
        ALTER ROLE $Usuario WITH LOGIN PASSWORD '$senhaSql';
    END IF;
END
`$gsf`$;
"@

    $sqlUsuario | & $Psql -X -w -v ON_ERROR_STOP=1 -h $Servidor -p $Porta `
        -U postgres -d postgres | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao criar ou atualizar o usuário da aplicação.'
    }

    $bancoExiste = & $Psql -X -w -tA -h $Servidor -p $Porta -U postgres `
        -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$Banco';"
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao consultar o banco de homologação.'
    }

    if ($Recriar -and ($bancoExiste -contains '1')) {
        $dropdb = Join-Path (Split-Path -Parent $Psql) 'dropdb.exe'
        & $dropdb -w --force -h $Servidor -p $Porta -U postgres $Banco
        if ($LASTEXITCODE -ne 0) {
            throw 'Falha ao remover o banco parcial de homologação.'
        }
        $bancoExiste = @()
    }

    if (-not ($bancoExiste -contains '1')) {
        $createdb = Join-Path (Split-Path -Parent $Psql) 'createdb.exe'
        & $createdb -w -h $Servidor -p $Porta -U postgres -O $Usuario $Banco
        if ($LASTEXITCODE -ne 0) {
            throw 'Falha ao criar o banco de homologação.'
        }
    }

    & $Psql -X -w -v ON_ERROR_STOP=1 -h $Servidor -p $Porta -U postgres `
        -d postgres -c "ALTER DATABASE $Banco OWNER TO $Usuario;" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao definir o proprietário do banco.'
    }

    Write-Host ''
    Write-Host 'PostgreSQL de homologação preparado com sucesso.' -ForegroundColor Green
    Write-Host "Banco: $Banco"
    Write-Host "Usuário: $Usuario"
    Write-Host "Servidor: ${Servidor}:$Porta"
    Write-Host 'A senha não foi salva. Use a mesma senha no próximo ensaio.'
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    $senhaAdmin = $null
    $senhaApp = $null
    $senhaConfirmacao = $null
    $senhaAdminSegura = $null
    $senhaAppSegura = $null
    $senhaAppConfirmacao = $null
}
