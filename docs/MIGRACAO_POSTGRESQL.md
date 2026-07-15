# Migração segura de SQLite para PostgreSQL

## Estado atual

- O serviço continua usando SQLite enquanto `GSF_DB_ENGINE=sqlite`.
- A sincronização MV permanece desativada.
- PostgreSQL só será ativado depois de um ensaio completo e comparação de dados.

## Pré-requisitos

1. PostgreSQL instalado e em execução.
2. Banco e usuário exclusivos para a GSF Hub.
3. `psycopg[binary]` instalado pelo `requirements.txt`.
4. Backup do SQLite e da pasta `media`.
5. Janela de manutenção para a troca final.

## Ensaio isolado

Não altere o ambiente do serviço NSSM nesta etapa.

Crie ou atualize o banco de homologação. As duas senhas são solicitadas de
forma oculta e não são salvas pelo script:

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File scripts\criar_postgresql_homologacao.ps1
```

Para descartar exclusivamente um ensaio parcial e recriar o banco de
homologação, acrescente `-Recriar`. Esse parâmetro recusa bancos cujo nome não
contenha `homolog`.

1. Pare gravações agendadas e faça uma cópia consistente do SQLite.
2. Registre as contagens originais:

```powershell
python manage.py auditar_migracao_banco --json --output contagens-sqlite.json
python manage.py dumpdata --natural-foreign --natural-primary `
  --exclude contenttypes --exclude auth.permission `
  --exclude admin.logentry --exclude sessions `
  --indent 2 --output dados-gsf.json
```

3. Em uma sessão PowerShell separada, configure temporariamente PostgreSQL:

```powershell
$env:GSF_DB_ENGINE='postgresql'
$env:GSF_DB_NAME='gsf_hub_homologacao'
$env:GSF_DB_USER='gsf_hub_app'
$env:GSF_DB_PASSWORD='<informar de forma segura>'
$env:GSF_DB_HOST='127.0.0.1'
$env:GSF_DB_PORT='5432'
```

4. Crie a estrutura e importe:

```powershell
python manage.py migrate --noinput
python manage.py loaddata dados-gsf.json
python manage.py auditar_migracao_banco --json --output contagens-postgres.json
python manage.py check
python manage.py test --noinput
```

5. Compare as contagens e homologue login, troca de unidade, chamados,
documentos, anexos, NOC e inventário.

O ensaio completo também pode ser executado pelo script abaixo. Ele solicita
somente a senha de `gsf_hub_app` e não altera o ambiente do NSSM:

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File scripts\ensaiar_migracao_postgresql.ps1
```

Depois de importar e comparar os dados, execute a suíte no PostgreSQL. O script
concede `CREATEDB` ao usuário da aplicação apenas durante os testes e revoga a
permissão no bloco de finalização:

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File scripts\testar_postgresql_homologacao.ps1
```

## Troca de produção

A troca exige serviço parado para impedir novas gravações durante o último
`dumpdata`. Somente após validar o ensaio:

1. parar `IntranetGSF` e tarefas que escrevem no banco;
2. fazer backup final de `db.sqlite3` e `media`;
3. gerar e importar a carga final no banco PostgreSQL vazio;
4. configurar as variáveis `GSF_DB_*` no NSSM;
5. iniciar o serviço e validar `/health/`;
6. manter o SQLite original intacto durante o período de rollback.

## Rollback

Se a homologação final falhar:

1. pare o serviço;
2. restaure `GSF_DB_ENGINE=sqlite` no NSSM;
3. confirme que o `db.sqlite3` original permanece no projeto;
4. inicie o serviço e valide `/health/`.

Não mantenha os dois bancos recebendo gravações simultaneamente.
