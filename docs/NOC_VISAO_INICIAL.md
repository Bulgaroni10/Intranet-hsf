# NOC — visão inicial

Status: planejado, ainda não iniciar implementação.

## Objetivo

Criar uma tela operacional de leitura rápida para a TI acompanhar saúde e capacidade da infraestrutura hospitalar, adequada para exibição contínua em monitor/TV.

## Layout de referência

- coluna esquerda: computadores e status online/offline;
- painel superior principal: impressoras monitoradas, nível de toner, alertas e equipamentos offline;
- painel intermediário: Active Directory e serviços de infraestrutura;
- painel inferior: consumo de recursos, capacidade e tendências;
- tema escuro GSF, alto contraste, atualização automática e modo tela cheia.

## Princípios

- exibir somente dados reais, com horário da última coleta;
- nunca apresentar status fictício quando a fonte estiver indisponível;
- separar offline de agente/coleta atrasada;
- alertas devem indicar unidade, criticidade e duração;
- acesso restrito à TI e administradores;
- nenhuma credencial, IP sensível ou dado pessoal em tela pública;
- manter histórico suficiente para distinguir incidente de oscilação.

## Dependências a validar antes da implementação

- origem e frequência da telemetria de impressoras;
- disponibilidade de nível de toner via SNMP, agente ou servidor de impressão;
- métricas autorizadas do Active Directory;
- quais recursos entram no painel inferior: servidor, armazenamento, rede ou serviços;
- unidades incluídas e possibilidade de alternar visão por unidade;
- intervalo de atualização e retenção do histórico.

## Sequência futura sugerida

1. NOC 1.0: computadores e disponibilidade dos sistemas existentes.
2. NOC 1.1: impressoras, toner e offline.
3. NOC 1.2: AD e serviços de infraestrutura.
4. NOC 1.3: capacidade, tendências e alertas persistentes.

O desenho fornecido pelo responsável do produto é a referência inicial de distribuição visual; o detalhamento das fontes deve ocorrer antes da criação de models ou coletores.
