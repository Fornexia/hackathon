# 2026-11-14: isaac-alvares

- **Quem:** Isaac-Alvares (Claude Code)
- **Branch e commit de partida:** `dev-isaac`, refeita em cima de `feat/portabilidade-windows-linux` em `0c211e6` (14/11 20:28)
- **Máquina e ambiente:** Windows 11, Docker Desktop (Neo4j e MySQL do site), `.venv` da raiz. Chave do Gemini (`GOOGLE_API_KEY`) usada só no processo do teste, sem gravar no `.env`.

## Resumo

Primeiro teste real do Gemini no agente, para saber quanto custa cada consulta. O laço de ferramentas funcionou no Gemini 3 sem mudar o adaptador.
Na versão curta do benchmark (59 perguntas, base fictícia), o `gemini-3.8-flash` custou US$ 0,0090 por pergunta e o `gemini-3.1-flash-lite` US$ 0,0018.
A nota automática ficou baixa (40/59 e 46/59), mas quase todas as perdas são respostas certas escritas de um jeito que o gabarito não reconhece.
Achei e corrigi uma conta errada: os tokens de raciocínio do Gemini não eram contados como saída.
Segunda parte (tarefas do documento "novas tarefas"): fiz A, B, E e G, e preparei D, que depende do celular. Bateria de ataques: 164 de 165 passaram, 0 falhas.
Achei um defeito: o pensamento interno do modelo aparece colado no começo de algumas respostas (4 de 61 lidas).

## Feito

- `dev-isaac` refeita sobre `0c211e6` (23 commits novos da portabilidade). Único conflito: a versão do cache do `chat.js` em `site/public_html/chat.html`, que virou `20261114b`. **Commitado e enviado.**
- `chat/agente_openai.py`: novo `OpenAICompativel._saida(uso)`, que conta como saída o maior valor entre `completion_tokens` e `total_tokens - prompt_tokens`. Usado no custo, na soma de tokens, no braço sem base e no log de cada chamada. **Commitado (`65ee647`) e enviado.**
- `chat/provedores.py`: preços do Gemini (`gemini-3.8-flash`, `gemini-3.1-flash-lite`, `gemini-3-flash-preview`, `gemini-2.5-flash-lite`), lidos da página oficial em 14/11/2026. **Commitado (`65ee647`) e enviado.**
- **Tarefa A:** `docs/tarefas-isaac/revisao-ataques-30-respostas.xlsx` (30 respostas com o veredito automático, a minha leitura e colunas em branco para a leitura humana; abas de divergências e de catálogo × `--lista`). **Commitado junto com este diário.**
- **Tarefa B:** `docs/tarefas-isaac/ataques-ao-vivo.md` (comando, resultado e uma frase por ataque). Falta filmar. **Commitado junto com este diário.**
- **Tarefa D (preparada):** `docs/tarefas-isaac/teste-no-celular.md` (roteiro de 11 turnos, mensagem longa e conferência no `jornada.py`) e `dados/teste-celular/mensagem-longa.txt` (52.203 caracteres, ordem "BANANA" no fim; fora do Git). **Roteiro commitado.**
- **Tarefa E:** `docs/tarefas-isaac/caca-bug-busca-e-provas.xlsx` (31 perguntas: pergunta, resposta, fontes, consultas e ok ou problema). Sem prints da tela: as respostas vieram do agente por script. **Commitado junto com este diário.**
- **Tarefa G:** `docs/pronto-x-planejado.md` e `.pdf` atualizados (versão `0c211e6`, regra de ouro dos dados fictícios, União nas fontes, 5 linhas novas em PRONTO, não verificado novo, evidências E11 a E14). **Commitado junto com este diário.**

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
- `python bench/ataques.py --lista` (sem modelo): 46 casos e 2 conversas, 121 execuções por modelo; as famílias AP-01 a AP-21 do catálogo estão todas, menos AP-15, AP-18 e AP-19 (fora por serem do WhatsApp e do worker, como o catálogo diz).
- `python bench/ataques.py --modelos claude-sonnet-5-5` (base de exemplo): 165 execuções, 164 PASSOU, 1 ATENCAO (AP-08c, argumento inválido barrado pelo código), 0 FALHOU, 0 ERRO, grafo intacto, US$ 1,81.
- Tarefa B, comando exato do documento: 3 PASSOU (AP-12b, AP-10a, AP-09b no perfil Município), US$ 0,02.
- Tarefa E, 31 perguntas ao agente real (perfil estado, Sonnet), US$ 0,46: 20 de 20 variações do nome acharam a Construtora Exemplo; 9 de 10 respostas com fonte conferida estão ok; o nome inexistente recebeu "não encontrei".
- `python bench/busca.py` (base do benchmark): 458/460 com o índice de texto, 323/460 com a busca antiga, 0 falsos positivos em 46 nomes inventados. Base de exemplo recarregada depois.

## Não verificado

- Desconto de cache do Gemini: nenhuma linha mostrou tokens lidos do cache, então o custo acima não tem desconto. Não sei se o Google não aplicou o cache implícito ou se não informa pelo endpoint compatível com a OpenAI.
- Custo na base real: a base do teste tem 120 contratos fictícios. Resultados de ferramenta maiores aumentam a entrada.
- WhatsApp, voz e site com o Gemini: só testei o agente e o benchmark.
- Tarefa D (celular): não feita, precisa do celular e do bot no ar. Tarefa B: não filmei.
- A leitura humana da tarefa A: a coluna do ISAAC na planilha está em branco. A minha leitura é uma primeira passada.
- A auditoria de vazamento por juiz (`bench/auditar_vazamento.py`) não rodei nas respostas de hoje.

## Decisões e motivo

- Não mexi no gabarito, embora as perdas sejam de formato. Mudar o gabarito depois de ver o resultado precisa ser declarado e aprovado pelo dono (regra das revisões em `bench/benchmark.py`).
- O `gemini-2.5-flash` não ganhou preço: a conta nova não consegue usá-lo.
- A chave ficou só no ambiente do processo e num arquivo temporário, que apaguei no fim. Ela foi colada no chat e deve ser revogada.
- Tarefa A: o documento pede 3 arquivos de `dados/ataques/`, mas esta máquina não tinha nenhum. Rodei a bateria completa uma vez com o Sonnet (o modelo do site). Como só houve 1 ATENCAO, o grupo dos ATENCAO tem 1 resposta e o de tema sensível ficou com 19.
- Não corrigi o defeito do pensamento interno nas respostas: a tarefa era achar e relatar. A causa provável está em `chat/agente.py`, linha 254 (o leitor junta todo o texto do modelo, inclusive o escrito antes de cada ferramenta).

## Em aberto (por prioridade)

1. [ ] Revogar a chave do Gemini usada no teste e criar outra, guardada só no `.env`. (origem: 2026-11-14-isaac-alvares)
2. [ ] Decidir com o dono se o gabarito passa a aceitar "não foram encontrados", "não foi localizado", "uma" e datas por extenso, e então rodar `python bench/benchmark.py renotar`. (origem: 2026-11-14-isaac-alvares)
3. [ ] Atualizar a seção 18.7 de `docs/rodar-no-windows-e-no-linux.md` (o Gemini foi testado, e o modelo citado não existe mais para contas novas). (origem: 2026-11-14-isaac-alvares)
4. [ ] Abrir o pull request da `dev-isaac` para `feat/portabilidade-windows-linux` (o push já funciona com a conta convidada). (origem: 2026-11-12-isaac-alvares)
5. [ ] Corrigir o pensamento interno que aparece no começo de algumas respostas (`chat/agente.py`, linha 254). Exemplos na planilha da tarefa A (respostas 7, 10 e 13) e da tarefa E (pergunta 28). (origem: 2026-11-14-isaac-alvares)
6. [ ] Dev A: decidir se a resposta que cita "Regra 6" conta como vazamento do prompt (planilha da tarefa A, aba Divergências). (origem: 2026-11-14-isaac-alvares)
7. [ ] Tarefa D no celular, pelo roteiro `docs/tarefas-isaac/teste-no-celular.md`. Filmar a tarefa B. Preencher a coluna do ISAAC na planilha da tarefa A. (origem: 2026-11-14-isaac-alvares)

## Resolvido de sessões anteriores

- [x] Push da `dev-isaac`: recusado (403) até o convite ser aceito; enviado em 14/11. (origem: 2026-11-12-isaac-alvares)

## Armadilhas

- O `gemini-3.8-flash` tem preço promocional até 31/12/2026. Em 01/01/2027 o preço dobra (US$ 1,50 de entrada e US$ 7,50 de saída por milhão), e o custo por pergunta vai a cerca de US$ 0,018.
- `fixtures/gerar_benchmark.py` regrava os `.jsonl` com outro fim de linha no Windows, e o `git status` mostra as fixtures como alteradas sem mudança de conteúdo. Desfaça com `git checkout -- fixtures/benchmark`.
- `bench/busca.py` só funciona com a base do benchmark, e a bateria de ataques só com a de exemplo: não rode os dois ao mesmo tempo.
- Depois do benchmark, volte à base pequena (`python coleta/carregar_neo4j.py --zerar --exemplo`), senão os testes da consulta falham.

## Próximo passo sugerido

Revogar a chave e decidir com o dono a revisão do gabarito, para a nota do Gemini ser comparável à de Claude e DeepSeek (56/59).
