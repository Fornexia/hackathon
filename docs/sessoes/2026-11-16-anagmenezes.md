# 2026-11-16: anagmenezes

- **Quem:** AnagMenezes (Gabriella, via Codex)
- **Branch e commit de partida:** gpt/gabriella-autenticacao-site-2026-11-15 em b7dc44b
- **Máquina e ambiente:** Windows local, maquina bibis; PHP 8.2.35, Docker ativo, MariaDB descartavel de testes, Python da .venv, Composer e Edge.

## Resumo

Nova tarefa autorizada em duas entregas locais, sem push: a primeira implementa e-mails de qualquer dominio valido, estado de verificacao, verificacao de contas antigas logadas e proxies confiaveis, concluida no commit 3f61265 com 147 testes aprovados. Depois desse commit e com status limpo foi iniciada a segunda, login Google, incluida neste segundo commit local com 164 testes aprovados. A regra solicitada para Google e token validado e email_verified verdadeiro; a limitacao de autoridade sobre dominios externos foi documentada. Estes registros mais recentes substituem a restricao antiga a Gmail descrita no historico abaixo.

Implementado o login publico sobre a autenticacao PHP/MariaDB existente, na branch derivada da feat. O codigo anterior ja aceitava clientes; faltavam verificacao de endereco e recuperacao de senha. Novos cadastros exigem Gmail e verificacao, sem promover usuarios a admin. Commit 5b22ad2 criado e branch enviada ao origin por autorizacao da usuaria. Ativacao no ambiente atual ainda depende de configuracao privada de correio, cron e migracao autorizada.

Auditoria final solicitada depois da publicacao: a suite existente passou novamente, mas testes complementares encontraram cinco falhas tecnicas. A usuaria autorizou as correcoes, agora implementadas e verificadas com 143 testes aprovados, e depois autorizou o commit e push deste conjunto. A comparacao com main inclui o portfolio herdado; a decisao de escopo continua pendente. A usuaria abrira o Pull Request pelo GitHub.

## Feito

- Apos autorizacao explicita posterior, realizado push dos commits 3f61265 e 1ebc1f3 para origin na mesma branch. Nenhum PR, merge ou deploy executado. Este registro acompanha o envio em commit separado apenas de documentacao.

- Entrega 2 incluida neste segundo commit local: GIS nas duas abas do chat, configuracao opcional do Client ID, API Google com CSRF e limites, tokeninfo via HTTPS/TLS sem redirecionar e com tempo/tamanho limitados. Conferidas assinatura pelo servico e claims no PHP; sem Client ID, rota 404 e botao oculto. Validacao nova em lib_google.php, sem novas dependencias Composer.
- Migracao acrescenta sub unico sensivel a maiusculas e permite hash nulo sem alterar nenhum valor existente. Conta nova Google recebe usuario comum; existente verificada preserva senha e plano; nao verificada perde senha, sessoes e tokens anteriores ao vinculo. Administrador sempre recusado por Google. Identidade usa sub estavel, com travas e rejeicao de vinculos conflitantes. Login por senha e redefinicao recusam hash nulo.
- Criados testes RSA/tokeninfo locais e GIS simulado em navegador. Documentados configuracao, origens localhost, CSP, limites do tokeninfo e do vinculo de enderecos externos, sem implementar desafio adicional nao pedido. Nenhum arquivo de deploy, site institucional ou configuracao privada modificado.

- Entrega 1 implementada: cadastro aceita formato valido ate 190 caracteres; login e me expõem email_verificado; Minha conta mostra o estado e solicita verificacao pelo endereco da sessao com login, CSRF, limite e fila existentes. Confirmacao preserva senha, papel e regra de compatibilidade das contas antigas. TRUSTED_PROXIES usa IPs exatos, vazio por padrao, e so confia no ultimo IP valido do cabecalho quando o remetente esta configurado.
- Atualizados textos, modelo publico de configuracao, README e guias de autenticacao e Windows/Linux. Acrescentados quatro testes em site/dev/test_auth_ajustes.py. Nenhuma alteracao em site-institucional, api da raiz, alertas, consulta ou configuracoes privadas. Entrega 2 continua pendente; nao houve push, PR ou deploy nesta tarefa.

- Analisada a proposta de duas novas entregas de autenticacao, sem iniciar implementacao: liberar dominios validos, expor verificacao, verificacao de conta antiga logada e proxies confiaveis; depois login Google separado. Base atual 37e6396. Identificadas decisoes de seguranca sobre vinculacao por dominio externo e validador de token; nenhuma alteracao em codigo, banco, dependencias ou configuracoes privadas nesta analise.

- Apos autorizacao, corrigidos cinco achados da auditoria: backup remoto com helper validado, limite concorrente de login por IP/endereco, retencao privada das sessoes, isolamento do teste de prova e login do benchmark com contas existentes. Correcoes incluidas no commit desta etapa, com envio autorizado. Sem merge ou deploy.
- Acrescentados oito testes em site/dev/test_auth_regressoes.py ao executor isolado. Atualizados modelo publico de configuracao, ignorados, guia Windows/Linux e docs/AUTENTICACAO.md. Inventario e proposta de separacao dos 43 arquivos institucionais em docs/REVISAO-AUTENTICACAO-PR.md; nenhum desses arquivos foi reorganizado ou alterado.

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

- Envio autorizado, Windows local: git status limpo antes do push; HEAD tinha dois commits a frente e nenhum atras da referencia remota. `git push origin gpt/gabriella-autenticacao-site-2026-11-15` concluiu o envio de 37e6396 a 1ebc1f3; `git rev-list --left-right --count HEAD...origin/gpt/gabriella-autenticacao-site-2026-11-15` retornou 0/0. Nao repetidos testes de produto, pois o codigo nao mudou desde os 164 aprovados. Diario validado novamente.

- Entrega 2 final, Windows bibis, PHP 8.2.35, Python da .venv, Edge e MariaDB 10.11 descartavel: `.venv\Scripts\python -X utf8 site/dev/test_auth.py`, com Playwright temporario, aprovou 164 testes em 602,878 segundos, zero falhas e zero pulados. Inclui 17 casos Google, navegador GIS simulado em duas abas a 390 px e todas as regressoes anteriores. Bancos e configuracoes temporarios removidos pelo executor, sem rede externa para Google, SMTP ou WhatsApp.
- Depois de reforcar o teste para alterar somente a assinatura e manter claims validas, `.venv\Scripts\python -X utf8 site/dev/test_auth.py test_auth_google.TestGoogle.test_assinatura_adulterada_e_credencial_malformada_recusadas` aprovou um caso em 4,689 segundos. Nenhum codigo de produto mudou depois do inicio da suite completa. `php -l` em seis PHP, `node --check` nos dois JavaScript do produto e no teste de interface, py_compile, validador do diario e git diff --check aprovados. Git ignore protege configuracao, sessoes, vendor e .env. Revisao dos caminhos alterados sem credenciais reais nos padroes examinados; nenhum arquivo privado ou fora do escopo.

- Entrega 2 parcial anterior: executor descartavel `.venv\Scripts\python -X utf8 site/dev/test_auth.py test_auth_google` aprovou os primeiros 13 testes em 53,467 segundos, sem chamadas externas. Essa rodada foi complementada pela suite completa acima; nenhuma delas comprova o GIS real.

- Entrega 1, Windows local bibis, PHP 8.2.35, Python da .venv, Edge e MariaDB 10.11 descartavel: `.venv\Scripts\python -X utf8 site/dev/test_auth.py`, com Playwright temporario, aprovou 147 testes em 360,313 segundos, zero falhas e zero pulados. Inclui os quatro novos casos, autenticacao, permissoes, sessoes, consultas, planos, worker/WhatsApp simulado, provas, SMTP TLS local e navegador. Uma rodada anterior aprovou 164 execucoes por descobrir novamente 17 testes importados; corrigida somente a importacao no novo modulo e repetida a suite completa sem duplicacoes.
- `php -l` nos cinco PHP alterados, `node --check` nos tres JavaScript alterados, validador do diario e `git diff --check` aprovados. Revisao dos 17 caminhos alterados nao encontrou credenciais reais nos padroes examinados nem arquivos privados/fora do escopo. Nao executados deploy, migracao em bancos existentes ou envio externo. Entrega 1 preparada para commit local autorizado; Google ainda nao iniciado.

- Revisao estatica da autenticacao e dos testes, com consulta a documentacao oficial do Google: lock possui apenas PHPMailer como pacote de produto, sem validador JWT instalado; tokeninfo e indicado para desenvolvimento/depuracao. Google recomenda desafio adicional para enderecos externos sem dominio hospedado. `git fetch origin` sem integracao confirmou branch sincronizada; comparacao com origin/feat/portabilidade-windows-linux tem 33 arquivos e nenhum em site-institucional. Nao foram repetidos testes; os 143 aprovados pertencem a entrega anterior e nao validam Google nem os quatro ajustes propostos.

- Atualizacao solicitada apos o push: `git pull --ff-only` no Windows retornou `Already up to date`; HEAD e origin/gpt/gabriella-autenticacao-site-2026-11-15 em 37e6396, diferenca 0/0. A main remota permanece em af43561 e nao acrescenta conteudo desde a base comum; nenhum merge necessario. Referencias das demais branches foram atualizadas, sem incorpora-las. Nenhum teste repetido, pois o codigo nao mudou. Apenas este registro local foi atualizado, sem novo commit/push.

- Antes do envio autorizado, `git fetch origin` e `git rev-list --left-right --count HEAD...origin/gpt/gabriella-autenticacao-site-2026-11-15` no Windows confirmaram 0/0; nenhum merge necessario. Indice contem apenas os 15 arquivos revisados; `git diff --cached --check` aprovado.

- Execucao final no Windows: `.venv\Scripts\python -X utf8 site/dev/test_auth.py`, com modulo Playwright temporario informado no ambiente: 143 testes aprovados em 321,308 segundos, zero falhas e zero pulados. Inclui autenticacao, perfis, planos, consultas, worker/WhatsApp simulado, provas, SMTP TLS local, navegador e oito regressoes. Todos os bancos eram descartaveis.

- Windows local, PHP 8.2.35 e MariaDB 10.11 descartavel: `.venv\Scripts\python -X utf8 site/dev/test_auth.py test_auth_regressoes` aprovou oito casos. A primeira tentativa teve tres falhas de transporte CRLF no executor de shell, corrigidas usando entrada binaria LF antes da reexecucao aprovada.
- Copia temporaria dos arquivos versionados com alteracoes atuais, sem configuracao privada nem .env: executor isolado com `test_prova.TestSemSegredo` aprovou um teste. Nenhum acesso ao banco atual.
- Sintaxe PHP, Bash e Python aprovada; `composer validate --no-check-publish` valido (aviso preexistente de licenca), `composer check-platform-reqs --no-dev` aprovado. Varredura de 76 caminhos envolvidos nao detectou credenciais reais; nenhuma configuracao privada/dependencia/sessao versionada. `git check-ignore` confirma protecao dos novos caminhos privados.
- `git fetch origin` sem merge: main permanece em af43561, sem diferenca de conteudo desde a base comum 584efc2; branch de trabalho permanece em f255342 antes do commit proposto. Arquivos institucionais seguem intactos.

- Windows local, maquina bibis, PHP 8.2.35, Python da .venv, Docker/MariaDB 10.11 e Edge. Leitura das instrucoes e diarios; git status e log conferidos. git pull buscou a origem, mas a branch continua sem upstream por decisao da preparacao anterior; nenhum merge foi realizado.
- python site/dev/test_auth.py: rodada inicial com 129 testes aprovados em banco descartavel, cobrindo autenticacao, consultas, planos, telefones/worker e exportacao de provas, sem servicos pagos.
- Caso de interface executado com Playwright e Edge: cadastro, verificacao, login de cliente, bloqueio de administracao, recuperacao, invalidacao de sessao, logout e largura movel passaram. Capturas em logs/auth-ui inspecionadas visualmente.
- Testes adicionais de configuracao ausente, cookie Secure em producao e recusa de captura em producao passaram. Simulador SMTP inicialmente respondeu incorretamente a AUTH PLAIN; corrigido o simulador, o caso SMTP local com certificado TLS verificado e autenticacao passou.
- composer install --no-dev --prefer-source instalou PHPMailer fixado no lock; composer audit --no-dev --locked sem alertas publicados. php -l nos arquivos PHP alterados e node --check nos scripts novos/alterados sem erros. bash -n site/deploy.sh, py_compile e git diff --check sem erros.
- Rodada final em 16/11/2026, Windows bibis: .venv\Scripts\python -X utf8 site/dev/test_auth.py, com modulo Playwright temporario configurado no ambiente, concluiu 135 testes em 463,076 segundos, todos aprovados e sem pulos. Incluiu SMTP local com TLS, preservacao de admin apos recuperacao, prazo absoluto de sessao e interface no Edge, alem das regressoes completas de API e provas. Conteiner e arquivos privados temporarios encerrados pelo executor.
- Diario validado com .venv\Scripts\python -X utf8 docs/sessoes/validar.py docs/sessoes/2026-11-16-anagmenezes.md. git diff --check sem erros; stashes anteriores preservados.
- PDF gerado no Windows bibis com ReportLab e bibliotecas temporarias fora das dependencias do produto; pypdf confirmou uma pagina e os trechos esperados. Renderizado com PyMuPDF e inspecionado visualmente, sem cortes ou sobreposicoes. Script e imagem intermediarios removidos apos a conferencia.
- Entrega em 16/11/2026, Windows bibis: git fetch origin, validacao dos dois diarios e git diff --cached --check concluidos. Hook executado no commit 5b22ad2; git push --set-upstream origin gpt/gabriella-autenticacao-site-2026-11-15 criou a branch remota com sucesso. Nenhum codigo alterado desde a rodada de 135 testes; nesta entrega apenas diario revisado e espaco final removido.
- Auditoria em 16/11/2026, Windows bibis: git fetch origin, status/log/diff conferidos em HEAD f255342 e origin/main af43561. Usado fetch em vez de pull para respeitar a proibicao de merge. Sao 71 arquivos no diff de PR: 28 da autenticacao e 43 do site institucional herdado; main tem o mesmo conteudo do ancestral comum 584efc2, sem conflito de conteudo identificado. Nenhum merge executado.
- Reexecucao de .venv\Scripts\python -X utf8 site/dev/test_auth.py com Playwright temporario: 135 testes aprovados, sem pulos, em 449,347 segundos. Somente conteineres e bancos descartaveis usados.
- Oito casos complementares temporarios, fora do repositorio: quatro aprovados, tres falhas de assercao e um erro em clone limpo. Limite de cinco falhas de login ultrapassado por seis requisicoes concorrentes em tres rodadas. GC do PHP com retencao de 1440 segundos removeu sessao com 25 minutos, antes dos 30 configurados. bench/carga.py nao entrou mesmo com credenciais legadas validas. test_prova.py leu caminho privado fixo e falhou quando esse arquivo nao existia na copia limpa.
- Casos complementares aprovados: duas migracoes preservaram os hashes do conteudo de sete tabelas com contas, planos, assinatura, telefone, pergunta e eventos; tres emissores concorrentes enviaram uma unica mensagem; SMTP local indisponivel preservou a fila e o bloqueio da conta pendente; redefinicao expirou corretamente e apenas um de tres consumos concorrentes foi aceito.
- Copia temporaria dos arquivos versionados, sem configuracao privada: npm ci com scripts desabilitados, npm run build e tsc aprovados. O tsconfig do portfolio inclui apenas src e vite.config.ts, deixando componentes na raiz fora da checagem de tipos. npm audit e composer audit sem alertas publicados. composer validate e check-platform-reqs aprovados, com aviso de licenca nao declarada. PHP, JavaScript e Bash sem erros de sintaxe. Diff de PR tem dois avisos de linha vazia final em arquivos herdados do portfolio.
- Reproducao local isolada do pipeline de backup: um mysqldump ficticio que escreveu CREATE TABLE e terminou com erro foi aceito sem pipefail; com pipefail foi recusado. Nao foi executado o deploy.sh nem qualquer comando remoto de deploy. O script tambem nao passa DB_PORT ao dump e bloqueia banco vazio antes do setup.
- Varredura dos arquivos alterados nao encontrou credenciais reais; candidatos detectados no teste de prova eram sentinelas ficticias ja existentes. .gitignore protege configuracoes privadas, vendor, capturas e dependencias locais. Nenhum arquivo privado foi modificado; um teste existente leu a configuracao local internamente, lacuna registrada acima.

## Não verificado

- GIS real, popup, consentimento, Client ID e origens no Google Cloud nao configurados nem homologados. Tokeninfo real nao chamado. Verificacao de conta antiga na pagina Minha conta validada por API e sintaxe, sem exercicio especifico desse botao em navegador. Configuracao de proxy e endereco corporativo nao homologados na hospedagem real.

- Sem entrega de correio real, credenciais SMTP reais, cron em hospedagem, deploy Hostinger, banco remoto ou migracao sobre a base atual. Nao houve acesso autenticado ao site publicado, uso de modelo pago nem envio WhatsApp.
- Sem homologacao em Linux, aparelho fisico ou leitor de tela. Empacotamento do deploy foi revisado e teve sintaxe conferida, sem execucao remota.
- Pendencias herdadas abaixo nao foram revalidadas. O envio da branch ao Git nao executa merge nem deploy.

## Decisões e motivo

- Google segue a regra expressa da tarefa: email_verified verdadeiro apos validar o token. Registrada a recomendacao do Google de desafio adicional para dominio externo sem Workspace; nenhum fluxo adicional ou restricao de dominio foi acrescentado. Usado tokeninfo, opcao autorizada, para manter lock enxuto sem implementar verificador JWT proprio. Documentado que o Google recomenda biblioteca para producao e que ha dependencia de rede e disponibilidade a cada login.

- Reaproveitar PHP puro, MariaDB, cookie de sessao, CSRF e verificacao de papeis existentes. Nao foi encontrada uma restricao de login apenas para admin no codigo. A quantidade/estado de contas no banco remoto nao foi comprovada.
- Exigir verificacao apenas de novos cadastros, mantendo contas antigas e seus hashes/papeis. A compatibilidade nao informa falsamente que os enderecos antigos foram verificados.
- Fila cifrada separa o envio SMTP da resposta da API sem armazenar o segredo do link em texto aberto. Captura de mensagens so funciona em ambiente de teste e banco com prefixo reservado.
- Isolar testes destrutivos da base compartilhada e preservar os stashes anteriores sem aplica-los. Nao modificar arquivos privados de configuracao. A publicacao da branch ao Git foi autorizada posteriormente; o deploy continua pendente.

## Em aberto (por prioridade)

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

- [x] Duas entregas autorizadas implementadas separadamente: ajustes no commit 3f61265, com 147 testes, depois Google neste segundo commit local, com 164 testes e nenhum pulo. Sem publicacao ou alteracao de bancos existentes. (origem: 2026-11-16-anagmenezes)

- [x] Cinco achados da auditoria corrigidos com autorizacao: backup, limite concorrente, retencao de sessoes, teste de prova isolado e benchmark. Oito regressoes e suite completa de 143 casos aprovadas. Commit e push autorizados posteriormente pela usuaria. (origem: 2026-11-16-anagmenezes)
- [x] Backup herdado da feat corrigido: falhas propagadas, porta respeitada, primeira instalacao distinguida e restauracao validada em banco descartavel. Sem executar deploy. (origem: 2026-11-15-anagmenezes)

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

Usuaria pode abrir o PR pelo GitHub; sugerida a base feat/portabilidade-windows-linux, que ja inclui o site institucional. Push autorizado concluido; nenhuma abertura de PR, merge ou publicacao do site foi realizada. Homologacao real e configuracoes privadas continuam pendentes.
