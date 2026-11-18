# Autenticação pública do FORNEX

## Diagnóstico da base b7dc44b

O login PHP consultava `usuarios` pelo e-mail e verificava a senha, sem exigir `papel=admin`.
O cadastro já inseria usuários com o perfil padrão `usuario` e iniciava uma sessão imediatamente.
`setup.php` provisiona o administrador explicitamente pela linha de comando; ele não é um cadastro público.
As rotas `/api/admin/*` restringem o acesso ao administrador. Consultas e telefones exigem conta e,
para criar recursos, plano ativo. A tela do chat já tenta ativar o plano de demonstração.

Portanto, não foi encontrada no código uma regra que permita somente o administrador realizar login.
A existência de apenas uma conta utilizável no ambiente publicado não foi comprovada por consulta ao banco remoto.
O administrador do protótipo React em `site-institucional/` usa armazenamento do navegador e não autentica na API PHP.

As lacunas para abrir o cadastro ao público eram: ausência de confirmação de endereço, recuperação de senha,
reenvio de verificação, configuração SMTP e invalidação das sessões depois de trocar a senha.

## Comportamento implementado

- Novas contas: qualquer e-mail válido com até 190 caracteres, pessoal ou corporativo, senha exclusiva do FORNEX de 15 a 128 caracteres e confirmação.
  No fluxo de senha, a senha do provedor de e-mail não é solicitada. Hash Argon2id, com espaços, Unicode e caracteres especiais.
  O acesso alternativo com Google está descrito abaixo e não exige criar senha do FORNEX.
- O cadastro retorna `202` com mensagem genérica, inclusive para endereço já cadastrado. Não altera a conta existente.
  Não inicia sessão nem ativa plano antes da confirmação. O perfil é explicitamente `usuario`.
- Verificação: link de 24 horas, confirmação por POST com CSRF. Reenvio invalida o link anterior.
  Depois de confirmar, a pessoa entra com a senha criada e segue o fluxo de plano e consultas existente.
- Recuperação: resposta genérica, link de 30 minutos, confirmação da nova senha. Não inicia sessão automaticamente.
  Trocar a senha incrementa a versão de autenticação e invalida todas as sessões anteriores da conta.
- Tokens: 32 bytes aleatórios, somente SHA-256 no registro de autenticação, finalidade separada, expiração e uso único.
  A confirmação concorrente é serializada por bloqueio da conta e do token.
- O segredo do link fica no fragmento de `acesso.html`, que o remove da barra de endereços. GET não consome o token.
  Essa página só carrega recursos locais e usa CSP e `no-referrer`.
- As sessões PHP continuam independentes por navegador, com cookie `hsid`, HttpOnly, SameSite=Lax,
  Secure em produção e troca de identificador ao entrar. Logout remove o cookie e a sessão.
  Expiram após 30 minutos sem interação ou 12 horas desde o login. O polling do chat não prolonga a sessão.
  O armazenamento usa diretório exclusivo privado (`site/sessoes` por padrão), com retenção do coletor PHP
  alinhada ao maior prazo configurado. `AUTH_SESSION_PATH` permite escolher outro diretório absoluto privado
  e gravável, exclusivo desta aplicação. A adoção desse diretório exige um novo login das sessões antigas;
  não modifica contas, senhas ou permissões. Não incluir essa pasta em artefatos públicos ou no Git.
- As rotas privadas continuam verificando a conta no backend; a administração verifica o papel em cada requisição.
  Limites de login existentes permanecem. Cadastro e solicitações de e-mail têm contadores atômicos por IP/endereço.
  No login, travas MariaDB por IP e e-mail serializam contagem, verificação e registro da tentativa entre processos.
  Os limites continuam sendo 5 falhas por par, 20 por IP e 30 por endereço em 15 minutos. As travas são liberadas
  antes da resposta; indisponibilidade da trava recusa a tentativa com 429, sem verificar a senha.

## Compatibilidade e migração

`site/migrar-autenticacao.php` acrescenta quatro colunas a `usuarios` e cria as tabelas `auth_tokens`,
`auth_limites` e `auth_emails`. Pode ser executada novamente. Não exclui contas nem muda IDs, senhas,
papéis, planos, telefones, assinaturas, consultas ou provas. DDL no MariaDB não é transacional:
faça backup antes; uma execução interrompida pode ser retomada com o mesmo comando.

A quarta coluna, `google_sub VARCHAR(64) NULL`, tem índice único e comparação sensível a maiúsculas.
`senha_hash` passa a aceitar `NULL` para contas só-Google. A migração não anula nem recalcula nenhum hash
existente: esse campo só é anulado pelo fluxo de vínculo de conta ainda não verificada descrito abaixo.

Contas anteriores ficam com `email_verificacao_exigida=0` e `email_verificado_em=NULL`.
Continuam entrando com seus endereços e hashes anteriores, inclusive o administrador e clientes com outro domínio.
Isso é compatibilidade com as contas existentes, **não** uma declaração de que esses endereços foram verificados.
Novos cadastros recebem obrigatoriamente `email_verificacao_exigida=1`. Nenhuma exceção depende do papel.
Recuperar a senha de uma conta antiga mantém seu papel e passa a usar Argon2id.

`usuario.email_verificado`, retornado por `/api/me` e pelo login, é booleano e representa exclusivamente
`email_verificado_em IS NOT NULL`. Contas antigas compatíveis podem retornar `false` e continuar entrando.
Na página Minha conta, uma conta logada pode solicitar "Verificar agora". A rota usa somente o endereço
da sessão; ignora um endereço enviado no corpo. Confirmar o link não altera papel, senha ou
`email_verificacao_exigida`. Uma conta já verificada recebe a resposta genérica sem novo envio.

Para atualizar um banco existente, use apenas:

```bash
php site/migrar-autenticacao.php
```

Não use `setup.php` com argumentos do administrador para uma atualização comum: esse comando também redefine
o administrador e atualiza planos/telefones segundo regras anteriores do projeto. O setup continua disponível
para a instalação inicial e chama a migração aditiva.

## Configuração e envio

PHP 8.2+, `pdo_mysql`, `mbstring`, `openssl` e suporte a Argon2id. Instale a dependência SMTP fixada no lock:

```bash
cd site
composer install --no-dev --prefer-dist
```

No Windows sem ZIP/unzip, use `--prefer-source`. O `vendor/` fica fora do `public_html` e é ignorado pelo Git.

Defina as opções abaixo no arquivo privado `site/hackathon-config.php` ou no ambiente do processo PHP/cron.
O modelo está em `site/hackathon-config.exemplo.php`. O PHP não carrega o `.env` automaticamente;
`deploy.sh` o carrega e gera as constantes fora do diretório público.

| Opção | Uso |
|---|---|
| `APP_URL` | Origem HTTPS fixa, sem caminho, query ou fragmento, por exemplo `https://seu-dominio.example` |
| `SMTP_HOST`, `SMTP_PORT` | Servidor SMTP; porta padrão 587 |
| `SMTP_SECURITY` | `tls` para STARTTLS ou `ssl` para TLS implícito; certificados são verificados |
| `SMTP_USER`, `SMTP_PASS` | Credenciais do provedor de envio; sem exposição ao navegador |
| `MAIL_FROM`, `MAIL_FROM_NAME` | Remetente autorizado pelo provedor e nome de exibição |
| `AUTH_MAIL_KEY` | Base64 de 32 bytes aleatórios, usada para cifrar a fila de mensagens |
| `AUTH_IDLE_SECONDS`, `AUTH_MAX_SECONDS` | Opcionais; padrões 1800 e 43200 segundos |
| `AUTH_SESSION_PATH` | Opcional; diretório privado exclusivo e gravável, fora de `public_html` |
| `TRUSTED_PROXIES` | Opcional; lista de IPs exatos, padrão vazio. Constante PHP como array ou ambiente com IPs separados por vírgula |
| `GOOGLE_CLIENT_ID` | Opcional; Client ID de um aplicativo Web do Google. Vazio oculta o botão e faz a rota Google retornar 404 |

Sem `TRUSTED_PROXIES`, o IP é sempre `REMOTE_ADDR`. Só para um remetente expressamente listado se usa
o último IP válido, da direita para a esquerda, em `X-Forwarded-For`; sem IP válido mantém-se o remetente.
Aceita IPv4 e IPv6, não CIDR nem curingas. O proxy confiável deve acrescentar corretamente o endereço
do par que o acessa: cabeçalhos preservados sem saneamento podem permitir falsificação. Em uma cadeia
de vários proxies, esse critério pode identificar o proxy anterior; configure conforme a topologia real.

Gere `AUTH_MAIL_KEY` com um gerenciador de segredos ou `base64_encode(random_bytes(32))` no PHP.
Não coloque credenciais em commits, mensagens ou diário. Guarde a chave junto dos backups privados.
Uma rotação exige tratar a fila antiga, que não pode ser decifrada com a chave nova.

Agende fora do document root, a cada minuto, usando o mesmo ambiente/configuração do site:

```cron
* * * * * /caminho/php /caminho/site/enviar-emails.php >> /caminho/privado/email-status.log 2>&1
```

A API grava o token e a mensagem cifrada com AES-256-GCM na mesma transação; não aguarda SMTP.
O envio usa PHPMailer com autenticação e TLS, processa até 20 mensagens por execução e remove o conteúdo
após sucesso. Falhas têm até cinco tentativas com intervalo de cinco minutos e saída sem destinatários/tokens.
O cron deve ter alerta para saída diferente de zero; após corrigir a configuração, uma nova solicitação emite outro link.
Reservas de cinco minutos permitem vários processos sem envio simultâneo da mesma linha. Uma queda entre a aceitação
SMTP e a confirmação no banco pode reenviar a mensagem; o token continua utilizável uma única vez.
Tokens expirados há sete dias são removidos com sua fila. Links usados/expirados perdem o conteúdo cifrado.

Sem configuração de correio completa, cadastro e solicitações de links retornam 503 antes de criar uma conta.
O login existente permanece disponível. A validação local não comprova entrega: o cron deve estar rodando,
e o domínio remetente deve ser autorizado no provedor, com SPF/DKIM/DMARC conforme sua configuração.

`deploy.sh` inclui as dependências e os arquivos privados e executa a migração antes de trocar a API pública.
Exige as variáveis de correio antes de publicar. Não cria o cron automaticamente.
Nenhum deploy nem envio externo foi executado nesta implementação.

O backup de banco é executado por `site/backup-banco.sh` sob Bash remoto com `pipefail`, respeitando `DB_PORT`
(padrão 3306). Uma falha do dump ou da compressão impede publicar o arquivo final e interrompe o deploy.
O arquivo é temporário até validar gzip e quantidade de tabelas; depois é renomeado, com permissões privadas.
Banco vazio é recusado na atualização comum e permitido somente em `--setup`, para instalação inicial explícita.
A senha é transmitida no SSH pela entrada padrão e usada via ambiente. A hospedagem precisa disponibilizar
Bash, gzip, cliente MariaDB/MySQL e mariadb-dump/mysqldump. O teste local restaura um backup real em um segundo
banco descartável e compara os dados; a restauração na Hostinger ainda deve ser homologada antes do deploy.

Na Hostinger, selecione PHP 8.2+ com as extensões listadas, instale o `vendor` fora de `public_html` e configure
um cron com o caminho absoluto do PHP e de `enviar-emails.php`, usando a mesma configuração privada do site.
Use host, porta, autenticação e modalidade TLS fornecidos para a caixa remetente no painel do provedor.
Não copie credenciais para a documentação. Confira permissão do diretório de sessões, HTTPS, certificado SMTP,
remetente autorizado e entrega real. Configuração SMTP ausente/inválida impede o cadastro com 503;
uma indisponibilidade de rede posterior ao enfileiramento preserva a conta pendente e a mensagem para novas tentativas.

## Login com Google

O botão aparece nas abas Entrar e Criar conta apenas quando `GOOGLE_CLIENT_ID` está definido. O Google
Identity Services entrega um ID token ao callback JavaScript, enviado por POST como `{credential}` à API
com o CSRF do FORNEX. Não há fluxo OAuth por redirecionamento nem solicitação da senha do Google.
O Google cuida da credencial da conta Google; o FORNEX continua responsável pela conta local, perfil,
plano, sessão e autorização de cada recurso.

O servidor consulta exclusivamente `https://oauth2.googleapis.com/tokeninfo` por HTTPS com certificado
verificado, sem seguir redirecionamentos, prazo de cinco segundos e resposta limitada. Esse serviço valida
a assinatura; o PHP também exige `aud` igual ao Client ID configurado, `iss` permitido, `exp` futuro,
`email_verified=true`, endereço válido e `sub` de até 64 caracteres. Nunca aceita somente decodificar o JWT.
Tokens, respostas brutas e URLs com credenciais não são registrados pela aplicação. Falhas são 401 genérico;
CSRF inválido continua 403 e excesso de tentativas, 429. Há limites atômicos antes da chamada externa e
por endereço validado. PHP precisa de `allow_url_fopen` ativo, saída HTTPS liberada e cadeia de CAs válida.

Foi escolhida a opção tokeninfo autorizada na tarefa para manter o lock e evitar uma implementação própria
de verificação JWT. Há custo de rede a cada login e dependência da disponibilidade do Google. O Google
recomenda biblioteca de validação para produção e apresenta tokeninfo como ferramenta de desenvolvimento
e depuração; esta escolha e seus limites devem ser considerados na homologação.
[Referência oficial sobre validação](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

Regras de conta, aplicadas em transação com travas por e-mail/sub e índice único:

- Conta nova: papel `usuario`, e-mail verificado, `email_verificacao_exigida=0`, `google_sub` preenchido,
  sem senha local. Não recebe acesso administrativo.
- Conta existente verificada: vincula o sub sem mudar senha, versão, plano, papel ou exigência de verificação.
- Conta existente sem verificação: anula a senha local, incrementa `auth_versao`, inutiliza todos os tokens
  abertos e apaga o conteúdo de sua fila antes de marcar como verificada e entrar. As sessões antigas deixam
  de valer; a senha que alguém tenha cadastrado antes de comprovar o endereço não conserva acesso.
  `email_verificacao_exigida` permanece como estava. Essa ação acontece no login Google, nunca na migração.
- Administrador: recusado por Google com a mesma mensagem genérica, sem modificar a conta; continua por senha.
- Um sub já vinculado identifica a mesma conta em acessos posteriores. Não sobrescreve outro vínculo,
  não junta contas diferentes e não reescreve o endereço local quando o endereço do Google muda.
- Contas só-Google não entram por senha e não recebem link de redefinição. Mesmo um token anterior não pode
  criar senha em uma conta com hash nulo. A resposta da solicitação continua genérica.

Conforme a regra expressa da tarefa, um token validado com `email_verified=true` é aceito também para endereço
externo ao Gmail/Workspace. Limitação relevante: para endereço sem Gmail e sem `hd`, o Google informa que
a verificação pode ter ocorrido no passado e recomenda comprovação adicional de controle do endereço.
Esse desafio adicional não foi acrescentado ao escopo. O comportamento deve ser revisado pela equipe antes
da ativação pública, especialmente para vínculo com contas corporativas existentes.

Para configurar, sem colocar credenciais no repositório:

1. No Google Cloud Console, configure a tela de consentimento/branding do Google Auth Platform. Em modo de
   teste, autorize as contas de homologação conforme as opções do painel.
2. Crie um Client ID OAuth do tipo **Aplicativo da Web**. Em origens JavaScript autorizadas, inclua
   `http://localhost:8080` e a origem HTTPS exata da produção, sem caminho. Use `localhost`, não `127.0.0.1`.
3. Configure apenas `GOOGLE_CLIENT_ID` no ambiente do PHP ou no arquivo privado `site/hackathon-config.php`.
   O Client ID é público e é exposto por `/api/me`; nenhum Client Secret é necessário neste fluxo.
   O `.env` não é carregado pelo PHP, mas o `site/deploy.sh` lê `GOOGLE_CLIENT_ID` e `TRUSTED_PROXIES` (os dois opcionais) do
   `.env` do notebook, confere o formato antes de publicar (o Client ID precisa ser `NUMEROS-texto.apps.googleusercontent.com`;
   proxies, só endereços IP) e os grava no arquivo privado do servidor. Sem `GOOGLE_CLIENT_ID`, o botão fica oculto.
   **No computador local, abra o site por `http://localhost:8080`**, nunca por `127.0.0.1`: o Google só aceita `localhost`
   como origem. Com um Client ID inexistente, o botão aparece, mas o clique mostra "Error 401: invalid_client".
4. Homologue popup, origens, consentimento e entrega do token com contas reais antes de liberar ao público.
   Se a hospedagem configura COOP, confira `same-origin-allow-popups` conforme a documentação do GIS.

O botão é desenhado pelo Google e só aceita tema, formato e largura. O `chat.js` o redesenha no tema atual do site
(`outline` no claro, `filled_black` no escuro), na largura do cartão (até 400 px) e ao trocar de aba, janela ou tema.

`chat.html` não define CSP própria. Se a hospedagem impõe CSP, permita o script
`https://accounts.google.com/gsi/client`, frame e conexão `https://accounts.google.com/gsi/` e estilo
`https://accounts.google.com/gsi/style` nas respectivas diretivas, preservando as outras fontes locais
já necessárias. Não liberar curingas. `acesso.html` continua com sua CSP local restrita e não carrega GIS.
[Configuração oficial do Client ID e da página](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).

## Contrato da API

Todas as escritas abaixo exigem cookie de sessão e `X-CSRF-Token`, obtido em `GET /api/me`.

| Método e rota | Corpo / resultado |
|---|---|
| `POST /api/cadastro` | `{nome, email, senha, confirmacao}` → 202; sem usuário/sessão de login |
| `POST /api/login` | `{email, senha}` → 200; pendente com senha correta: 403 `email_nao_verificado` |
| `POST /api/login/google` | `{credential}` → 200 com usuário/plano/CSRF; 401 genérico para token/vínculo inválido, 404 sem Client ID |
| `POST /api/email/reenviar` | `{email}` → 202 genérico |
| `POST /api/email/verificar` | `{token}` → 200 ou 400 para inválido/expirado/usado |
| `POST /api/email/verificar-conta` | `{}` → 202 genérico; exige login/CSRF e usa somente o endereço da conta autenticada |
| `POST /api/senha/recuperar` | `{email}` → 202 genérico |
| `POST /api/senha/redefinir` | `{token, senha, confirmacao}` → 200; sessões antigas deixam de valer |
| `POST /api/sessao/atividade` | `{}` → 200 com login; renova somente o prazo de inatividade |

403 com `codigo=csrf` permite ao cliente buscar outro CSRF e repetir uma vez. Recusas por perfil ou verificação
não são repetidas. Reenvio/recuperação não informam se existe uma conta. O login usa erro genérico para credenciais erradas;
diferenças de tempo entre hashes legados e atuais não têm garantia de indistinguibilidade.

## Verificação segura

Na raiz, com PHP, Docker e Python disponíveis:

```bash
python site/dev/test_auth.py
```

O executor cria contêiner `fornex-auth-test-*`, banco `fornex_auth_test_*`, configuração, credenciais e sessões
temporários e remove tudo ao terminar. Não lê `.env` nem a configuração privada atual. Executa autenticação,
regressões de API/WhatsApp e exportação de provas. Os testes antigos agora recusam execução direta contra a base local.
Para selecionar um caso/suíte, acrescente o nome unittest, por exemplo `test_auth`.

Os e-mails são capturados somente com `AMBIENTE=test`, banco com prefixo reservado e `MAIL_TRANSPORT=capture`.
Não há bypass de verificação na aplicação. As regressões de planos/consultas preparam suas contas verificadas diretamente
no banco descartável; a suíte de autenticação usa os links reais capturados. Há também SMTP falso local com TLS.

O teste opcional de interface requer Playwright instalado fora das dependências do produto e um navegador:
defina `FORNEX_PLAYWRIGHT_MODULE` para o caminho do módulo e, se necessário, `FORNEX_BROWSER_CHANNEL` (padrão `msedge`).
Ele testa cadastro, confirmação, login, recuperação e largura móvel, bloqueando acessos externos.
As capturas ficam em `logs/auth-ui/`, fora do versionamento.

`test_auth_regressoes` cobre: seis logins simultâneos em três servidores PHP, limites globais e liberação de travas,
GC forçado com sessão de 25 minutos e expiração aos 31, exportação sem ler configuração privada,
login do benchmark para contas legadas/verificadas e recusa de pendentes, migração repetida sem mudar dados,
backup/restauração real, dump parcial, preservação de backup anterior, porta e banco vazio.
Os scripts de backup são testados diretamente no contêiner descartável; `deploy.sh` não é executado pelos testes.

`test_auth_ajustes` cobre cadastro corporativo, recusa de formatos inválidos e endereços acima do limite,
o campo booleano de verificação no login e em `/api/me`, confirmação de conta antiga sem alterar seu
hash, papel ou regra de compatibilidade, solicitação restrita à própria conta, login/CSRF obrigatórios
e uso de `X-Forwarded-For` somente quando o remetente é um proxy configurado (IPv4 e IPv6).

`test_auth_google` usa um tokeninfo HTTP exclusivo de loopback e JWTs RSA gerados durante os testes.
O substituto só é aceito com `AMBIENTE=test` e banco com o prefixo reservado; fora disso o destino é sempre
o Google oficial. Testa assinatura adulterada, aud/iss/exp/verificação inválidos, contas novas/repetidas,
vínculos, preservação de conta verificada, revogação de senha/sessões/tokens de conta não verificada,
recusa de admin, hash nulo, CSRF, limites, concorrência, migração repetida e indisponibilidade do validador.
Com Playwright, simula também o script GIS nas duas abas, passa pelo backend real e ativa o plano existente
a 390 px, bloqueando rede externa. Não valida o popup nem o serviço real do Google.

O benchmark `bench/carga.py --contas /caminho/privado/contas.json` recebe contas de teste já verificadas, com
`email`, `senha` e `nome` opcional. Faz apenas login e segue o fluxo de planos existente. Não cadastra contas
automaticamente nem contorna a confirmação. Sem esse arquivo, usa as contas legadas de carga, se já existirem.
O teste automatizado verifica somente a preparação das sessões; não inicia carga, worker pago ou envio externo.

Pendências para ativação real: configurar correio e cron, aplicar a migração no ambiente escolhido após backup,
publicar mediante autorização e conferir HTTPS, entrega real de mensagens e separação dos perfis nesse ambiente.
