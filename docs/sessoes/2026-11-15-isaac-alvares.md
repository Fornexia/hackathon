# 2026-11-15: isaac-alvares

- **Quem:** Isaac-Alvares (Claude Code)
- **Branch e commit de partida:** `dev-isaac` em `b73d7d6` (já com a `feat/portabilidade-windows-linux` de `584efc2`)
- **Máquina e ambiente:** Windows 11, Docker Desktop instalado, `.venv` da raiz, PHP, bun e git. WhatsApp não pareado nesta máquina.

## Resumo

Conferi as tarefas do Isaac pendentes para 15/11. A tarefa E (caça-bug) já foi feita em 14/11. A tarefa D (teste no celular) depende do celular e está preparada desde 14/11.
A única tarefa nova é o item 0d do diário do Rodrigo de 14/11 (rodar o `ligar-tudo-e-instalar-docker.bat` no Windows e relatar). Rodei o modo de teste; a instalação de verdade não dá para testar aqui, porque esta máquina já tem Docker.
O pull request #3 (`dev-isaac` para `feat/portabilidade-windows-linux`) segue aberto, sem revisão.

## Feito

- `docs/tarefas-isaac/instalar-docker-relato.md` (novo): relato do item 0d. **Commitado junto com este diário.**

## Verificado (e como)

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\instalar-e-ligar.ps1 -Teste` → código 0, as 4 etapas na ordem; `.env` e configuração do site não foram tocados; git, python, php e bun encontrados. 15/11/2026, Windows 11.
- `git fetch`: nenhuma branch nova cita o Isaac; a `feat/portabilidade-windows-linux` está em `584efc2` e ainda não recebeu o PR #3.

## Não verificado

- A instalação real do Docker pelo script (esta máquina já tem Docker).
- A execução sem `-Teste`: abriria o gateway do WhatsApp, que aqui não está pareado.
- Tarefa D (celular): segue com o Isaac.

## Decisões e motivo

- Não rodei a execução real do script: ela não testaria a instalação (o objetivo do item) e ligaria o gateway do WhatsApp, que pediria pareamento por QR code.

## Em aberto (por prioridade)

1. [ ] Tarefa D no celular, pelo roteiro `docs/tarefas-isaac/teste-no-celular.md`. (origem: 2026-11-14-isaac-alvares)
2. [ ] Pedir a alguém sem Docker que rode o `ligar-tudo-e-instalar-docker.bat` e anote o que aconteceu (ver o relato). (origem: 2026-11-15-isaac-alvares)
3. [ ] Pedir revisão do pull request #3 ao Lucas ou ao Rodrigo. (origem: 2026-11-15-isaac-alvares)
4. [ ] Filmar a tarefa B e preencher a coluna do ISAAC na planilha da tarefa A. (origem: 2026-11-14-isaac-alvares)
5. [ ] Revogar a chave do Gemini usada em 14/11. (origem: 2026-11-14-isaac-alvares)

## Resolvido de sessões anteriores

- [x] Abrir o pull request da `dev-isaac`: aberto como #3 em 14/11, sem conflito, depois do merge da portabilidade. (origem: 2026-11-12-isaac-alvares)

## Armadilhas

- O `ligar-tudo` (e o `ligar-tudo-e-instalar-docker.bat` sem `-Teste`) liga o gateway do WhatsApp. Numa máquina sem pareamento, ele abre uma janela pedindo QR code.
- O `diff` entre o `scripts/instalar-e-ligar.ps1` local e o do Git mostra o arquivo inteiro diferente: é só o fim de linha (CRLF).

## Próximo passo sugerido

Fazer a tarefa D no celular e pedir a revisão do PR #3.
