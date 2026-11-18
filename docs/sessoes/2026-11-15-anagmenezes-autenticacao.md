# 2026-11-15: anagmenezes-autenticacao

- **Quem:** AnagMenezes (Gabriella, via Codex)
- **Branch e commit de partida:** gpt/gabriella-autenticacao-site-2026-11-15 a partir de origin/feat/portabilidade-windows-linux em b7dc44b
- **Máquina e ambiente:** Windows local, maquina bibis, Git e Python da .venv. Sem iniciar ou alterar servicos.

## Resumo

Atualizada a feat local e criada/selecionada a branch de autenticacao solicitada. A origem recebeu tres commits novos desde 584efc2 e agora esta em b7dc44b. Dois ajustes locais anteriores foram preservados no stash 6668b2d. Nenhuma alteracao de autenticacao implementada; somente este diario esta no disco, sem commit ou push desta etapa.

## Feito

- feat/portabilidade-windows-linux atualizada por fast-forward de a8b628d para b7dc44b.
- Criada e selecionada gpt/gabriella-autenticacao-site-2026-11-15, com HEAD identico a origem remota e sem upstream herdado da feat.
- Stash preservar-ajustes-antes-branch-autenticacao-2026-11-15 (6668b2d) guarda somente infra/docker-compose.yml e site/dev/test_api.py, da branch anterior. Nao aplicado na branch nova. O stash anterior tambem foi mantido.
- Diario criado copiando _modelo.md, com pendencias herdadas do diario anterior em e387ca2. Nenhum arquivo de codigo editado nesta tarefa.

## Verificado (e como)

- Em 15/11/2026, Windows, maquina bibis: git pull atualizou origin/feat/portabilidade-windows-linux de 584efc2 para b7dc44b. git status, git branch -avv, git log, hook e identidade conferidos; instrucoes e tres diarios mais recentes lidos.
- git stash push -- com os dois caminhos: escopo conferido por git stash show --name-only; arvore limpa antes da troca. git switch feat/portabilidade-windows-linux e git merge --ff-only origin/feat/portabilidade-windows-linux concluidos sem conflitos.
- git switch --no-track -c gpt/gabriella-autenticacao-site-2026-11-15 concluido. git rev-parse HEAD confirmou b7dc44b5f65f02be8f0ae8755c9ed6057521ce48, igual a origem.
- Leitura de site-institucional/LEIA-ME.md e busca das rotas em site/public_html/api/lib_conta.php: cadastro, login e logout permanecem no PHP; o portfolio fica em subpasta.
- Diario validado com .venv\Scripts\python -X utf8 docs/sessoes/validar.py docs/sessoes/2026-11-15-anagmenezes.md; verificacao final da base e do status sem alteracoes de codigo.

## Não verificado

- Sem testes funcionais de login, cadastro, API, banco, build React ou suites completas nesta preparacao de branch. Nenhuma mudanca de autenticacao foi solicitada em detalhe nem implementada. Pendencias herdadas abaixo nao foram revalidadas. Sem commit, push ou deploy desta nova branch.

## Decisões e motivo

- Criar diretamente da feat remota atualizada, conforme pedido, sem incorporar a branch de CI por merge. O workflow e os relatorios exclusivos da branch anterior continuam nela.
- Guardar os ajustes locais em stash identificado para iniciar a branch de autenticacao sobre o codigo exato da origem, preservando o trabalho anterior. Nao ler nem modificar configuracao de segredos.

## Em aberto (por prioridade)

- [ ] Definir e implementar as mudancas de autenticacao desejadas na nova branch; revisar login, cadastro e sessao, com testes adequados ao escopo. (origem: 2026-11-15-anagmenezes)

Pendencias herdadas da branch anterior; nao revalidadas nesta tarefa:
- [ ] Feat, backup: propagar falha do mysqldump no shell remoto, tratar primeiro setup em banco vazio e respeitar DB_PORT; testar recuperação antes do deploy. (origem: 2026-11-15-anagmenezes)
- [ ] Feat, rastreabilidade: registrar modelo concreto no ramo Codex e definir complementação automática de provas, além de preservar os metadados já apontados. (origem: 2026-11-15-anagmenezes)

- [ ] Portfolio ja recebido em site-institucional/: manter revisao de planos, deploy, autenticacao do admin, inclusao de componentes no TypeScript e build no CI. Links para o chat foram atualizados na origem. (origem: 2026-11-15-anagmenezes)

- [ ] Integração feat: corrigir encerramento Codex no Windows e preservar todos os metadados de prova no adaptador; incluir onze testes novos no CI e investigar instabilidade local do teste de status. (origem: 2026-11-15-anagmenezes)
- [ ] Análise, retomada: distinguir números manuais dos sincronizados e carregar autorização antes de consumir WhatsApp. Histórico por entes corrigido pela feat integrada. (origem: 2026-11-15-anagmenezes)
- [ ] Análise, retomada: dividir eventos por bytes UTF-8 e tratar HTTP 413 e demais recusas sem perda silenciosa; revisar retenção e mascaramento do log legado. (origem: 2026-11-15-anagmenezes)
- [ ] Restabelecer serviços e executar integração; os testes pulados nesta retomada não validam o isolamento no banco nem API/prova. (origem: 2026-11-15-anagmenezes)

- [ ] Análise geral: corrigir consumo paginado dos eventos finais do chat e confirmação do cursor WhatsApp após atendimento, com deduplicação. (origem: 2026-11-15-anagmenezes)
- [ ] Antes de exposição pública: limitar consumo acumulado e fila; alinhar prazos cliente/servidor e limitar memória durante leitura de eventos para exportação. (origem: 2026-11-15-anagmenezes)
- [ ] Investigar inicialização da segunda instância MCP no teste de canal Windows e atualizar trechos desatualizados do README. (origem: 2026-11-15-anagmenezes)


Pendencias herdadas dos diarios de 14/11:
- [ ] Resolver saldo da API OpenAI; benchmark OpenAI e ataques pagos permanecem pendentes.
- [ ] Decidir destino da correcao local do teste da API e alteracao preexistente da infraestrutura; fora do commit CI.
- [ ] Investigar agregacao N010 e avaliar padroes S02/V28 e prova N033/N034 sem alterar gabarito automaticamente.
- [ ] Melhorias de voz, instalacao Docker em Windows limpo, cadastro sob demanda, orgaos PNCP e duplicidade, analise da API da Receita.
- [ ] Apresentacao e deploy Hostinger, repeticao de ataques e conversas apos mudancas, cache, alertas de saude e matriz WhatsApp. Ver docs/BACKLOG.md e diario 2026-11-14-rodrigo.

## Resolvido de sessões anteriores

- [x] Preparacao da branch de autenticacao concluida a partir da feat atualizada. (origem: 2026-11-15-anagmenezes)
- [x] Push anterior concluido em e387ca2 na branch de CI; nao altera a origem desta nova branch. (origem: 2026-11-15-anagmenezes)
- [x] Portfolio da Rafaella recebido pela feat em subpasta (9a9d6b2); links da tela de teste atualizados em dea3197 e b7dc44b. O conflito da simulacao de merge direto nao se aplica a essa importacao ja feita. (origem: 2026-11-15-anagmenezes)

## Armadilhas

- O stash 6668b2d pertence ao trabalho anterior; aplicar apenas quando for retomar aqueles ajustes, sem sobrescrever mudancas futuras.
- A nova branch foi criada sem upstream: ela nao acompanha nem envia automaticamente para a feat.
- Codigos e configuracoes ignorados pelo Git permanecem locais; criar branch nao reinstala dependencias nem valida o ambiente. O arquivo do diario e a unica diferenca local intencional desta etapa.

## Próximo passo sugerido

Implementar as mudancas de autenticacao que o usuario especificar, trabalhando em gpt/gabriella-autenticacao-site-2026-11-15.
