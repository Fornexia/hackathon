# 2026-11-17: anagmenezes

- **Quem:** AnagMenezes, via Codex
- **Branch e commit de partida:** docs/rentabilidade-proposta a partir de origin/main em af43561
- **Máquina e ambiente:** Windows local, Git com checkout isolado e Python da .venv do checkout original.

## Resumo

A usuaria pediu separar os dois PDFs comerciais da autenticacao. Criada docs/rentabilidade-proposta diretamente de origin/main em checkout isolado. Incluidos somente os documentos em docs/comercial e este diario obrigatorio, para commit e envio autorizado ao GitHub. Nenhum codigo de autenticacao foi incorporado.

## Feito

- Copiados integralmente docs/comercial/analise-de-rentabilidade-fornex.pdf e docs/comercial/proposta-preliminar-fornex.pdf, sem alteracao editorial.
- Branch criada a partir de af43561, sem merge, rebase ou reescrita. Este diario acompanha o commit dos documentos.
- Checkout original da autenticacao e suas duas alteracoes locais anteriores preservados; nenhum outro arquivo foi incluido.

## Verificado (e como)

- Windows local: git fetch origin, branch/status/log e base remota conferidos. Git worktree separado criado em pasta temporaria para nao transportar commits ou arquivos pendentes da autenticacao.
- PDFs abertos por PyMuPDF temporario: 20 e 8 paginas; varredura sem padroes de chaves privadas ou tokens de provedor. SHA-256 confirmou identidade de cada copia com o original em Downloads.
- Validador do diario, git diff --cached --check e lista dos arquivos do commit conferidos. Comparacao com origin/main limitada aos dois PDFs e ao diario; codigo do site sem diferenca. Envio ao remoto conferido ao final.

## Não verificado

- Nao houve auditoria financeira nova, correcao das premissas ou edicao dos PDFs. Sem testes de produto, pois esta entrega contem apenas documentos. Nenhum PR, merge, deploy ou alteracao de banco.

## Decisões e motivo

- Branch exclusiva docs/rentabilidade-proposta baseada na main para permitir PR independente da autenticacao. Nomes de arquivos sem espacos em docs/comercial; conteudo original preservado.
- As pendencias herdadas abaixo sao contexto de outras tarefas, nao mudancas incluidas nesta branch.

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

- [x] Documentos separados da branch de autenticacao: inclusao anterior desfeita em 0aecb1e; agora preparados em branch exclusiva a partir da main. (origem: 2026-11-17-anagmenezes)

## Armadilhas

- Nao comparar esta branch contra a de autenticacao: a base de revisao e main. O checkout aberto no IDE continua na autenticacao para preservar as alteracoes locais anteriores.
- Os PDFs sao documentos preliminares; publica-los nao equivale a validar ou aprovar os valores apresentados. Nao incluir configuracoes privadas ou dados pessoais no diario.

## Próximo passo sugerido

Abrir PR exclusivo de docs/rentabilidade-proposta para main e solicitar revisao da equipe, sem merge automatico.
