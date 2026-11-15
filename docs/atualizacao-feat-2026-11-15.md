# Atualização da branch feat — 15/11/2026

Origem escolhida pelo usuário: `origin/feat/portabilidade-windows-linux`, commit `584efc2`.
Destino: `gpt/gabriella-ci-testes-2026-11-14`, partindo de `bf76f04`.
A comparação usa o ancestral comum `a8b628d`; são sete commits exclusivos da origem e três exclusivos do destino.
A integração automática reuniu 45 arquivos, sem conflitos, preservando o workflow, o executor e os registros do CI.
Merge local concluído em `9a705fd`, com pais `bf76f04` e `584efc2`. As quatro alterações locais anteriores foram restauradas sem conflitos; a cópia de segurança no stash foi mantida. Este relatório e a atualização do diário ficam somente no disco.

## Atualizações recebidas

| Área | Mudança | Consequência operacional |
|---|---|---|
| Visual | Paleta ciano e azul-marinho, Manrope, tema claro/escuro e botão persistido no navegador | Páginas e iframe compartilham a escolha de tema |
| Agente do site | Adaptador Codex por sessão; `AGENTE_SITE_PROVEDOR` assume `codex` | Requer autenticação, modelo e binário Codex disponíveis no worker; não usa a cadeia de fallback anterior nessa rota |
| WhatsApp | Mantém o provedor anterior | Troca do agente do site não migra o WhatsApp |
| Histórico | Chaves incluem os entes autorizados, ordenados | Evita levar respostas de um perfil mais amplo ao contexto de outro perfil |
| Sanções | `cobertura` passa a retornar total, fornecedores e até três exemplos de sanções com situação `EM ABERTO` | Evita varrer todos os fornecedores; esse campo não representa a vigência do CEIS/CNEP federal |
| Worker | Cliente HTTPS com IPv4 e validação TLS; sondagem a cada três segundos | Contorna o problema de IPv6 descrito no incidente da origem |
| Oferta | Só o plano Único é oferecido; migração preserva os planos referenciados pelo histórico | Assinaturas ativas antigas são migradas sem reescrever perguntas anteriores |
| Telefones | Novos números nascem aprovados; administração pode bloquear e liberar novamente | Aprovação manual deixa de ser etapa obrigatória; o setup também libera pendentes legados |
| Deploy | Domínio padrão FornexIA; backup de arquivos e banco antes da publicação | Script modificado, mas não executado nesta análise |
| Comercial | Documento base em DOCX/PDF e material de benchmark/custo Codex | Arquivos recebidos; conteúdo comercial e resultados históricos não foram revalidados |

## Achados da revisão

### Alta no Windows: encerramento do adaptador Codex não é portável

`chat/agente_codex.py`, método `Sessao.fechar`, usa `os.killpg` e `signal.SIGKILL`. O primeiro não existe no Windows desta máquina.
Reproduzido sem abrir uma sessão real, instanciando o objeto sem construtor e substituindo o processo por um mock: `fechar()` levanta `AttributeError`.
O encerramento roda em `finally`, portanto pode interromper a limpeza e propagar erro até depois de uma resposta concluída.
Além disso, a descoberta do binário da extensão procura somente o caminho Linux, antes de recorrer ao PATH ou `CODEX_BIN`.

Recomendação: implementar encerramento da árvore de processos conforme a plataforma, testar timeout e saída normal em Windows e Linux e conferir a descoberta do executável. Os onze testes novos não exercitam o encerramento de uma sessão real.

### Alta para rastreabilidade: a fonte Codex perde metadados da prova

`eventos_do_item` repassa identificador, trecho, URL, captura e `hash_confere`, mas omite `documento_hash`, `arquivo`, `tabela`, `linha` e `trecho_mascarado`.
Reproduzido com um resultado MCP fictício contendo todos esses campos: os cinco desapareceram do evento de saída.
`lib_prova.php` exige parte deles para classificar a cadeia como completa. Assim, uma evidência originalmente completa pode sair como `prova_incompleta` no pacote quando o site usa Codex.

Recomendação: reutilizar a tradução de fontes do agente existente e verificar a exportação com esse provedor. O adaptador também não passa pela mesma etapa de complementação automática de provas da cadeia anterior.

### Média: testes novos ainda não fazem parte do executor de CI

Os onze testes estão em `chat/test_worker.py`. `scripts/testes_ci.py` descobre apenas `chat/testes` para a suíte de chat.
Eles foram executados separadamente nesta revisão, mas não serão incluídos automaticamente pelo workflow preservado.
Recomendação: incluí-los no executor ou movê-los para a pasta descoberta, ajustando os imports.

### Pendências herdadas da análise anterior

O histórico por entes corrige o achado de contexto após redução de perfil. A paginação do chat, o cursor WhatsApp confirmado antes do atendimento, o perfil amplo antes de sincronizar, o descarte de HTTP 413, os limites acumulados de consumo e a retenção do log legado continuam presentes. Ver `docs/analise-projeto-2026-11-15.md`; suas referências de linha descrevem o código anterior à integração.

## Verificação nesta máquina

Windows 11, Python 3.13.3 da `.venv`, sem chamadas pagas, deploy, envio de WhatsApp ou migração de banco.

- `git pull`: referências atualizadas; a branch atual já estava atualizada com seu upstream.
- Comparações por `git log --left-right`, `git diff --stat`, histórico e leitura do código.
- Cópia isolada da origem em `logs/revisao-feat-2026-11-15`, criada com `git archive`, sem copiar o `.env`.
- Consulta na cópia isolada: 313 descobertos, 270 aprovados, 43 pulados, zero falhas, 6,002 s. Neo4j indisponível; variáveis fictícias somente no processo de teste.
- Testes novos, `python -m unittest discover -s chat -p 'test_*.py'`: onze aprovados na cópia isolada e na árvore integrada.
- `php -l`: oito arquivos sem erro de sintaxe, cobrindo a API e o setup.
- Duas reproduções locais confirmaram a falha de encerramento Windows e a perda de metadados de prova. Sem LLM e sem arquivos de autenticação.
- Suíte existente de chat: 262 descobertos em 305,599 s; 244 aprovados, 15 pulados, duas falhas em scripts shell e um erro de gravação temporária no vigia. Durante a execução, o PowerShell também falhou ao iniciar com `System.OutOfMemoryException`; não é possível atribuir todos os problemas à branch.
- Reteste apenas dos três casos: a sintaxe shell e a gravação do vigia passaram; o teste de status dos serviços continuou falhando no Windows. Os scripts e esse teste não são alterados pela origem. O reteste não torna a execução completa aprovada.
- Controle no código anterior (`bf76f04`), extraído em pasta isolada: o mesmo teste de status passou em 22,690 s. O comportamento varia nesta máquina; a causa ainda não foi confirmada. Nenhuma proteção ou asserção foi removida para obter aprovação.
- Reteste final do status na árvore integrada, sem mudanças de código: passou em 20,000 s. Os três casos problemáticos passaram em execuções pontuais posteriores; a suíte completa não foi repetida nem declarada aprovada.

API com MariaDB, prova integrada, navegador, autenticação Codex real, coleta externa, backup remoto e hospedagem não foram testados nesta tarefa. O conteúdo do `.env` não foi alterado.

## Limite da integração

A origem foi integrada como recebida; os achados acima não foram corrigidos automaticamente. A `feat/api-demo`, embora também descoberta no remoto, ficou fora da integração por escolha explícita do usuário. Nenhum push ou deploy foi feito.

## Revisão complementar solicitada em 15/11/2026

Escopo adotado: `feat/portabilidade-windows-linux`, identificada no histórico como a feat escolhida pelo usuário. Depois de novo `git pull` (`Already up to date`), a origem continua em `584efc2` e a branch atual em `9a705fd`. Não houve nova integração nesta revisão.

`git merge-base --is-ancestor origin/feat/portabilidade-windows-linux HEAD` retornou zero: a origem já está inteiramente incluída. `git rev-list --left-right --count HEAD...origin/feat/portabilidade-windows-linux` retornou `4 0`. O código commitado de `chat`, `consulta`, `site` e `bench` é igual nas duas referências, conforme `git diff --exit-code`; isso não inclui as modificações locais não commitadas.

### Achados confirmados novamente

1. **Alta — encerramento no Windows:** `chat/agente_codex.py:109` chama `os.killpg`, inexistente no Windows. Reprodução com processo simulado levantou `AttributeError`, sem iniciar Codex. Como `fechar` é chamado no `finally`, a exceção pode ocorrer depois do evento `fim`, atrapalhar a limpeza e acionar o tratamento de erro do worker.
2. **Alta — metadados de prova descartados:** `chat/agente_codex.py:119` perdeu `arquivo`, `documento_hash`, `linha`, `tabela` e `trecho_mascarado` ao traduzir uma evidência fictícia completa. A exportação PHP depende desses metadados para completar a cadeia até o arquivo bruto. O ramo Codex também retorna antes de `completar_provas`, comportamento confirmado com mock; ele depende das evidências abertas explicitamente pelo modelo. Recomenda-se usar o caminho comum de registro de fontes e definir a complementação para esse provedor.
3. **Média — modelo registrado apenas como provedor:** `chat/agente.py:537` grava `leitor.modelo_pedido` e `leitor.modelo` como `codex`. O adaptador escolhe o modelo concreto em sua configuração, sem atualizar esses campos. Reprodução do roteamento com resposta simulada confirmou `CODEX_MODEL_RECORDED=codex`. O worker usa esses campos no evento final e no log; a prova perde o nome do modelo efetivo.
4. **Média — testes novos fora do CI:** os onze casos em `chat/test_worker.py` passam isoladamente, mas `scripts/testes_ci.py:15` descobre somente `chat/testes`. O teste chamado `test_fonte_preserva_prova` verifica trecho e hash, sem conferir os metadados faltantes nem o encerramento Windows.

### Achados adicionais na rotina de backup

**Alta — erro de dump parcial pode passar como backup válido.** Em `site/deploy.sh:23`, o comando remoto executa `mysqldump | gzip` sem ativar `pipefail` no shell remoto. O `set -euo pipefail` do script local não é transmitido pelo SSH. Se o dump falhar depois de emitir algum `CREATE TABLE`, o gzip pode terminar com sucesso e a checagem de conteúdo aprovar o arquivo parcial. A publicação pode então continuar sem um backup completo, contrariando a promessa do script.

Reprodução local apenas da pipeline, em Git Bash sem perfil: uma função fictícia `mysqldump` emitiu uma linha `CREATE TABLE` e terminou com código 2. Sem `pipefail`, a pipeline e a checagem retornaram zero. Controle com `set -eo pipefail` retornou 2. Não houve conexão SSH nem execução do deploy. A conclusão é sobre o shell remoto usual sem `pipefail`; configurações especiais do servidor não foram inspecionadas.

**Média — primeira publicação em banco vazio é bloqueada.** A mesma checagem exige ao menos um `CREATE TABLE` antes de executar o `setup.php`. Com dump vazio válido, a pipeline retornou 1. Portanto, em banco recém-criado sem tabelas, o fluxo `--setup` para antes da criação do schema. É necessário distinguir banco inicialmente vazio de falha no backup, mantendo a interrupção em erros reais.

Também foi observado estaticamente que o backup não repassa `DB_PORT` ao `mysqldump`, embora o script grave essa porta na configuração PHP. A consequência depende do uso de porta diferente da padrão; esse cenário não foi executado.

### Comparação com a branch da Rafaella

Para cobrir o contexto da análise anterior, foi simulada também a integração direta de `origin/portfolio-fornexia-rafaella` na feat. `git merge-tree --write-tree origin/feat/portabilidade-windows-linux origin/portfolio-fornexia-rafaella` encontrou novamente um único conflito add/add em `AGENTS.md`, com README combinado automaticamente. Logo, mudar o destino para a feat não elimina esse conflito nem as pendências funcionais do portfólio. Nenhuma branch foi alterada.

### Verificações desta revisão

Máquina `bibis`, Windows, Python da `.venv`, 15/11/2026. Cópia isolada da origem criada por `git archive` em diretório temporário, com parâmetros fictícios e sem copiar configurações locais. Somente testes gratuitos e simulações:

| Comando na cópia isolada | Resultado atual |
|---|---|
| `python -X utf8 -m unittest discover -s chat -p test_*.py` | 11 aprovados, 0,140 s |
| `python -X utf8 -m unittest discover -s chat/testes -p test_portabilidade.py` | 4 aprovados, 0,018 s |
| `python -X utf8 -m unittest discover -s chat/testes -p test_prova_automatica.py` | 32 descobertos, 29 aprovados e 3 pulados, 0,069 s |
| `php -l` nos sete arquivos da API e `site/setup.php` | Oito aprovados |
| Reproduções isoladas de encerramento, fonte, modelo e complementação | Comportamentos descritos acima confirmados |
| Pipeline de backup com dump fictício em Git Bash | Dump parcial aceito sem pipefail; rejeitado com pipefail; banco vazio rejeitado |

Total dos testes Python direcionados: **44 aprovados e três pulados**, sem falhas. Isso não substitui a suíte completa nem valida Codex autenticado, integração com banco, interface, backup restaurável ou servidor real. Não se repetiram as suítes completas já descritas no histórico. Nenhuma correção de produção, merge, push, deploy, chamada de modelo ou mudança em banco foi feita nesta revisão.

Recomendação: a integração de código já existe, mas corrigir encerramento Windows, preservação da prova e backup antes de considerar a feat pronta para operação nesse ambiente. Cobrir os casos novos no CI e executar o fluxo real do site depois das correções.
