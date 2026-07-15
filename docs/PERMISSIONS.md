# Permissões e isolamento por unidade

## Regra obrigatória

Todo dado operacional vinculado a hospital deve ser consultado pela unidade
ativa do usuário. A regra também vale para superusuários e administradores de
TI. Ter acesso a várias unidades permite selecioná-las, não misturar seus dados.

Use sempre o helper central:

```python
from usuarios.escopo import aplicar_escopo_unidade

itens = aplicar_escopo_unidade(Modelo.objects.all(), request.user)
```

Para modelos cujo campo possui outro nome:

```python
itens = aplicar_escopo_unidade(
    Modelo.objects.all(), request.user, campo='empresa',
)
```

Registros globais ou compartilhados precisam ser autorizados explicitamente:

```python
itens = aplicar_escopo_unidade(
    Documento.objects.all(),
    request.user,
    incluir_globais=True,
    campos_compartilhados=('unidades_compartilhadas',),
)
```

O mesmo queryset restrito deve ser usado em `get_object_or_404`. Nunca busque o
objeto por ID antes de aplicar o escopo.

## Testes mínimos de uma nova funcionalidade

Cada módulo com dados por unidade precisa demonstrar que:

1. a Unidade A visualiza seus registros;
2. a Unidade A não lista registros da Unidade B;
3. uma URL direta para o ID da Unidade B retorna HTTP 404;
4. um superusuário continua limitado à unidade ativa;
5. registros globais aparecem somente quando a regra do módulo os permite.
