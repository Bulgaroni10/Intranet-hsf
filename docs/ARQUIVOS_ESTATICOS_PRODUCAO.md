# Arquivos estáticos em produção

No servidor, não execute `manage.py collectstatic` diretamente. O shell não herda as variáveis configuradas no serviço NSSM e o Django pode assumir `DEBUG=True`, deixando de gerar o manifesto usado pelo WhiteNoise.

Use sempre:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\Projetos\intranet_gsf\scripts\coletar_estaticos_producao.ps1
```

O script força `DEBUG=False` apenas durante a coleta, reconstrói os arquivos e valida as entradas obrigatórias `home.css` e `noc.css`. As variáveis do PowerShell são restauradas ao final.
