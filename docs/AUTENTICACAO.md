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

- Novas contas: endereço `@gmail.com`, senha exclusiva do FORNEX de 15 a 128 caracteres e confirmação.
  A senha do Google não é solicitada e não há OAuth. Hash Argon2id, com espaços, Unicode e caracteres especiais.
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
- As rotas privadas continuam verificando a conta no backend; a administração verifica o papel em cada requisição.
  Limites de login existentes permanecem. Cadastro e solicitações de e-mail têm contadores atômicos por IP/endereço.

## Compatibilidade e migração

`site/migrar-autenticacao.php` acrescenta três colunas a `usuarios` e cria as tabelas `auth_tokens`,
`auth_limites` e `auth_emails`. Pode ser executada novamente. Não exclui contas nem muda IDs, senhas,
papéis, planos, telefones, assinaturas, consultas ou provas. DDL no MariaDB não é transacional:
faça backup antes; uma execução interrompida pode ser retomada com o mesmo comando.

Contas anteriores ficam com `email_verificacao_exigida=0` e `email_verificado_em=NULL`.
Continuam entrando com seus endereços e hashes anteriores, inclusive o administrador e clientes com outro domínio.
Isso é compatibilidade com as contas existentes, **não** uma declaração de que esses endereços foram verificados.
Novos cadastros recebem obrigatoriamente `email_verificacao_exigida=1`. Nenhuma exceção depende do papel.
Recuperar a senha de uma conta antiga mantém seu papel e passa a usar Argon2id.

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

## Contrato da API

Todas as escritas abaixo exigem cookie de sessão e `X-CSRF-Token`, obtido em `GET /api/me`.

| Método e rota | Corpo / resultado |
|---|---|
| `POST /api/cadastro` | `{nome, email, senha, confirmacao}` → 202; sem usuário/sessão de login |
| `POST /api/login` | `{email, senha}` → 200; pendente com senha correta: 403 `email_nao_verificado` |
| `POST /api/email/reenviar` | `{email}` → 202 genérico |
| `POST /api/email/verificar` | `{token}` → 200 ou 400 para inválido/expirado/usado |
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

Pendências para ativação real: configurar correio e cron, aplicar a migração no ambiente escolhido após backup,
publicar mediante autorização e conferir HTTPS, entrega real de mensagens e separação dos perfis nesse ambiente.
