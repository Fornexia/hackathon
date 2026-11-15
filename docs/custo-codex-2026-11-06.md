# Custo do Codex no FornexIA — medição de 06/11/2026

Rodada: `dados/bench/codex-20261106-100-r5`. Modelo `gpt-6.1-sol`, raciocínio `medium`, autenticação ChatGPT `pro`, cliente `codex-cli 0.164.0-alpha.11.1`.

Foram executadas 100 perguntas únicas, em sessões independentes, com até 3 em paralelo e acesso somente às oito consultas MCP do projeto. O site e o worker de produção não foram trocados para Codex.

| Medida | Resultado |
|---|---|
| Perguntas respondidas | 100/100 |
| Perguntas com resposta e chamada MCP concluída | 99/100 |
| Janela efetivamente informada pela conta | 10080 minutos (7 dias) |
| Consumo antes → depois | 13% → 14% |
| Variação visível | 1 ponto(s) percentual(is) |
| Tempo total da rodada | 652.2 segundos (10.87 minutos) |
| Latência média / mediana por pergunta | 19.09 s / 18.76 s |
| Perguntas em 5h, extrapoladas pela vazão com 3 simultâneas | 2760 |
| Conferências de evidência / hashes válidos | 163 / 163 |

A pergunta 100, sobre CPF, foi recusada conforme a regra de proteção de dados, sem chamar uma ferramenta. Houve uma falha em buscar_fornecedor na pergunta 6; a sessão terminou com resposta baseada na consulta de cobertura. Não foi feita uma auditoria factual integral.

## O que significa a janela de 5 horas

A conta medida não retornou uma janela de 300 minutos: retornou uma janela semanal, sem janela secundária. Não existe base medida para dizer quantas perguntas consomem 1% de uma franquia de 5h desta conta. A documentação atual também informa que planos Pro não têm limite de cinco horas. A projeção acima de perguntas em 5h mede velocidade de processamento e não garante franquia disponível.

## Conversão do consumo em capacidade

Estimativa central: 100 / 1 = **100 perguntas por ponto percentual da janela medida**. Isso projeta **10000 perguntas por 7 dias**, ou **42857 por mês de 30 dias**.

Distribuindo a cota uniformemente pelo tempo, seriam **298 perguntas a cada 5h em média**. Isso não cria nem representa uma franquia de 5h.

Com plena utilização dessa capacidade, o rateio do Codex seria **R$ 0,0120 por pergunta**, e Codex + VPS seria **R$ 0,0166 por pergunta**.

O painel tem resolução de 1 ponto percentual. A diferença real pode estar aproximadamente entre max(0, 1-1) e 1+1 pontos; não trate a estimativa central como capacidade contratual.

## Custo conforme o volume utilizado

Premissas herdadas do pitch: Codex = R$ 515/mês e VPS = R$ 197/mês. O tipo de plano retornado pela conta não revela o valor pago. Estes valores não foram confirmados em fatura. O custo unitário é rateio da assinatura; não é cobrança adicional por chamada.

| Perguntas/mês | Só Codex | Codex + VPS |
|---:|---:|---:|
| 1000 | R$ 0,5150 | R$ 0,7120 |
| 5000 | R$ 0,1030 | R$ 0,1424 |
| 13200 | R$ 0,0390 | R$ 0,0539 |

Fórmulas: perguntas por ponto = N / Δp; capacidade da janela = 100 × N / Δp; capacidade mensal = capacidade da janela × 30 / dias da janela; rateio unitário = custo mensal / perguntas efetivamente atendidas no mês. O cálculo de 5h por vazão usa N × 18.000 / tempo total em segundos.

## Limites da medição

- O limite é compartilhado com outros usos da conta. A variação antes/depois não isola eventuais sessões externas. Esta conversa também pode contribuir para o consumo compartilhado.
- Percentual inteiro e eventual atraso de atualização limitam a precisão. Os snapshots completos e as notificações de limite estão preservados junto aos resultados.
- Capacidade extrapolada depende de modelo, raciocínio, contexto, cache, ferramentas e distribuição das perguntas. Foram usados pedidos curtos e sem histórico de conversa.
- Sucesso operacional significa resposta concluída e consulta à base; não equivale a uma auditoria factual integral. Conferências de hash validam a integridade do trecho, não a correção de toda a interpretação.
- Não foram incluídos API oficial do WhatsApp, impostos, suporte ou equipe. As hipóteses mensais supõem disponibilidade e uso da capacidade; o notebook e três consultas simultâneas não validam uma VPS específica.
- Tentativas de configuração anteriores foram descartadas: uma falhou antes de chamar o modelo, uma foi recusada por incompatibilidade do CLI antigo e duas não conseguiram consultar o MCP. O baseline desta rodada foi capturado depois delas.

Fontes: [limites e preços do Codex](https://learn.chatgpt.com/docs/pricing) e [protocolo do App Server](https://learn.chatgpt.com/docs/app-server). Os snapshots observados desta conta prevalecem para a descrição da janela efetivamente medida.

Dados brutos e perguntas reais ficam em `dados/bench/`, ignorados pelo Git. Este relatório não inclui dados pessoais nem credenciais.
