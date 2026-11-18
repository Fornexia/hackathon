# Revisão da autenticação para Pull Request

> Este documento registra a auditoria anterior aos ajustes de e-mail/proxy e ao login Google.
> A entrega de ajustes está no commit local `3f61265`, com 147 testes aprovados. A nova entrega Google
> acrescenta uma coluna e altera a nulabilidade do hash: exige a migração atualizada antes da ativação.
> A suíte completa posterior ao Google aprovou 164 testes, sem falhas ou pulos, com serviços simulados.
> Configuração, testes atuais e limites estão em [AUTENTICACAO.md](AUTENTICACAO.md) e no diário de 16/11.
> Para o próximo PR, sugere-se a base `feat/portabilidade-windows-linux`, que já inclui os 43 arquivos
> institucionais; não houve mudança de base, reorganização, reescrita do histórico ou novo push nesta tarefa.

Branch: `gpt/gabriella-autenticacao-site-2026-11-15`. Ponto de partida das correções: `f255342`.
Referência remota conferida: `origin/main` em `af43561`.

## Correções autorizadas

| Problema | Gravidade na auditoria | Correção e evidência |
|---|---|---|
| Dump parcial podia ser aceito antes da migração | Alta | Bash remoto com `pipefail`; helper independente, porta explícita, arquivo temporário, validação gzip/tabelas e renomeação final. Testes de falha parcial, preservação de destino, instalação vazia e restauração real |
| Requisições simultâneas ultrapassavam o limite de login | Média | Travas MariaDB por IP e e-mail abrangem contagem, senha e registro. Testes com seis clientes/três servidores, limites globais e retomada após desbloqueio |
| Coletor PHP podia apagar sessão antes dos 30 minutos | Média | Diretório privado exclusivo e `gc_maxlifetime` alinhado aos prazos. GC forçado preserva sessão de 25 minutos; aplicação recusa aos 31 |
| Teste de prova lia configuração privada e falhava em clone limpo | Média | Usa somente `CONFIG` temporária validada pelo executor. Regressão impede leitura do caminho privado mesmo quando existe |
| Benchmark usava cadastro/contrato anteriores | Média | Login de contas existentes; arquivo privado opcional de contas verificadas. Testa conta antiga, nova verificada, pendente e ausente, sem cadastro automático |

As correções preservam o esquema da aplicação, os papéis e o fluxo de planos. Não exigem nova migração.
A troca do diretório de sessões encerra a continuidade das sessões antigas: será necessário entrar novamente.
As contas, suas senhas e permissões são preservadas.

## Validação e limites

Executor: `python site/dev/test_auth.py`, com PHP 8.2.35, Python 3.13 e MariaDB 10.11 descartável no Windows.
O navegador opcional usa Playwright/Edge instalado fora do produto. SMTP é simulado localmente com TLS.
O executor remove contêineres, bancos, configuração e sessões temporários ao terminar.

Resultado final: **143 testes aprovados em 321,308 segundos, sem falhas nem testes pulados**, incluindo navegador.
A execução específica das oito regressões também passou. Um teste adicional de exportação de provas passou
em cópia temporária sem `.env` nem configuração privada. Sintaxe PHP/Bash/Python e requisitos Composer aprovados;
validação Composer válida, com aviso preexistente de ausência de licença. Varredura de 76 caminhos envolvidos
não detectou credenciais reais; nenhum arquivo privado/dependência/sessão está entre os arquivos previstos.
O diário de 16/11/2026 registra comandos e limitações. Testes não demonstram entrega SMTP real,
execução do cron, restauração na Hostinger ou comportamento do ambiente publicado.

Para homologar: configurar origem HTTPS, SMTP/TLS, remetente autorizado, chave privada da fila e cron;
conferir permissões do diretório de sessões, backup recuperável e migração aditiva após backup.
Não executar `setup.php` com administrador em atualização comum. Ver [AUTENTICACAO.md](AUTENTICACAO.md).

## Análise dos 43 arquivos institucionais

Os 43 arquivos abaixo são anteriores à implementação PHP, recebidos nos commits `9a9d6b2`, `dea3197` e `b7dc44b`.
São uma aplicação React/Vite independente. A API PHP não importa esses arquivos e seu deploy é separado.
`Testar.tsx` fornece links para o chat e cadastro; não autentica na API. `Admin.tsx` guarda a proteção do protótipo
no navegador e não representa o perfil administrativo do backend PHP.

Todos os caminhos da tabela são relativos a `site-institucional/`.

| Grupo | Quantidade | Arquivos |
|---|---:|---|
| Componentes React | 9 | `Admin.tsx`, `App.tsx`, `Fundadores.tsx`, `Sections.tsx`, `Social.tsx`, `Testar.tsx`, `ThemeToggle.tsx`, `main.tsx`, `components/fornex-laptop/FornexLaptop.tsx` |
| TypeScript e integração Vite | 5 | `content.ts`, `hooks.ts`, `theme.ts`, `vite-env.d.ts`, `vite.config.ts` |
| Estilos | 6 | `index.css`, `styles/admin.css`, `styles/light.css`, `styles/pro.css`, `styles/testar.css`, `components/fornex-laptop/FornexLaptop.css` |
| Imagens | 5 | `favicon.png`, `reference.png`, `notebook-reference.jpg`, `components/fornex-laptop/assets/area-tecnica.jpg`, `components/fornex-laptop/assets/assistente-laptop.jpg` |
| Ferramentas/publicação | 10 | `make/analyze-routes`, `make/deploy`, `make/deploy-preview`, `make/deploy.json`, `make/dev`, `make/dev.json`, `make/format`, `make/install`, `make/langserver`, `make/site.json` |
| Dependências/configuração | 4 | `.gitignore`, `package.json`, `package-lock.json`, `tsconfig.json` |
| Documentação | 2 | `DIARIO-DE-MODIFICACOES.md`, `LEIA-ME.md` |
| Conteúdo | 1 | `public/content.json` |
| Entrada HTML | 1 | `index.html` |

Pendência de escopo **média**: esses arquivos ampliam o PR de autenticação. A importação e seus ajustes devem
ter revisão própria. O `tsconfig.json` inclui `src` e `vite.config.ts`, enquanto os componentes estão na raiz;
a checagem atual não cobre os componentes (achado **baixo**, fora das cinco correções autorizadas).
O build Vite validado na auditoria não substitui essa checagem. A proteção local do protótipo não deve ser
apresentada como autenticação administrativa de produção.

### Proposta de separação, sem executar

1. Revisar e integrar os três commits institucionais em PR próprio primeiro, a partir da linha que já os contém.
2. Depois que essa base estiver na `main`, revisar o PR desta branch: a comparação passará a concentrar a autenticação
   e estas correções. Atualizar sua base somente com autorização, sem reescrever commits.
3. Se a equipe precisar da autenticação antes do institucional, criar futuramente outra branch baseada na `main`
   e transportar apenas os commits/arquivos necessários, preservando integralmente esta branch como referência.
   Essa alternativa exige aprovação prévia e nova validação da comparação.

Nenhum arquivo institucional foi movido, excluído ou alterado nesta correção. Nenhum histórico foi reescrito.
Nenhuma das alternativas foi executada. A ausência de conflitos de conteúdo na auditoria não equivale a merge aprovado.

## Commit proposto

As cinco correções estão verificadas e prontas para revisão técnica. Nenhum impedimento técnico foi encontrado
nessas correções. Para um PR exclusivo da autenticação, a decisão de separação dos 43 arquivos continua pendente;
o achado de TypeScript pertence à revisão institucional e não foi alterado sem autorização.

Mensagem: `fix(auth): corrigir achados da auditoria e adicionar regressões isoladas`.

Incluir somente as correções PHP, o helper de backup e sua chamada no deploy, adaptação de carga, regressões,
executor isolado, modelo público de configuração, regras de ignorados, documentação e diário da sessão.
Não incluir configurações privadas, sessões, dependências instaladas, capturas ou arquivos de contas de carga.
O commit e o push deste conjunto foram autorizados expressamente pela usuária após a revisão.
A abertura do Pull Request será feita pela usuária no GitHub; não realizar merge nem deploy nesta etapa.

Arquivos previstos (15):

```text
.gitignore
README.md
bench/carga.py
docs/AUTENTICACAO.md
docs/REVISAO-AUTENTICACAO-PR.md
docs/rodar-no-windows-e-no-linux.md
docs/sessoes/2026-11-16-anagmenezes.md
site/backup-banco.sh
site/deploy.sh
site/dev/test_auth.py
site/dev/test_auth_regressoes.py
site/dev/test_prova.py
site/hackathon-config.exemplo.php
site/public_html/api/lib_base.php
site/public_html/api/lib_conta.php
```
