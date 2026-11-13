# 2026-11-12: isaac-alvares

- **Quem:** isaac-alvares, com Claude Code
- **Branch e commit de partida:** `dev-isaac` em `0172803` (um commit sobre `feat/portabilidade-windows-linux` em `a93dca9`)
- **Máquina e ambiente:** notebook Windows 11 com 7,8 GB de RAM, `.venv` com `mcp` e `neo4j`, PHP 8.2, `bun`, `claude` com login, Docker Desktop com Neo4j e MariaDB. Só os dados fictícios (`fixtures/exemplo`); sem a base real. Sem chave do DeepSeek: a cadeia de modelos fica só no Sonnet.

## Resumo

Tarefa da planilha de 12/11: lista do que está PRONTO contra o que é só PLANEJADO, pedida pelo marketing. Entregue em `docs/pronto-x-planejado.md`, com a
evidência de cada item pronto, uma seção "Não verificado" e uma tabela do que o folheto promete e o sistema não faz. Antes, a `dev-isaac` foi trazida para cima da
versão de 12/11 da branch de portabilidade (o conflito com o botão "Exportar prova" foi resolvido mantendo as duas mudanças). As provas ao vivo rodaram depois de
liberar espaço no disco, que estava 100% cheio e impedia o Docker de ligar.

## Feito

- `docs/pronto-x-planejado.md` (novo): tabela de duas colunas, seção "Não verificado", tabela "Folheto × sistema" e 10 evidências. **Commitado junto com este diário.**
- `docs/pronto-x-planejado.pdf` (novo): versão para o marketing, a partir de "A tabela", sem as seções "Não verificado" e "Limites desta verificação" (a versão completa é o `.md`). **Commitado junto com este diário.**
- `docs/evidencias/2026-11-08/` (3 prints) e `docs/evidencias/2026-11-12/` (2 prints) do chat local, usados como evidência. **Commitado junto com este diário.**
- Rebase da `dev-isaac` sobre `a93dca9`: commit `0172803` (`chat/agente.py`, `site/public_html/assets/chat.js`, `site/public_html/chat.html`). **Commitado.**
- Hook ativado neste clone (`git config core.hooksPath .githooks`).

## Verificado (e como)

Tudo em 12/11/2026, Windows 11, dados fictícios, já com o commit `0172803`:
- `python -m unittest discover -s chat/testes` → **205 testes OK, 13 pulados**.
- `python -m unittest discover -s consulta/testes` → **65 testes OK, nenhum pulado** (Neo4j no ar).
- `python site/dev/test_api.py` → **82 testes OK**; `python site/dev/test_prova.py` → **33 testes OK** (worker e Neo4j parados durante os dois).
- **Busca por CNPJ**, direto em `buscar_fornecedor` com o perfil Estado: CNPJ formatado e só dígitos acham o fornecedor; CNPJ parcial e CNPJ de ente fora do perfil não acham nada.
- **Pergunta real pelo site** (`site:1100`, conta de teste local): "O CNPJ ... tem contratos ou sanções?" respondida em 28 s pelo `claude-sonnet-5-5`, com 6 consultas, 2 fontes e
  sem asteriscos na tela (a correção do `0172803` aparece funcionando). `python scripts/jornada.py site:1100` mostrou a jornada inteira.
- **Exportar prova** da `site:1100`: ZIP de 11,5 KB com `prova.json`, `LEIA-ME.txt`, `verificar_prova.py` e 2 trechos (lido pelo navegador, sem salvar em disco).
- **Controle de perfil ao vivo:** a mesma pergunta com `python chat/agente.py municipio "..."` não mostra a sanção do Estado e diz que entes fora do perfil não foram consultados.
- **Histórico na tela:** ao recarregar `chat.html`, a conversa anterior não aparece.

## Não verificado

- O `verificar_prova.py` do pacote não foi rodado à mão, como um auditor faria.
- Busca por CNPJ com a base real: fornecedor com documento mascarado fica sem CNPJ (`coleta/extrair.py`), e não sei quantos são.
- Os números da base real, o WhatsApp com número real e o site publicado. O que o documento marca como **time 12/11** vem do diário do Rodrigo; não repeti.
- Não sei se foi a regra nova do agente ou a limpeza do `chat.js` que tirou os asteriscos: o texto cru do modelo não foi olhado.

## Decisões e motivo

- **Três baldes em vez de dois** (pronto, planejado e "não verificado"): a planilha manda marcar como "não verificado", nunca como pronto, o que não deu para provar.
- **Evidência de 08/11 mantida, com a data**, só onde não repeti hoje (pagamentos e memória da conversa).
- **Rebase em vez de merge** na `dev-isaac`: o commit ainda não tinha sido enviado, então o histórico fica linear sem reescrever nada público.
- **Pacote de prova lido pelo navegador, sem salvar o arquivo**: bastava listar o conteúdo.

## Em aberto (por prioridade)

1. [ ] Abrir o pull request da `dev-isaac` para `feat/portabilidade-windows-linux`, depois do push (confira com `git status -sb` se o push já foi). (origem: 2026-11-12-isaac-alvares)
2. [ ] Marketing corrigir o folheto conforme a tabela "Folheto × sistema" (franquia e excedente, 756 contratos, LGPD, cache, tela de CNPJ). (origem: 2026-11-12-isaac-alvares)
3. [ ] Migrar os 20 ataques de prompt para a bateria automatizada e medir a taxa de bloqueio (tarefa da planilha de 13/11). Hoje: 0 de 20 com o modelo real. (origem: 2026-11-11-rodrigo)
4. [ ] Linha 573 de `docs/rodar-no-windows-e-no-linux.md` ainda diz `planos: 2`; o `setup.php` cria 1 plano (plano único desde `f87cce9`). Trocar por `planos: 1`. (origem: 2026-11-12-isaac-alvares)
5. [ ] Rodar o `verificar_prova.py` de um pacote real, fora do projeto. (origem: 2026-11-12-isaac-alvares)
6. [ ] Aprovar o commit em partes e o push do trabalho de observabilidade. (origem: 2026-11-12-rodrigo)
7. [ ] Medir Sonnet contra Opus no benchmark antes de cravar a escolha. (origem: 2026-11-12-rodrigo)
8. [ ] Passos 2 a 5 do plano de robustez: ataques e benchmark rodando sozinhos, afirmação ligada a evidência, busca melhor, medir o cache. (origem: 2026-11-12-rodrigo)
9. [ ] Avisar por e-mail ou WhatsApp quando um componente ficar fora além do limite. (origem: 2026-11-12-rodrigo)
10. [ ] Restante da matriz do WhatsApp, deploy na Hostinger e teste em celular de verdade. (origem: 2026-11-11-rodrigo)

## Resolvido de sessões anteriores

Nenhum.

## Armadilhas

- **Disco cheio derruba o Docker sem avisar direito**: o Docker Desktop abre, mas o motor não liga; o motivo só aparece no log dele ("There is not enough space on the disk").
  Na janela de erro, use "Quit", nunca "Reset to factory defaults" (apaga os bancos locais).
- Com 7,8 GB de RAM, `site/dev/test_api.py` falha por falta de memória se o Neo4j estiver ligado junto. Pare o Neo4j durante esse teste.
- `site/dev/test_api.py` e `test_prova.py` limpam o banco do site: a sessão do navegador cai e é preciso entrar de novo.
- A pasta pessoal do usuário desta máquina tem um repositório git vazio criado por engano (um `.git` na raiz do perfil). Rode comandos git só dentro do clone do projeto.

## Próximo passo sugerido

Abrir o pull request da `dev-isaac` e começar a bateria dos 20 ataques de prompt (tarefa de 13/11).
