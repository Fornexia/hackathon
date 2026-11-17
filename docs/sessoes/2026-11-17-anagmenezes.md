# 2026-11-17: anagmenezes

- **Quem:** AnagMenezes, via Codex
- **Branch e commit de partida:** gpt/gabriella-autenticacao-site-2026-11-15 em 09267ca
- **Máquina e ambiente:** Windows local, Git, Python da .venv e PyMuPDF temporario fora do produto.

## Resumo

A pedido da usuaria, adicionados dois PDFs comerciais fornecidos em Downloads, sem editar o conteudo. Preparado commit limitado aos dois documentos e a este diario obrigatorio, seguido de envio autorizado para a branch atual. Alteracoes locais anteriores permanecem fora deste envio.

## Feito

- Incluidos docs/comercial/analise-de-rentabilidade-fornex.pdf e docs/comercial/proposta-preliminar-fornex.pdf, copias integrais dos originais. Este conjunto compoe o commit de documentos da tarefa.
- Nenhuma alteracao em codigo, configuracao privada ou banco. Relatorio Markdown e diario do dia anterior, ja modificados antes desta tarefa, preservados sem incluir no commit.

## Verificado (e como)

- Windows local, Python da .venv e Git: status e log conferidos; git fetch origin sem merge/rebase confirmou a branch atual sincronizada antes do envio. Lidos instrucoes e tres diarios recentes.
- PDFs abertos com PyMuPDF temporario: 20 e 8 paginas, respectivamente, sem anexos. Varredura do texto nao encontrou padroes de chaves privadas, tokens de provedor, enderecos pessoais, documento pessoal formatado ou telefone. Metadados de autoria mantidos. Conferencia de SHA-256 comprovou copias identicas aos originais.
- Validador do diario e git diff --cached --check executados antes do commit. O envio ao remoto e conferido ao final, sem abrir PR ou fazer deploy.

## Não verificado

- Nao houve nova auditoria financeira, correcao das premissas ou alteracao editorial dos PDFs; publicados como fornecidos. Nao repetidos testes do produto, pois somente documentos foram acrescentados.

## Decisões e motivo

- Usar docs/comercial e nomes de arquivo sem espacos, mantendo os bytes originais. Usar a mesma branch da autenticacao conforme o contexto do pedido de envio ao repositorio, sem mudar a base ou reescrever o historico.
- Incluir somente os PDFs solicitados e o diario obrigatorio; nao incorporar as alteracoes pendentes da analise anterior.

## Em aberto (por prioridade)

- [ ] Cobertura/custos: obter inventario da instancia usada na apresentacao, contagens por fonte/orgao/ano e completude; definir contratante versus usuario e receita da equipe; medir horas de manutencao/suporte e faturamento real da operacao. Infraestrutura e consumo considerados da contratante conforme pedido. (origem: 2026-11-16-anagmenezes)

- [ ] Google em homologacao: revisar limites do tokeninfo e a politica explicita de vinculo para enderecos externos sem Workspace, configurar Client ID, popup/origens e validar com contas reais. Migração atualizada somente apos backup e autorizacao no ambiente escolhido. Sem push nesta tarefa. (origem: 2026-11-16-anagmenezes)

- [ ] Auditoria, escopo: decidir tratamento dos 43 arquivos do portfolio antes de PR exclusivo da autenticacao; proposta documentada e comandos antigos do README e guia Windows/Linux atualizados. Se o portfolio permanecer no PR, revisar inclusao de componentes reais no tsconfig. Nao remover funcionalidades nem mudar historia sem aprovacao. (origem: 2026-11-16-anagmenezes)
- [ ] Para ativar o login publico: configurar SMTP, origem HTTPS, chave privada da fila e cron; aplicar a migracao apos backup no ambiente escolhido e homologar entrega real e perfis. Nenhuma dessas configuracoes foi alterada nesta sessao. (origem: 2026-11-16-anagmenezes)


Pendencias herdadas da branch anterior; nao revalidadas nesta tarefa:
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

- [x] Commits da autenticacao ja enviados em sessao anterior; nesta tarefa o envio e exclusivo dos documentos comerciais e diario. (origem: 2026-11-16-anagmenezes)

## Armadilhas

- O primeiro PDF possui trechos com hipoteses financeiras de versoes diferentes; copia para o repositorio nao equivale a revisao ou aprovacao de valores.
- Os dois arquivos locais anteriores continuam pendentes; nao usar git add indiscriminado. Nao registrar segredos ou dados pessoais no diario.

## Próximo passo sugerido

Revisar os documentos no GitHub e decidir os ajustes comerciais com a equipe; nenhuma publicacao do sistema ou alteracao financeira foi executada.
