# Análise do projeto — 15/11/2026

**Atualização posterior:** a `feat/portabilidade-windows-linux` foi integrada em `9a705fd`. Ela separa o histórico por entes, corrigindo o achado 4 deste retrato anterior, e adiciona um adaptador Codex com limitações próprias. Os achados e números de linha abaixo descrevem `bf76f04`; a revisão das mudanças está em [Atualização da branch feat](atualizacao-feat-2026-11-15.md).

Revisão do clone Windows, branch `gpt/gabriella-ci-testes-2026-11-14`, commit `bf76f04`. Análise estática dos componentes e execução de testes gratuitos. Complemento desta retomada: conferência dos achados anteriores e quatro reproduções isoladas de comportamento do worker. Não é auditoria exaustiva nem certificação de produção. Nenhum segredo foi impresso, modelo pago chamado, deploy realizado ou grafo recarregado.

## Avaliação geral

O projeto é um MVP de consulta a fornecedores com rastreabilidade, bastante além de um protótipo de chat. Os pontos mais fortes são o filtro de acesso antes do modelo, consultas parametrizadas, evidências com hash, exportação de prova e testes de isolamento. Os principais riscos estão na entrega confiável das mensagens, na sustentação factual das respostas e na operação dependente do notebook.

O código oferece uma boa base para demonstração controlada. Para operação pública, convém resolver primeiro os achados de autorização, entrega e controle de consumo, validar o ambiente de hospedagem e repetir a avaliação dos modelos com as ferramentas atuais. Nesta retomada o Neo4j estava indisponível para os testes; portanto, não foi possível confirmar o funcionamento integrado do ambiente atual.

## Arquitetura e responsabilidades

| Componente | Responsabilidade | Observação |
|---|---|---|
| `coleta/` e `esquema/` | Coleta, normalização, proveniência e carga Neo4j | Fontes estaduais, municipais, federais, Receita e PNCP; cobertura varia por fonte |
| `consulta/` | Ferramentas MCP, perfis, consultas fixas e provas | O modelo não escolhe tenants nem escreve Cypher |
| `chat/agente.py` | Isolamento, eventos, fallback e provas automáticas | Claude em diretório neutro e com ferramentas limitadas |
| `chat/agente_openai.py` | Provedores compatíveis com chat completions | Lista permitida de ferramentas; texto final sem streaming |
| `chat/worker.py` | Fila do site, histórico e atendimento WhatsApp | Estado em memória e arquivos locais; requer processo disponível |
| `site/` | Contas, planos de demonstração, fila, administração e prova ZIP | PHP/MariaDB, sessões, CSRF, autorização por proprietário |
| `canal-whatsapp/` | Gateway Baileys, acesso, canal MCP e arquivos de mensagens | Canal de sessão e worker são caminhos operacionais diferentes |
| `bench/`, `fixtures/`, testes e CI | Avaliação factual, ataques e regressões | Resultados fictícios não demonstram cobertura do mundo real |
| `inferencia/`, `planilha/` | Visão, voz e Google Sheets | Parte herdada; dependências e permissões separadas do núcleo |

Fluxo central: navegador → fila MariaDB → worker → agente → MCP com perfil → Neo4j. O WhatsApp entra pelo gateway e arquivos locais. A coleta alimenta o grafo; o modelo consulta o que já foi carregado.

## Achados prioritários

### 1. Alta: respostas concluídas podem aparecer truncadas no navegador

Evidência: `site/public_html/api/lib_chat.php:117` devolve no máximo 200 eventos. Em `site/public_html/assets/chat.js:321`, o navegador encerra a consulta ao receber status final, mesmo quando esse lote não contém `fim` nem `erro`.

Cenário: uma resposta já concluída tem mais de 200 eventos pendentes para o navegador, por retomada ou atraso de rede. Ele recebe a primeira página e para. Pode perder o restante do texto, fontes e evento final. Achado por leitura combinada do produtor e consumidor; não reproduzido visualmente nesta sessão.

Recomendação: devolver indicação de próxima página/último seq e consumir o backlog até o evento terminal. Testar resposta longa concluída antes da primeira leitura e retomada após desconexão.

### 2. Alta: cursor do WhatsApp confirma mensagens antes do atendimento

Evidência: `chat/worker.py:462` persiste o cursor de todo o bloco antes de chamar `atender_whatsapp` na linha 467.

Se o processo cair entre esses pontos ou no meio de um bloco, a próxima inicialização começa depois das mensagens ainda não atendidas. Exceções também são registradas e o cursor permanece avançado. Reproduzido nesta retomada com a função original, dois registros fictícios e interrupção simulada antes de concluir o primeiro atendimento: o cursor já apontava para o fim dos dois registros. Não foi provocado crash no bot real.

Recomendação: processamento persistente por ID, estados de pendente/processando/concluído e confirmação após entrega. Incluir deduplicação para que a repetição após uma queda não duplique respostas.

### 3. Alta com perfis diferentes: WhatsApp usa acesso amplo antes de sincronizar

Evidência: `chat/worker.py:53` começa com `perfis_por_numero` vazio; `tenants_do_numero`, na linha 306, devolve `PERFIL_MANUAL` para qualquer número ausente. O laço WhatsApp e o de sincronização iniciam em threads independentes. A lista `allowFrom` do gateway persiste em disco e pode conter números anteriormente aprovados pelo site.

Cenário: após reiniciar o worker, um número de plano restrito já está autorizado no gateway, mas seu perfil ainda não foi carregado. A pergunta recebe Estado, Município e União. Se a API de telefones estiver indisponível, essa condição persiste. A troca atômica do dicionário evita uma corrida durante a atualização, mas não cobre a inicialização.

Reproduzido isoladamente: com o mapa inicial vazio, a função original devolveu os três entes para o remetente fictício de perfil restrito. Não foi demonstrado vazamento de dado real. O plano Único atual tem os mesmos três entes, o que reduz o impacto imediato nessa configuração; a garantia de isolamento deixa de valer quando os perfis diferem.

Recomendação: distinguir explicitamente números manuais de números do site, carregar os perfis antes de consumir mensagens e suspender atendimento quando a autorização não puder ser determinada. Testar reinício com API lenta ou indisponível.

### 4. Alta ao reduzir acesso: histórico anterior continua no contexto do modelo

Evidência: o histórico usa apenas `site:{usuario_id}` (`chat/worker.py:229`) ou `wa:{chat}` (`chat/worker.py:408`), sem incorporar os entes autorizados. As linhas 235 e 346 o enviam à pergunta seguinte; `chat/agente.py:112` inclui perguntas e respostas anteriores no prompt.

Reproduzido isoladamente: duas chamadas ao fluxo WhatsApp, primeiro com os três entes e depois só com Município, usando a mesma conversa. O segundo agente recebeu a resposta fictícia produzida sob o perfil amplo. A consulta MCP pode estar corretamente restrita, mas o texto de fora do escopo já chegou ao modelo pelo histórico. Não houve chamada a LLM nem prova de divulgação a outro usuário.

Recomendação: vincular o histórico à identidade e ao conjunto de permissões; limpar ou separar o contexto quando os entes mudarem. Aplicar também ao site e a grupos, caso sejam habilitados. O cenário exige mudança de perfil durante a vida do worker; não é mistura automática de contas diferentes.

### 5. Alta para entrega: erro 413 pode virar consulta concluída sem texto

Evidência: `Lote._postar`, em `chat/worker.py:210`, trata qualquer HTTP menor que 500 como confirmação e remove o lote. A API limita cada evento a 20.000 bytes (`lib_worker.php:11`). O worker concatena deltas sem teto de bytes; provedores compatíveis com OpenAI emitem a resposta inteira em um evento.

Reproduzido isoladamente com o `Lote` original e uma API simulada que aplica o limite real: um delta de 20.001 caracteres ASCII foi rejeitado com 413 e removido; o evento `fim` seguinte foi aceito. O servidor poderia encerrar a consulta sem o texto. O risco também abrange perda silenciosa de lotes em outras recusas 4xx, embora cada código precise de tratamento próprio.

Recomendação: dividir texto pelo tamanho do JSON serializado em UTF-8 e encerrar com erro observável quando um lote for recusado. Somente confirmação de sucesso deve contar como persistência; repetir indefinidamente um 413 também não resolve. Testar texto longo com acentos e resposta sem streaming.

### 6. Alta antes de exposição pública: consumo de modelos sem limite cumulativo por conta

Evidência: `rota_perguntas_criar` limita a uma pergunta aberta por usuário, mas não aplica orçamento diário/mensal ou limite global da fila. Cadastro é público; `rota_assinatura` ativa plano de demonstração sem pagamento por desenho.

O limite de concorrência por conta não limita o custo acumulado e pode ser multiplicado por novas contas. Não é falha para uma demonstração fechada; é risco de custo e disponibilidade se o mesmo modo for publicado amplamente.

Recomendação: limites de requisições e de gasto, teto global da fila, proteção do cadastro e uma configuração explícita para demonstração versus operação comercial.

### 7. Média: presença de prova não garante correção de toda a resposta

Evidência: `consulta/prova.py` escolhe evidências por número, valor ou data; `chat/agente.py:475` tenta completar fontes e registra ausência sem bloquear a resposta. `lib_prova.php` classifica a completude dos metadados, sem verificar semanticamente cada afirmação.

É uma boa proteção de proveniência, mas uma agregação incorreta pode vir acompanhada de uma fonte verdadeira. O diário anterior registra o caso N010, de contagem de sanções; ele não foi reexecutado nesta análise.

Recomendação: agregações determinísticas no backend, contagem total separada de listas limitadas, e avaliação que confira cada número da resposta. Explicar na interface o alcance de `com_prova`.

### 8. Média: limite de memória da exportação chega depois da leitura integral

Evidência: `site/public_html/api/lib_prova.php:184` usa `fetchAll()` antes de contabilizar os bytes e aplicar o corte. O teto final de 5 MB não limita a memória já alocada ao buscar todos os eventos.

Recomendação: limitar os bytes acumulados por pergunta e interromper a leitura ao atingir o orçamento, usando também consulta paginada ou não bufferizada. Apenas trocar `fetchAll()` por `fetch()` não garante o limite se o driver MySQL continuar bufferizando o resultado. O impacto depende da quantidade real de eventos e da memória disponível no PHP; não foi feito teste de exaustão.

### 9. Média: tempos de espera do cliente e do servidor divergem

O navegador para após 130 s (`chat.js:29`), a fila pode esperar 120 s e o processamento pode durar mais 180 s (`lib_chat.php:8–9`). Uma pergunta reservada perto do fim da espera pode continuar válida no servidor depois da desistência da tela.

Recomendação: prazos coerentes, calculados a partir do estado da pergunta, e retomada de consultas que ainda estão processando.

### 10. Média: teste do canal MCP apresenta falha no Windows em rodada anterior

O ensaio completo do Bun falhou ao abrir o canal no sandbox. Repetido fora do sandbox, o arquivo `canal.test.ts` aprovou 14 testes, inclusive isolamento de anexos, mas falhou no segundo grupo, de caminhos relativos e pastas extras, com `Connection closed`.

Isso limita a garantia de portabilidade do teste/canal nesse cenário. Não prova falha do gateway ou do WhatsApp real. Investigar a inicialização do segundo processo e capturar seu stderr antes de atribuir causa. Nesta retomada, o Bun não foi encontrado no PATH e a suíte TypeScript não foi repetida; o resultado acima pertence à rodada anterior registrada neste clone.

### 11. Baixa: documentação mistura estados de datas diferentes

O README ainda diz que o agente isolado não existe e que nenhum ataque real foi executado. O código contém o agente, e o diário de 14/11 registra ataques e consultas reais. Contagens de testes e cobertura também variam entre seções.

Recomendação: atualizar a matriz de requisitos e pendências com referência a comandos, ambiente e data. Separar claramente situação da branch, situação do bot em execução e situação do servidor publicado.

### 12. Média: proteção dos logs estruturados não cobre o log legado do chat

Evidência: `chat/worker.py:60` grava `logs/chat.jsonl` diretamente, preservando `pergunta` após mascarar somente CPF. Não usa `registro.limpar` nem a rotação por tamanho dos logs por subsistema. Perguntas contendo e-mail, telefone ou segredo podem permanecer nesse arquivo. A fila `inbound.jsonl` também contém conteúdo bruto por desenho.

Os logs por subsistema possuem uma proteção melhor; a descrição genérica de que nenhum log contém texto de mensagem não se aplica a todos os arquivos. Achado estático; nenhum log de conversa real foi aberto para buscar dados pessoais.

Recomendação: definir quais arquivos são histórico necessário e quais são telemetria, reduzir conteúdo no log legado, aplicar mascaramento consistente e estabelecer retenção, rotação e permissões para históricos e mídias. Registrar essa diferença na documentação operacional.

## Segurança e manutenção

Proteções encontradas: SQL parametrizado; cookies HttpOnly/Secure conforme ambiente; CSRF nas escritas do navegador; regeneração de sessão; limitação de falhas de login; chave própria do worker com comparação constante; autorização por dono nos eventos e exportações; perfil fora dos argumentos do modelo; restrição de ferramentas; validação de caminhos reais dos anexos; mascaramento e rotação dos logs por subsistema. Essas proteções não eliminam as lacunas de contexto, inicialização e log legado descritas acima.

Limites: o pacote não inclui o bruto nem versão de extrator e não avalia todos os dados pessoais. Hashes demonstram integridade em relação aos bytes conferidos, sem certificar interpretação factual. Não foram auditadas dependências contra bases de vulnerabilidades nem permissões reais de hospedagem. `.env` e `google-sa.json` não apareceram em `git ls-files`; isso não verifica o histórico completo do Git.

O núcleo tem separação razoável entre coleta, consulta, agente e interface. A manutenção fica mais difícil pela coexistência do modelo inicial de hackathon, dos módulos auxiliares e de dois modos de atendimento WhatsApp. Configuração, instalação e demonstração devem indicar explicitamente quais componentes são necessários.

## Verificações da retomada atual — Windows 11, Python 3.13.3

| Verificação | Resultado desta execução |
|---|---|
| `git pull`, status e histórico | Clone atualizado; alterações locais preservadas; hook já configurado |
| `.venv\Scripts\python -X utf8 -m unittest discover -s consulta/testes` | 313 descobertos: 270 aprovados, 43 pulados, zero falhas; 2,786 s |
| `.venv\Scripts\python -X utf8 -m unittest discover -s chat/testes` | 262 descobertos: 247 aprovados, 15 pulados, zero falhas; 168,675 s |
| Diagnóstico `test_acesso_neo4j.MOTIVO` | Neo4j indisponível (`ServiceUnavailable`); nenhuma carga ou inicialização de banco executada |
| `.venv\Scripts\python -m pip check` | Nenhuma dependência instalada incompatível; isso não é auditoria de vulnerabilidades |
| `php -l` nos sete arquivos da API e `site/setup.php` | Oito arquivos sem erro de sintaxe |
| Quatro reproduções locais do worker | Cursor antecipado, perfil inicial amplo, histórico após redução de perfil e descarte de HTTP 413 confirmados |

As reproduções usaram Python por stdin, extraindo por AST as definições originais de `worker.py`, com dependências substituídas em memória, API simulada e arquivos temporários fictícios dentro de `logs/`. Não importaram a configuração do worker, não acionaram o gateway e não alteraram código de produção. Confirmam o comportamento das funções nos cenários descritos; não substituem teste integrado.

Os 43 testes pulados de consulta dependem do Neo4j. No chat foram pulados 12 testes exclusivos de Linux, dois de prova no grafo e um de canal opcional sem Bun. Surgiram avisos de drivers Neo4j não fechados. Logs das suítes em `logs/analise-consulta-2026-11-15.log` e `logs/analise-chat-2026-11-15.log`, ignorados pelo Git.

API, pacote de prova, interface, coleta externa, voz, visão, planilha, hospedagem e provedores reais não receberam novo teste funcional nesta retomada. A revisão desses módulos foi estática. Não foram pesquisadas vulnerabilidades de dependências em serviços externos. Nenhum resultado histórico abaixo deve ser lido como integração aprovada no ambiente atual.

## Verificações da rodada anterior, preservadas do relatório existente

- `git pull`: concluído, clone já atualizado; `git status` e histórico conferidos. Hook já configurado em `.githooks`.
- `.venv\Scripts\python -X utf8 -m unittest discover -s consulta/testes`: 313 testes, todos aprovados, 28,070 s.
- `.venv\Scripts\python -X utf8 -m unittest discover -s chat/testes`: 262 testes, 250 aprovados e 12 pulados por exigirem Linux, 215,477 s. Avisos de drivers Neo4j não fechados; suite terminou com código zero.
- `php -l`: sete arquivos da API e `site/setup.php`, todos sem erro de sintaxe.
- `bun test testes`: 27 aprovados e 1 falha de inicialização MCP no sandbox. Reteste isolado fora dele: 14 aprovados e 1 falha no segundo grupo.
- Testes de API e prova não repetidos: modificam dados locais e exigem confirmar ausência de worker; a consulta de processos por CIM foi negada. O resultado histórico verde do CI é evidência anterior, não execução desta análise.
- Sem validação visual, celular real, instalação limpa, deploy, carga, chamadas pagas, coleta externa ou ensaio de queda. Módulos auxiliares receberam leitura estática, não testes funcionais completos.

## Ordem de trabalho recomendada

1. Fechar as lacunas de autorização na inicialização do WhatsApp e no histórico após mudança de perfil.
2. Corrigir paginação do chat, confirmação de entrega do WhatsApp e descarte de lotes recusados, com cenários de falha.
3. Introduzir limites de consumo e fila antes da exposição pública; alinhar prazos e limitar exportação durante a leitura.
4. Resolver agregação N010 e medir novamente prova, ataques e benchmark com as ferramentas atuais.
5. Investigar o segundo processo MCP do teste de canal no Windows; restaurar a verificação integrada com serviços disponíveis.
6. Validar deploy HTTPS e dispositivos reais; planejar operação sem dependência de notebook pessoal e recuperação dos estados persistentes.
7. Atualizar documentação, retenção dos logs e cobertura e limitações de cada fonte. Validar a hipótese de valor e o preço com usuários reais antes de assumir viabilidade comercial.
