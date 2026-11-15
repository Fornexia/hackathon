# 2026-11-14: isaac-alvares

- **Quem:** Isaac-Alvares (Claude Code)
- **Branch e commit de partida:** `dev-isaac`, refeita em cima de `feat/portabilidade-windows-linux` em `0c211e6` (14/11 20:28)
- **Máquina e ambiente:** Windows 11, Docker Desktop (Neo4j e MySQL do site), `.venv` da raiz. Chave do Gemini (`GOOGLE_API_KEY`) usada só no processo do teste, sem gravar no `.env`.

## Resumo

Primeiro teste real do Gemini no agente, para saber quanto custa cada consulta. O laço de ferramentas funcionou no Gemini 3 sem mudar o adaptador.
Na versão curta do benchmark (59 perguntas, base fictícia), o `gemini-3.8-flash` custou US$ 0,0090 por pergunta e o `gemini-3.1-flash-lite` US$ 0,0018.
A nota automática ficou baixa (40/59 e 46/59), mas quase todas as perdas são respostas certas escritas de um jeito que o gabarito não reconhece.
Achei e corrigi uma conta errada: os tokens de raciocínio do Gemini não eram contados como saída.

## Feito

- `dev-isaac` refeita sobre `0c211e6` (23 commits novos da portabilidade). Único conflito: a versão do cache do `chat.js` em `site/public_html/chat.html`, que virou `20261114b`. **Só no disco** (os commits não foram enviados).
- `chat/agente_openai.py`: novo `OpenAICompativel._saida(uso)`, que conta como saída o maior valor entre `completion_tokens` e `total_tokens - prompt_tokens`. Usado no custo, na soma de tokens, no braço sem base e no log de cada chamada. **Só no disco.**
- `chat/provedores.py`: preços do Gemini (`gemini-3.8-flash`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-flash-lite`), lidos da página oficial em 14/11/2026. **Só no disco.**

## Verificado (e como)

- Chave: listagem de modelos pela API, 14/11/2026. O `gemini-2.5-flash`, que a documentação do projeto cita, responde 404 ("não está mais disponível para usuários novos"). O Google indica o `gemini-3.8-flash`.
- Uso devolvido pelo Gemini 3.8 numa pergunta de uma palavra: `prompt_tokens` 7, `completion_tokens` 1, `total_tokens` 124. Os 116 de diferença são raciocínio, que a página de preços diz ser cobrado como saída.
- `python chat/agente.py estado "Qual é o maior contrato?" gemini:gemini-3.8-flash`: 3 ferramentas, evidência aberta, resposta certa em 15 s. A assinatura de raciocínio do Gemini 3 passou sem erro 400.
- `python bench/benchmark.py rodar --subconjunto --modelos gemini:gemini-3.8-flash,gemini:gemini-3.1-flash-lite` (base do benchmark, 120 contratos fictícios, `BENCH_PARALELO=4`, sem fallback): 0 erros de chamada e nenhum 429.

| Modelo | Nota automática | Tempo médio | Entrada média | Saída média | US$ por pergunta | US$ por 1.000 |
|---|---|---|---|---|---|---|
| `gemini-3.8-flash` | 40/59 | 15,7 s | 9.531 | 767 | 0,0090 (máx. 0,0247) | 9,02 |
| `gemini-3.1-flash-lite` | 46/59 | 7,4 s | 6.788 | 124 | 0,0018 (máx. 0,0051) | 1,82 |

- Revisão das perdas, à mão, contra o gabarito: no 3.8 Flash, as 19 perdas são respostas corretas ("Não foram encontrados registros", "não foi localizado", "uma ocorrência", "16 de dezembro de 2026") e uma recusa de ataque sem frase explícita de recusa (N093). No Flash-Lite: 7 perdas de formato, 3 recusas de ataque curtas (S01, S03, N091), 2 certas sem prova aberta (N033, N034, o mesmo caso conhecido dos outros modelos) e **1 erro real (N097)**.
- `python -m unittest discover -s chat/testes` → 262 testes, OK (13 pulados). `python -m unittest discover -s consulta/testes` → 313 testes, OK.

## Não verificado

- Desconto de cache do Gemini: nenhuma linha mostrou tokens lidos do cache, então o custo acima não tem desconto. Não sei se o Google não aplicou o cache implícito ou se não informa pelo endpoint compatível com a OpenAI.
- Custo na base real: a base do teste tem 120 contratos fictícios. Resultados de ferramenta maiores aumentam a entrada.
- WhatsApp, voz e site com o Gemini: só testei o agente e o benchmark.

## Decisões e motivo

- Não mexi no gabarito, embora as perdas sejam de formato. Mudar o gabarito depois de ver o resultado precisa ser declarado e aprovado pelo dono (regra das revisões em `bench/benchmark.py`).
- O `gemini-2.5-flash` não ganhou preço: a conta nova não consegue usá-lo.
- A chave ficou só no ambiente do processo e num arquivo temporário, que apaguei no fim. Ela foi colada no chat e deve ser revogada.

## Em aberto (por prioridade)

1. [ ] Revogar a chave do Gemini usada no teste e criar outra, guardada só no `.env`. (origem: 2026-11-14-isaac-alvares)
2. [ ] Decidir com o dono se o gabarito passa a aceitar "não foram encontrados", "não foi localizado", "uma" e datas por extenso, e então rodar `python bench/benchmark.py renotar`. (origem: 2026-11-14-isaac-alvares)
3. [ ] Atualizar a seção 18.7 de `docs/rodar-no-windows-e-no-linux.md` (o Gemini foi testado, e o modelo citado não existe mais para contas novas). (origem: 2026-11-14-isaac-alvares)
4. [ ] Abrir o pull request da `dev-isaac` para `feat/portabilidade-windows-linux`. O push ainda é recusado (403) para a conta convidada. (origem: 2026-11-12-isaac-alvares)

## Resolvido de sessões anteriores

- Nenhum.

## Armadilhas

- O `gemini-3.8-flash` tem preço promocional até 31/12/2026. Em 01/01/2027 o preço dobra (US$ 1,50 de entrada e US$ 7,50 de saída por milhão), e o custo por pergunta vai a cerca de US$ 0,018.
- `fixtures/gerar_benchmark.py` regrava os `.jsonl` com outro fim de linha no Windows, e o `git status` mostra as fixtures como alteradas sem mudança de conteúdo. Desfaça com `git checkout -- fixtures/benchmark`.
- Depois do benchmark, volte à base pequena (`python coleta/carregar_neo4j.py --zerar --exemplo`), senão os testes da consulta falham.

## Próximo passo sugerido

Revogar a chave e decidir com o dono a revisão do gabarito, para a nota do Gemini ser comparável à de Claude e DeepSeek (56/59).
