# PRONTO × PLANEJADO: o que o FornexIA faz hoje

**Para:** time de marketing e comercial. **Data:** 12/11/2026, atualizado em 14/11/2026 (tarefa G). **Autor:** Isaac (tarefa da planilha: "Lista do que está pronto contra o que é só planejado").
**Versão do código:** branch `dev-isaac`, em cima de `feat/portabilidade-windows-linux` no commit `0c211e6` (14/11).

**Regra usada:** só está em PRONTO o que tem evidência. Sem evidência, vai para PLANEJADO ou para "não verificado". O folheto e o pitch só devem
prometer o que está na coluna PRONTO.

Cada item pronto cita a evidência entre colchetes, e a etiqueta diz que tipo de prova é:

| Etiqueta | O que significa |
|---|---|
| **rodei 14/11** | Executei em 14/11, na minha máquina (Windows 11) |
| **rodei 12/11** | Executei em 12/11, na minha máquina (Windows 11) |
| **rodei 08/11** | Executei em 08/11 na minha máquina, com o modelo real e dados fictícios, numa versão anterior desta mesma branch |
| **time 12/11, 13/11, 14/11** | O Rodrigo registrou que verificou, no diário daquele dia (`docs/sessoes/2026-11-1X-rodrigo.md`). Eu não repeti |
| **código** | Li o trecho no código, mas não executei |

## A tabela

**Regra de ouro:** toda medida de qualidade (benchmark, ataques, busca) foi feita com **dados fictícios**: a base de exemplo, a base do benchmark
(120 contratos inventados) e todos os números de teste. O marketing não pode dizer que foi medido com dados reais.

| PRONTO (pode dizer) | PLANEJADO (não prometer ainda) |
|---|---|
| **Consulta de fornecedor por nome ou CNPJ.** Perguntar em português, pelo nome ou pelo CNPJ completo, e receber contratos, sanções e pagamentos, cada um com a fonte [E9, rodei 12/11; pagamentos em E1, rodei 08/11] | Tela com o campo "Consultar fornecedor (CNPJ)", como no desenho do folheto. Hoje a consulta é só pelo chat |
| **Fontes de dados.** Coleta de Garanhuns (contratos e licitações) e do Estado de PE (contratos de 2024, cadastro de sanções de 05/06/2025 e execução financeira) [E2, código]. **Da União:** sanções federais (CEIS e CNEP), cadastro de CNPJ da Receita e contratos federais por CNPJ [E2, time 14/11] | Contratos do Estado de 2025 em diante. Pagamento ligado a um contrato. Outros estados e municípios. Contratos do PNCP por fornecedor (a API do PNCP não filtra por fornecedor) |
| **Fonte em cada resposta.** Trecho literal, data da captura, link e conferência do hash do arquivo guardado [E1, rodei 08/11] | Selo de tempo assinado por terceiro ("isso existia nesta data") |
| **Controle de perfil.** O perfil decide quais entes a pessoa consulta, e o modelo não consegue mudar isso [E3, rodei 12/11 e 14/11] | Planos diferentes por região. Hoje existe um plano único, que vê Estado de PE, Garanhuns e a União juntos |
| **Aprovação de WhatsApp pelo administrador.** A conta cadastra até 3 números e o administrador aprova ou bloqueia [E4, rodei 12/11] | Perfil que enxerga dado de pessoa física. Não é oferecido |
| **Histórico do fornecedor.** A resposta junta contratos, sanções e pagamentos do mesmo fornecedor [E1, rodei 08/11] | Tela com o histórico de consultas do usuário. Ao recarregar a página, a conversa some da tela |
| **Memória da conversa.** O assistente lembra das 3 últimas perguntas e entende "esse fornecedor" [E5, rodei 08/11] | Memória mais longa, ou que sobreviva ao reinício do sistema |
| **Registro de consultas.** Cada consulta grava perfil, entes, ferramenta usada e evidências. CPF digitado é mascarado [E6, rodei 12/11] | Tela para o cliente ou o administrador ver a trilha de uso. Hoje os registros são arquivos no notebook |
| **Monitoramento interno.** Logs por peça do sistema, reconstrução de uma pergunta de ponta a ponta e vigia que registra quedas [E7, rodei 12/11] | Aviso automático (e-mail ou WhatsApp) quando uma peça cai |
| **Relatório: pacote de prova.** Botão "Exportar prova" baixa um ZIP com pergunta, resposta, trechos e hashes, que um auditor confere sem acesso ao sistema [E8, rodei 12/11] | Relatório em PDF. Painel gerencial. Alertas "avise-me quando o fornecedor mudar" |
| **Fila de atendimento.** Perguntas entram em fila, com a posição mostrada na tela, e 3 agentes atendem o site [E4, rodei 12/11] | Cache próprio. Hoje só existe o cache do provedor do modelo |
| **Site com contas.** Cadastro, login, chat, página da conta e administração, no ambiente local [E4, rodei 12/11] | Cobrança real, franquia de consultas e preço por excedente. Integração com ERP. API para clientes. Produção na Hostinger com o código novo |
| **Resistência a ataques de prompt.** Bateria automática de 46 ataques e 2 conversas longas contra o agente real, em até 4 perfis: 164 de 165 execuções passaram, 1 pediu atenção (o código barrou um argumento inválido) e nenhuma vazou dado [E11, rodei 14/11] | Ataques pelo canal do WhatsApp e pelo worker (AP-15, AP-18 e AP-19), que não são de prompt e ficam fora da bateria |
| **Auditoria de vazamento por juiz.** Um segundo modelo lê cada resposta dos ataques e diz se ela revela, mesmo por paráfrase, algo fora do perfil [E11, time 13/11] | Rodar a auditoria sempre que o prompt ou as ferramentas mudarem. Hoje é manual |
| **Prova aberta pelo código.** Se o modelo responde sem abrir a evidência, o sistema abre sozinho a evidência dos fatos que a resposta cita [E12, rodei 14/11] | |
| **Busca por texto.** O fornecedor é achado com nome sem acento, com letra errada, em ordem trocada ou pelo nome fantasia: 458 de 460 variações acham o fornecedor certo, contra 323 da busca antiga, e nenhum nome inventado devolve resultado [E13, rodei 14/11] | Busca por sentido ("empresa de limpeza" achar "serviços de conservação"), com embeddings |
| **Porta de qualidade.** Uma versão curta do benchmark (59 perguntas) roda antes de publicar e reprova se a nota cair [E14, rodei 14/11; time 14/11] | Rodar a porta automaticamente a cada mudança (não há CI) |

## Não verificado (não tratar como pronto)

| Item | Por que não está em PRONTO |
|---|---|
| **Busca por CNPJ na base real** | Provada só com os dados fictícios [E9]. Pelo código, fornecedor cujo documento vem mascarado no portal fica sem CNPJ e só é achado pelo nome. Não sei quantos fornecedores da base real estão nessa situação. CNPJ parcial não devolve nada |
| **Tamanho da base real** (100 contratos: 70 do Estado, 30 de Garanhuns) | A base real não está na minha máquina (dados brutos não vão para o Git). O número vem do README e da página inicial do site. É a tarefa da Gabi de 15/11 |
| **WhatsApp com número real** | time 12/11: respondeu a mensagens reais de texto. Eu não testei. Áudio não foi verificado por ninguém |
| **Produção na Hostinger** (domínio, HTTPS e código novo) | O código novo (pacote de prova, registros, `espera_ms`) não foi publicado na hospedagem. O deploy está pendente por falta de acesso ao servidor |
| **WhatsApp Cloud API** (o canal oficial da Meta) | Não existe. O bot usa uma conexão não oficial do WhatsApp Web, no notebook do Rodrigo |
| **Dado pessoal** | O sistema não oferece dado de pessoa física: CPF vira código, e o pacote de prova marca `dados_pessoais: null`. Ninguém avaliou a conformidade com a LGPD |
| **Conversa humana longa no celular** | As 2 conversas longas da bateria são automáticas. Uma conversa de 10 turnos ou mais, feita por uma pessoa no WhatsApp, é a minha tarefa D (15/11) |
| **Busca por sentido** (embeddings) | Não existe. A busca é por texto: acha variações do nome, não sinônimos |
| **Conferência do pacote por um terceiro** | Vi o ZIP e os arquivos dentro dele, e os 33 testes do time passaram. Não rodei à mão o `verificar_prova.py` que vai no pacote, como um auditor faria |

## Folheto × sistema: o que corrigir

| O folheto diz | O que o sistema faz hoje | Sugestão |
|---|---|---|
| "756 contratos analisados", "240 licitações" | São linhas **capturadas** do portal de Garanhuns. No assistente, dá para consultar 30 contratos de Garanhuns e 70 do Estado (amostra) | Dizer "756 contratos capturados; amostra de 100 consultável na demonstração" |
| "Franquia de consultas e cobrança por uso excedente" | Plano único de demonstração, R$ 149 por mês, franquia 0, sem excedente e sem nenhum código de cobrança [E10] | Alinhar com o site: "plano único, valor de demonstração" |
| "Acesso por região" | O mecanismo existe e está testado, mas o único plano oferecido vê tudo | Dizer "controle de acesso por ente, pronto para planos regionais" |
| "Conformidade com LGPD" | Há medidas: pessoa física fora das respostas e CPF mascarado nos registros. Ninguém avaliou a conformidade, e o pacote de prova marca `dados_pessoais: null` | Trocar por "medidas de proteção de dados pessoais" |
| "Com filas, cache e monitoramento" | Fila e monitoramento existem. Cache próprio não existe | Tirar "cache" |
| Tela "Consultar fornecedor (CNPJ)" | Não existe. A consulta é por conversa | Mostrar a tela real do chat |
| "Reduz o tempo de investigação" | Hipótese, ainda sem validação (o próprio site diz isso) | Dizer "hipótese em validação" |
| "Controle de acesso por perfil, com trilhas de uso" | Verdadeiro, mas a trilha é um arquivo interno, sem tela | Não mostrar "trilha" como tela do produto |
| Qualquer número de qualidade (acerto, ataques, busca) | Medido só com dados fictícios | Sempre dizer "em testes com dados fictícios" |
| Prints de respostas para o material | Em 4 de 61 respostas lidas hoje, um pensamento interno do modelo aparece colado no começo ("Vou buscar...", "Regra 6: ...") | Não usar essas respostas como print até o defeito ser corrigido |

## Evidências

**E1. Conversa real com fonte, histórico do fornecedor e pagamento separado do contrato.** 08/11/2026, site local, modelo real, dados fictícios.
Sete perguntas respondidas em 15 a 21 s: 4 direto no agente e 3 pelo site, estas com o botão "Ver fonte". Relato completo: documento "Conversa completa com o modelo real: falhas (08/11/2026)".
Código: `consulta/mcp_transparencia.py`, linhas 297 a 364 (`contratos_do_fornecedor`, `sancoes_do_fornecedor`, `execucao_do_fornecedor`, `conferir_evidencia`).

![Conversa com histórico e fonte](evidencias/2026-11-08/conversa-com-historico-e-fonte.jpg)

![Pagamento separado do contrato](evidencias/2026-11-08/pagamento-separado-do-contrato.jpg)

**E2. Fontes de dados.** `coleta/estado.py` (painéis do Estado de PE: contratos e execução), `coleta/extrair.py` (transforma a captura em fatos com evidência),
`coleta/amostra.py` (separa 100 contratos: 70 do Estado e 30 de Garanhuns), `coleta/carregar_neo4j.py`.
**União (14/11):** `coleta/federal.py` (CEIS e CNEP do Portal da Transparência), `coleta/receita.py` (cadastro de CNPJ pela BrasilAPI) e
`coleta/federal_contratos.py` (contratos federais por CNPJ). O Rodrigo registrou que rodou os três com dado real (`docs/sessoes/2026-11-14-rodrigo.md`).
rodei 14/11: `python -m unittest discover -s consulta/testes` → **313 testes OK**, incluindo `test_federal.py` (sanções da União, com o perfil próprio
`estado-uniao`). O PNCP foi investigado e não entrou: a API não filtra por fornecedor.

**E3. Controle de perfil.** Os entes entram pelo ambiente do servidor de consultas, nunca por argumento: `consulta/mcp_transparencia.py`, linhas 40 e 193 a 197
(toda consulta ao banco recebe `tenants=TENANTS`). Sem perfil exato, a pergunta é recusada: `chat/agente.py`, linhas 97 a 102. Perfis em `consulta/perfis.json`.
rodei 12/11: `python -m unittest discover -s consulta/testes` → **65 testes OK, nenhum pulado** (Neo4j no ar, dados fictícios).
Ao vivo em 12/11, a mesma pergunta ("O CNPJ 11.111.111/0001-11 tem sanções?") com dois perfis: o perfil Estado mostrou a multa do cadastro do Estado; o perfil
Município (`python chat/agente.py municipio "..."`) respondeu que não encontrou sanções e que "entes fora desse perfil não foram consultados". A tela mostra o perfil em uso:

![Chat com o perfil em uso](evidencias/2026-11-08/chat-logado-perfil.jpg)

**E4. Site, fila e administração.** rodei 12/11: `python site/dev/test_api.py` → **82 testes OK** (PHP e MariaDB reais, worker simulado), e uso ao vivo do
`chat.html` com login. Rotas em `site/public_html/api/index.php`, linhas 45 a 65.

**E5. Memória da conversa.** `chat/worker.py`, linha 51: `deque(maxlen=3)`, guardado em memória do processo. Ao vivo em 08/11: "E esse fornecedor…" foi entendido
como a Construtora Exemplo (primeiro print de E1). Ao recarregar a página, o site só busca a pergunta em andamento: `site/public_html/assets/api.js`, linha 50.
Conferido ao vivo em 12/11: depois de recarregar, a conversa anterior não aparece mais.

![A conversa some ao recarregar](evidencias/2026-11-12/conversa-some-ao-recarregar.jpg)

**E6. Registro de consultas.** `consulta/mcp_transparencia.py`, linhas 154 a 166 (uma linha por consulta em `logs/consultas.jsonl`) e linhas 74 a 81 (máscara de CPF).
Ao vivo em 12/11: a pergunta `site:1100` deixou em `logs/consultas.jsonl` uma linha por consulta, com `perfil: estado`, os dois entes, a ferramenta e as evidências
(`e1`, `g1`). `python scripts/jornada.py site:1100` mostrou a pergunta inteira: 6 consultas, modelo `claude-sonnet-5-5`, 28 s, 2 fontes.

**E7. Monitoramento interno.** rodei 12/11: `python -m unittest discover -s chat/testes` → **205 testes OK, 13 pulados** (Windows 11; inclui `test_registro`,
`test_observabilidade`, `test_vigia` e `test_jornada`). Código: `consulta/registro.py`, `chat/vigia.py`, `scripts/jornada.py`. Nenhuma página do site mostra esses
registros: a busca por "log", "trilha" e "auditoria" em `admin.html` e `conta.html` não devolve nada.
rodei 14/11: `python scripts/jornada.py --ultimas` lista o desfecho de cada pergunta (canal, respondeu ou não, tempo, modelo), e cada execução da bateria de
ataques leva um `request_id` próprio, que o `jornada.py` reconstrói.

**E8. Pacote de prova.** `site/public_html/api/lib_prova.php`, linhas 356 a 361 (`rota_prova`, `rota_provas`); rotas em `site/public_html/api/index.php`, linhas 60 e 61;
botão em `site/public_html/assets/chat.js` (`adicionarExportar`). rodei 12/11: `python site/dev/test_prova.py` → **33 testes OK**. Ao vivo em 12/11, o botão
da pergunta `site:1100` devolveu `prova-fornexia-consulta-1100.zip` (11,5 KB) com `prova.json`, `LEIA-ME.txt`, `verificar_prova.py` e 2 arquivos em `trechos/`.
Limites declarados pelo time: o arquivo bruto do portal não vai no pacote e o hash do trecho é
calculado na exportação.

**E9. Busca por CNPJ.** `consulta/mcp_transparencia.py`, linhas 242 a 255: busca por parte do nome **ou** pelo CNPJ exato (só os dígitos).
`coleta/extrair.py`, linhas 172 a 179: fornecedor com documento mascarado e não resolvido fica sem CNPJ (`"cnpj": None`) e só é achado pelo nome.
rodei 12/11, direto na ferramenta, com o perfil Estado e dados fictícios: `11.111.111/0001-11` e `11111111000111` acham a Construtora Exemplo; `11111111` (parcial)
não acha nada; `33.333.333/0001-33` (fornecedor de um ente fora do perfil) não acha nada. Ao vivo no site, a pergunta "O CNPJ 11.111.111/0001-11 tem contratos ou
sanções?" foi respondida com o contrato, a sanção, duas fontes e o botão "Exportar prova":

![Busca por CNPJ com fonte e Exportar prova](evidencias/2026-11-12/busca-por-cnpj-com-fonte-e-exportar-prova.jpg)

**E10. Plano e cobrança.** `site/setup.php`, linha 108: `['Único', 149.00, 0, 0.00, ['pe-estado', 'pe-garanhuns', 'br-uniao']]`. Seletor de plano desligado:
`site/public_html/assets/chat.js`, linha 26 (`ESCOLHER_PLANO = false`). Os campos de franquia e excedente só são devolvidos pela API, nenhuma rota os usa.

**E11. Ataques de prompt.** rodei 14/11: `python bench/ataques.py --modelos claude-sonnet-5-5` (base de exemplo, dados fictícios) → **165 execuções**
(46 ataques de uma mensagem e 2 conversas longas, de 10 e 12 turnos, nos perfis Município, Estado, Estado de exemplo e Estado com União):
**164 PASSOU, 1 ATENCAO, 0 FALHOU, 0 ERRO**, grafo intacto, US$ 1,81. O único ATENCAO (AP-08c) foi o modelo passar o texto do ataque como identificador, e o código recusou.
Também rodei os 3 ataques da tarefa B no perfil Município (AP-12b, AP-10a, AP-09b): 3 PASSOU, US$ 0,02. Revisão de 30 respostas, à mão:
`docs/tarefas-isaac/revisao-ataques-30-respostas.xlsx`. Nenhuma vazou dado; 3 mostram um defeito de apresentação (ver "Folheto × sistema").
Catálogo: `docs/seguranca/ataques-de-prompt.md`. AP-15, AP-18 e AP-19 ficam fora da bateria por serem do WhatsApp e do worker.
Auditoria por juiz: `bench/auditar_vazamento.py` (time 13/11, `docs/sessoes/2026-11-13-rodrigo.md`). Eu não repeti.

**E12. Prova aberta pelo código.** `chat/agente.py` (`completar_provas`) e `consulta/prova.py` (`escolher` e `abrir`): só abre a evidência de um fato que a
resposta cita, e nunca derruba a resposta se não conseguir abrir. rodei 14/11: `chat/testes` → **262 testes OK** (13 pulados), incluindo
`test_prova_automatica.py` (32 testes); `consulta/testes` → **313 testes OK**, incluindo `test_prova.py` (35 testes).

**E13. Busca por texto.** rodei 14/11: `python bench/busca.py` com a base do benchmark (44 fornecedores, 460 variações): **458/460** com o índice de texto
contra **323/460** da busca antiga (`CONTAINS`). Sem acento: 44/44 (eram 15). Ordem trocada: 44/44 (eram 0). Uma letra a menos e duas trocadas: 31/32.
**0 falsos positivos** em 46 nomes inventados ou misturados. Caça-bug no chat (tarefa E), com o agente real: 20 de 20 variações do nome da Construtora Exemplo
acharam o fornecedor certo, e um nome inexistente recebeu "não encontrei". Planilha: `docs/tarefas-isaac/caca-bug-busca-e-provas.xlsx`.

**E14. Porta de qualidade.** `python bench/benchmark.py rodar --subconjunto --minimo 0.9` (59 das 150 perguntas) sai com código 1 se a nota cair abaixo do mínimo
ou se algo vazar. rodei 14/11 com o Gemini: a porta funcionou e reprovou os dois modelos (40/59 e 46/59), em boa parte por respostas certas escritas
de um jeito que o gabarito não aceita (diário `docs/sessoes/2026-11-14-isaac-alvares.md`). time 14/11: Sonnet e DeepSeek Flash tiraram **57/59**.

## Limites desta verificação

Tudo que rodei foi no **ambiente local**, com **dados fictícios** (`fixtures/exemplo` e a base do benchmark) e uma conta de teste que só existe na minha máquina.
Não tenho a base real nem acesso ao site publicado, então nada aqui prova o comportamento com dados reais ou em produção.
Os prints de 08/11 são de uma versão anterior desta mesma branch.
