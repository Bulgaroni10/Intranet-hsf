[CmdletBinding()]
param(
    [string]$Servico = 'postgresql-x64-18',
    [string]$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$PgHba = 'C:\Program Files\PostgreSQL\18\data\pg_hba.conf'
)

$ErrorActionPreference = 'Stop'

$identidade = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identidade)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra o PowerShell ou Prompt de Comando como Administrador.'
}

if (-not (Test-Path -LiteralPath $Psql)) {
    throw "psql não encontrado em: $Psql"
}
if (-not (Test-Path -LiteralPath $PgHba)) {
    throw "pg_hba.conf não encontrado em: $PgHba"
}

$pgCtl = Join-Path (Split-Path -Parent $Psql) 'pg_ctl.exe'
$diretorioDados = Split-Path -Parent $PgHba

if (-not (Get-Service -Name $Servico -ErrorAction SilentlyContinue)) {
    & $pgCtl register -N $Servico -D $diretorioDados -S auto `
        -U 'NT AUTHORITY\NetworkService'
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível registrar novamente o serviço $Servico."
    }
}

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

function Reiniciar-PostgreSQL {
    $controle = Get-Service -Name $Servico

    if ($controle.Status -ne 'Stopped') {
        Stop-Service -Name $Servico
        $controle.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }

    try {
        Start-Service -Name $Servico
    }
    catch {
        # O PostgreSQL pode ultrapassar o tempo interno do Service Control
        # Manager e terminar a inicialização logo depois. A validação real é
        # feita abaixo, aguardando explicitamente o estado Running.
    }

    $controle = Get-Service -Name $Servico
    $controle.WaitForStatus('Running', [TimeSpan]::FromSeconds(240))
    $controle.Refresh()
    if ($controle.Status -ne 'Running') {
        throw "O serviço $Servico não voltou ao estado Running."
    }
}

function Aplicar-ConfiguracaoPostgreSQL {
    & $pgCtl reload -D $diretorioDados 2>$null
    if ($LASTEXITCODE -eq 0) {
        Start-Sleep -Seconds 2
        return
    }

    Reiniciar-PostgreSQL
}

$backup = "$PgHba.codex-reset"
$restaurar = $false
$senha = $null
$confirmacao = $null

try {
    Copy-Item -LiteralPath $PgHba -Destination $backup -Force
    $restaurar = $true

    $linhas = Get-Content -LiteralPath $PgHba
    $linhas = $linhas | ForEach-Object {
        if ($_ -match '^\s*host\s+all\s+all\s+(127\.0\.0\.1/32|::1/128)\s+') {
            $_ -replace 'scram-sha-256\s*$', 'trust'
        }
        else {
            $_
        }
    }
    # Windows PowerShell 5 adiciona BOM ao usar `Set-Content -Encoding UTF8`.
    # O PostgreSQL interpreta esses bytes como um tipo de conexão inválido.
    $utf8SemBom = [Text.UTF8Encoding]::new($false)
    [IO.File]::WriteAllLines($PgHba, $linhas, $utf8SemBom)
    Aplicar-ConfiguracaoPostgreSQL

    $senhaSegura = Read-Host 'Defina a nova senha do usuário postgres' -AsSecureString
    $confirmacaoSegura = Read-Host 'Confirme a nova senha do usuário postgres' -AsSecureString
    $senha = Converter-Senha $senhaSegura
    $confirmacao = Converter-Senha $confirmacaoSegura

    if ($senha.Length -lt 16) {
        throw 'A nova senha deve ter pelo menos 16 caracteres.'
    }
    if ($senha -cne $confirmacao) {
        throw 'As senhas não conferem.'
    }

    $senhaSql = $senha.Replace("'", "''")
    "ALTER ROLE postgres WITH PASSWORD '$senhaSql';" |
        & $Psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -U postgres -d postgres |
        Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw 'O PostgreSQL recusou a alteração da senha.'
    }
}
finally {
    if ($restaurar -and (Test-Path -LiteralPath $backup)) {
        Copy-Item -LiteralPath $backup -Destination $PgHba -Force
        Remove-Item -LiteralPath $backup -Force
        Aplicar-ConfiguracaoPostgreSQL
    }
    $senha = $null
    $confirmacao = $null
    $senhaSegura = $null
    $confirmacaoSegura = $null
}

Write-Host 'Senha administrativa redefinida e autenticação segura restaurada.' -ForegroundColor Green
