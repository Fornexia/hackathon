# 2026-11-16: rodrigo-google

- **Quem:** rodrigo-google (Rodrigo Santana, com Claude Code)
- **Branch e commit de partida:** `feat/ajustes-login-google` em `09267ca` (= `gpt/gabriella-autenticacao-site-2026-11-15`), no worktree `hackathon-gabi`. **Local, sem push**: o trabalho é da Gabi e só sobe na branch dela com o aval dela.
- **Máquina e ambiente:** Windows 11, Docker Desktop (MariaDB descartável), PHP 8.2, Edge com Playwright (Python e Node).

## Resumo

Ao testar o login com Google, o clique no botão mostrou "Error 401: invalid_client". Causa: o ambiente de demonstração usava um Client ID inventado; o código está certo, falta criar um Client ID real no Google Cloud Console. Aproveitei para refazer o visual do botão no padrão do site (divisor "ou", tema claro e escuro, largura do cartão), fazer o `deploy.sh` levar `GOOGLE_CLIENT_ID` e `TRUSTED_PROXIES` ao servidor (antes o botão nunca apareceria na produção) e esconder o botão "Verificar agora" depois do envio. **Commitado só nesta branch local.**

## Feito

- `site/public_html/assets/chat.js`: o botão do Google é redesenhado no tema do site (`outline` no claro, `filled_black` no escuro), com a largura do cartão (até 400 px), texto "Continuar com o Google" (serve para entrar e para criar conta), e de novo ao trocar de aba, de tema ou de tamanho da janela. `shape: 'rectangular'`; no escuro o contêiner ganha o canto de 12 px dos botões do site.
- `site/public_html/chat.html` e `site.css`: o rótulo "Ou entre com Google" virou o divisor "ou" com linhas, o botão do Google em largura total e a dica em texto pequeno. Versões dos arquivos (`?v=`) atualizadas para não pegar cache.
- `site/deploy.sh`: lê `GOOGLE_CLIENT_ID` e `TRUSTED_PROXIES` (opcionais) do `.env`, confere o formato antes de publicar e grava as duas constantes no `hackathon-config.php` do servidor. Sem elas, o arquivo não muda.
- `site/public_html/assets/conta.js`: depois de "Verificar agora" dar certo, o botão some e a mensagem fica.
- `docs/AUTENTICACAO.md` e `site/dev/README.md`: no computador local, abrir por `http://localhost:8080` (nunca `127.0.0.1`); o erro `invalid_client` e o que ele significa; como o deploy leva o Client ID.

## Verificado (e como)

- `python site/dev/test_auth.py test_auth_google test_auth_ajustes` com o módulo Playwright → **21 testes OK, 0 pulados** (inclui o teste do navegador com o Google simulado, nas duas abas e a 390 px).
- `test_auth.TestAuthPublica.test_interface_no_navegador` → OK (cadastro, verificação, login, recuperação, no Edge).
- Botão **real** do Google (com Client ID falso) renderizado no Edge em tema claro, escuro e a 390 px: um botão por aba, largura 400 px (desktop) e 304 px (celular), sem erro de JavaScript. Com tema trocado em tempo de execução, o botão muda de `outline` para `filled_black` e volta, sempre um por aba.
- `deploy.sh`: `bash -n` OK; o bloco que gera o `hackathon-config.php` foi renderizado com e sem as variáveis (as linhas só aparecem quando há valor, com aspa simples escapada). Validação do Client ID aceita `123-abc.apps.googleusercontent.com` e recusa texto sem número, domínio acrescentado e espaço; a de proxies recusa `;` e nomes.

## Não verificado

- **Login com o Google de verdade:** exige um Client ID real, que só o dono da conta Google da empresa pode criar. Sem ele, o clique mostra `invalid_client`, como visto.
- `deploy.sh` rodando de ponta a ponta (sem SSH, sem Hostinger): só o bloco da configuração foi exercitado.
- A aparência do botão em outros navegadores e no modo escuro do sistema operacional além do Edge.

## Decisões e motivo

- **Mantive o botão oficial do Google** (iframe/div dele) em vez de um botão próprio: o fluxo de ID token só funciona por ele, e esconder o botão do Google sob um botão nosso é frágil e foge das regras de marca do Google. O que se pode escolher (tema, formato, largura) foi ajustado ao site.
- **Canto de 12 px só no tema escuro:** o botão escuro não tem borda, então o recorte fica limpo; o claro tem borda cinza que um recorte cortaria.
- **`tokeninfo` mantido:** a Gabi o escolheu e funciona; é ferramenta de depuração segundo o Google (rede a cada login). Trocar pela validação local com as chaves públicas do Google fica como endurecimento antes de abrir ao público.

## Em aberto (por prioridade)

1. [ ] **Criar o Client ID real** no Google Cloud Console (aplicativo Web, origens `http://localhost:8080` e a de produção) e pôr `GOOGLE_CLIENT_ID` em `site/hackathon-config.php` (local) e no `.env` (deploy). (origem: 2026-11-16-rodrigo-google)
2. [ ] **Combinar com a Gabi** como estas mudanças entram na branch dela (patch, ou branch separada para ela mesclar). (origem: 2026-11-16-rodrigo-google)
3. [ ] SMTP real, cron do `enviar-emails.php` e `composer install` antes do deploy: sem isso, o cadastro por senha continua devolvendo 503 na produção. (origem: 2026-11-16-rodrigo-google)
4. [ ] Trocar o `tokeninfo` pela validação local do token antes de abrir ao público. (origem: 2026-11-16-rodrigo-google)
5. [ ] Tela de consentimento em modo "teste": só as contas listadas entram; publicar o app para liberar todos. (origem: 2026-11-16-rodrigo-google)

## Resolvido de sessões anteriores

Nenhum.

## Armadilhas

- `http://127.0.0.1:8080` não funciona com o Google: use `http://localhost:8080`.
- Mudanças nas origens autorizadas do Client ID podem levar de alguns minutos a algumas horas para valer.
- O `.env` não é lido pelo PHP: o `deploy.sh` é quem transporta `GOOGLE_CLIENT_ID` para o arquivo privado do servidor.
- Os testes com navegador precisam de `FORNEX_PLAYWRIGHT_MODULE` apontando para um Playwright de Node (fora do repositório).

## Próximo passo sugerido

Criar o Client ID, testar o clique de verdade em `http://localhost:8080` e então combinar com a Gabi como entram as mudanças.
