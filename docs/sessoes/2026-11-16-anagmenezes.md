# 2026-11-16: anagmenezes

- **Quem:** AnagMenezes (Gabriella, via Codex)
- **Branch e commit de partida:** gpt/gabriella-autenticacao-site-2026-11-15 em b7dc44b
- **Máquina e ambiente:** Windows local, maquina bibis; PHP 8.2.35, Docker ativo, MariaDB descartavel de testes, Python da .venv, Composer e Edge.

## Resumo

Implementado o login publico sobre a autenticacao PHP/MariaDB existente, na branch derivada da feat. O codigo anterior ja aceitava clientes; faltavam verificacao de endereco e recuperacao de senha. Novos cadastros exigem Gmail e verificacao, sem promover usuarios a admin. Commit 5b22ad2 criado e branch enviada ao origin por autorizacao da usuaria. Ativacao no ambiente atual ainda depende de configuracao privada de correio, cron e migracao autorizada.

## Feito

- API: cadastro pendente, reenvio/verificacao, recuperacao/redefinicao com tokens temporarios de uso unico, CSRF e limites atomicos. Senhas novas com Argon2id e confirmacao.
- Sessoes: versao por conta para invalidar todos os acessos apos redefinir a senha, expiração por inatividade e prazo total, cookie removido no logout e permissões consultadas no backend.
- Migracao aditiva em site/migrar-autenticacao.php, repetivel e sem redefinir senhas, papeis ou relacoes. Contas anteriores permanecem compativeis, sem marcar enderecos como verificados.
- Fila de correio cifrada e envio CLI por PHPMailer com TLS, tentativas e reserva para concorrencia. Composer e lock adicionados; vendor ignorado. SMTP nao configurado nem usado com destinatarios externos.
- Telas existentes reaproveitadas; confirmacao de senha, estado de verificacao, acesso.html para links e recuperacao. Empacotamento do deploy inclui dependencias e migracao, sem executar publicacao.
- Testes isolados criam e removem seu proprio conteiner, banco, configuracao e sessoes. Suites antigas passaram a recusar a base compartilhada. Diagnostico verificar_login.py usa o mesmo executor seguro.
- docs/AUTENTICACAO.md, README e guia local documentam diagnostico, contrato, compatibilidade, configuracao e ativacao.
- A pedido da usuaria, gerado output/pdf/fornex-autenticacao-resumo.pdf: uma pagina simples sobre o que foi feito, funcionamento, finalidade, testes e pendencias para ativacao. Sem alterar o codigo da autenticacao nesta etapa.
- Depois, a pedido da usuaria, excluido somente o PDF de resumo gerado. Test-Path confirmou a ausencia do arquivo; codigo de autenticacao preservado.
- Entregue a implementacao no commit 5b22ad2, com 28 arquivos, e realizado push da branch gpt/gabriella-autenticacao-site-2026-11-15 para origin, com upstream configurado. Arquivos privados, dependencias instaladas, capturas de testes e stashes anteriores ficaram fora do commit.

## Verificado (e como)

- Windows local, maquina bibis, PHP 8.2.35, Python da .venv, Docker/MariaDB 10.11 e Edge. Leitura das instrucoes e diarios; git status e log conferidos. git pull buscou a origem, mas a branch continua sem upstream por decisao da preparacao anterior; nenhum merge foi realizado.
- python site/dev/test_auth.py: rodada inicial com 129 testes aprovados em banco descartavel, cobrindo autenticacao, consultas, planos, telefones/worker e exportacao de provas, sem servicos pagos.
- Caso de interface executado com Playwright e Edge: cadastro, verificacao, login de cliente, bloqueio de administracao, recuperacao, invalidacao de sessao, logout e largura movel passaram. Capturas em logs/auth-ui inspecionadas visualmente.
- Testes adicionais de configuracao ausente, cookie Secure em producao e recusa de captura em producao passaram. Simulador SMTP inicialmente respondeu incorretamente a AUTH PLAIN; corrigido o simulador, o caso SMTP local com certificado TLS verificado e autenticacao passou.
- composer install --no-dev --prefer-source instalou PHPMailer fixado no lock; composer audit --no-dev --locked sem alertas publicados. php -l nos arquivos PHP alterados e node --check nos scripts novos/alterados sem erros. bash -n site/deploy.sh, py_compile e git diff --check sem erros.
- Rodada final em 16/11/2026, Windows bibis: .venv\Scripts\python -X utf8 site/dev/test_auth.py, com modulo Playwright temporario configurado no ambiente, concluiu 135 testes em 463,076 segundos, todos aprovados e sem pulos. Incluiu SMTP local com TLS, preservacao de admin apos recuperacao, prazo absoluto de sessao e interface no Edge, alem das regressoes completas de API e provas. Conteiner e arquivos privados temporarios encerrados pelo executor.
- Diario validado com .venv\Scripts\python -X utf8 docs/sessoes/validar.py docs/sessoes/2026-11-16-anagmenezes.md. git diff --check sem erros; stashes anteriores preservados.
- PDF gerado no Windows bibis com ReportLab e bibliotecas temporarias fora das dependencias do produto; pypdf confirmou uma pagina e os trechos esperados. Renderizado com PyMuPDF e inspecionado visualmente, sem cortes ou sobreposicoes. Script e imagem intermediarios removidos apos a conferencia.
- Entrega em 16/11/2026, Windows bibis: git fetch origin, validacao dos dois diarios e git diff --cached --check concluidos. Hook executado no commit 5b22ad2; git push --set-upstream origin gpt/gabriella-autenticacao-site-2026-11-15 criou a branch remota com sucesso. Nenhum codigo alterado desde a rodada de 135 testes; nesta entrega apenas diario revisado e espaco final removido.

## Não verificado

- Sem entrega de correio real, credenciais SMTP reais, cron em hospedagem, deploy Hostinger, banco remoto ou migracao sobre a base atual. Nao houve acesso autenticado ao site publicado, uso de modelo pago nem envio WhatsApp.
- Sem homologacao em Linux, aparelho fisico ou leitor de tela. Empacotamento do deploy foi revisado e teve sintaxe conferida, sem execucao remota.
- Pendencias herdadas abaixo nao foram revalidadas. O envio da branch ao Git nao executa merge nem deploy.

## Decisões e motivo

- Reaproveitar PHP puro, MariaDB, cookie de sessao, CSRF e verificacao de papeis existentes. Nao foi encontrada uma restricao de login apenas para admin no codigo. A quantidade/estado de contas no banco remoto nao foi comprovada.
- Exigir verificacao apenas de novos cadastros, mantendo contas antigas e seus hashes/papeis. A compatibilidade nao informa falsamente que os enderecos antigos foram verificados.
- Fila cifrada separa o envio SMTP da resposta da API sem armazenar o segredo do link em texto aberto. Captura de mensagens so funciona em ambiente de teste e banco com prefixo reservado.
- Isolar testes destrutivos da base compartilhada e preservar os stashes anteriores sem aplica-los. Nao modificar arquivos privados de configuracao. A publicacao da branch ao Git foi autorizada posteriormente; o deploy continua pendente.

## Em aberto (por prioridade)

- [ ] Para ativar o login publico: configurar SMTP, origem HTTPS, chave privada da fila e cron; aplicar a migracao apos backup no ambiente escolhido e homologar entrega real e perfis. Nenhuma dessas configuracoes foi alterada nesta sessao. (origem: 2026-11-16-anagmenezes)


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

- [x] Analise e implementacao do login publico na branch de autenticacao, preservando contas antigas e papeis, com 135 testes reais aprovados em ambiente isolado. (origem: 2026-11-15-anagmenezes)
- [x] Preparacao da branch de autenticacao concluida a partir da feat atualizada. (origem: 2026-11-15-anagmenezes)
- [x] Push anterior concluido em e387ca2 na branch de CI; nao altera a origem desta nova branch. (origem: 2026-11-15-anagmenezes)
- [x] Portfolio da Rafaella recebido pela feat em subpasta (9a9d6b2); links da tela de teste atualizados em dea3197 e b7dc44b. O conflito da simulacao de merge direto nao se aplica a essa importacao ja feita. (origem: 2026-11-15-anagmenezes)

## Armadilhas

- A branch acompanha origin/gpt/gabriella-autenticacao-site-2026-11-15. Os stashes anteriores nao foram aplicados. O push nao publica o site nem aplica migracao no banco atual.
- A API atualizada exige executar a migracao aditiva antes de publica-la. Nao usar setup com argumentos do admin para uma atualizacao comum: o setup redefine a conta administrativa e aplica outras regras preexistentes.
- Sem configuracao de correio, novos cadastros e solicitacoes de links retornam indisponibilidade; contas antigas continuam podendo entrar. Configuracao de SMTP sem cron nao comprova envio.
- Nao executar suites antigas contra a base atual. Usar site/dev/test_auth.py, que cria e remove os recursos descartaveis.
- Windows local sem ZIP/unzip precisou de Composer com prefer-source. Playwright temporario foi instalado fora das dependencias do produto; capturas de teste ficam ignoradas em logs.
- Nao colocar credenciais, conteudo de configuracao privada ou dados pessoais neste diario.

## Próximo passo sugerido

Revisar a branch publicada e configurar o correio e a migracao para homologacao do login publico no ambiente escolhido, mantendo a separacao entre cliente e administrador.
