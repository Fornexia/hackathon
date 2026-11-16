# Backlog

Code freeze: **06/11/2026, 12h**. O que ficar de fora entra como próximo passo no registro de limitações.

**Critério de pronto:** uma pergunta real, resposta conferível, outro perfil bloqueado e tudo no log.

## Hoje, até o Checkpoint 1 (19h)
- [x] Capturar o portal de Garanhuns com hash
- [x] Criar o repositório
- [ ] Verificar se pagamento se liga a contrato
- [x] Ler os painéis do portal do Estado de PE; coleta ainda não testada

## Hoje, 19h50–21h30
- [x] Implementar a ontologia v1
- [x] Carregar amostra de 10 contratos no Neo4j
- [x] Criar as consultas com filtro de perfil
- [ ] Validar a primeira resposta com âncora pelo WhatsApp

## Noite, se houver fôlego
- [x] Criar o segundo tenant e os dois perfis (três perfis em `consulta/perfis.json`, testados no Neo4j com dados fictícios)
- [x] Registrar consultas e fontes no log (`logs/consultas.jsonl`)

## Amanhã, 9h40–11h
- [x] Testar acesso entre perfis (65 testes automáticos, ver `docs/testes-seguranca.md`)
- [ ] Rodar os ataques de prompt com o agente real e registrar (catálogo em `docs/seguranca/ataques-de-prompt.md`)
- [ ] Isolar as ferramentas do agente no WhatsApp e resolver a corrida de perfil (AP-07, AP-18)
- [ ] Confirmar com o mentor o que "por estado" exige (um estado a mais, ou município mais Estado)
- [ ] Construir site e chat: ver [tasks](specs/001-site-e-chat/tasks.md)
- [x] Completar o README com as instruções de execução

## Amanhã, 11h–12h
- [ ] Ensaiar a demo
- [ ] Fechar slides, premissas, limitações, riscos e próximos passos
- [ ] Enviar os materiais

## Validar com o mentor
1. Portal municipal conta, ou o estadual é obrigatório?
2. Onde o analista perde mais tempo: achar, confirmar a empresa ou documentar a fonte?
3. Os fornecedores dos clientes aparecem nesses portais?
4. Que decisão a resposta alimenta: homologar, bloquear ou renovar?
5. Qual erro é inaceitável: sem fonte, vazamento ou dado desatualizado?
6. O "Obrigatório (até 19h)" do slide 44 vale para hoje?

## Cobertura de CNPJs fora da amostra (combinado em 14/11/2026, um item de cada vez, com verificação)
Motivo: três CNPJs reais testados pelo WhatsApp (Ferreira Costa e dois outros) não foram achados. A base é uma amostra de 100 contratos e o Neo4j do notebook tem hoje a base de exemplo (fictícia).
1. [x] **CEIS e CNEP** (sanções federais): feito, verificado com dado real, **commitado e enviado** (ver `docs/testes-seguranca.md` §2.7). O plano "Único" do site já inclui a União (§2.10). Falta: **publicar na Hostinger** (worker novo antes, `php site/setup.php` depois).
2. [x] **Cadastro da Receita** (razão social, situação, CNAE): coleta por lista, extração, ferramenta `cadastro_do_fornecedor` e busca por nome fantasia **prontas, verificadas com dado real e commitadas** (`docs/testes-seguranca.md` §2.8). Falta: decidir se o cadastro passa a ser buscado **na hora da pergunta** (hoje é por lista), medir ataques e benchmark com a ferramenta nova, e coletar os CNPJs da demonstração. **Decisão do dono (14/11): manter, inclusive o nome do titular de MEI na razão social (dado público no cadastro).**
3. [ ] **PNCP** (coletor, extração e teste **prontos e commitados**; ver `docs/testes-seguranca.md` §2.9). Investigação de 14/11: a API oficial de consulta **não filtra por fornecedor**; contratos só por data de publicação (**máximo 365 dias**), `cnpjOrgao` ou unidade. Serve para **ampliar os contratos de órgãos escolhidos**, não para consultar um CNPJ qualquer. Medido: Município de Garanhuns (11.303.906/0001-00) tem **55 contratos em 2026** (47 fornecedores, 46 com valor informado) e **nenhum é da Ferreira Costa, da Bernhoeft nem do MEI testado**. A API é lenta (cerca de 15 s por página de 10) e deu erro 500 com página de 100. Falta: decidir quais outros órgãos entram em `ORGAOS_PNCP` (hoje só a Prefeitura de Garanhuns) e como evitar a contagem dupla com o portal municipal.
4. [ ] **API da Receita Federal** (pedido do Rodrigo, para análise depois): consulta por CNPJ (por exemplo BrasilAPI) ou os arquivos abertos mensais (`dadosabertos.rfb.gov.br`). Só dá identidade da empresa; não traz contrato nem sanção.
5. [x] **Contratos federais por CNPJ** (`/api-de-dados/contratos/cpf-cnpj`): feito, chave testada e funcionando (HTTP 200), coletor, extração e testes **commitados** (§2.9). A filial da Bernhoeft tem 2 contratos com a Receita Federal. Passo a passo da chave em `docs/chave-api-portal-transparencia.md`.
7. [ ] **(Lucas)** **Melhorias vistas no teste de voz de 14/11** (`docs/testes-seguranca.md` §2.11): (a) ferramenta `sancionados_entre_contratados` para a pergunta "existe fornecedor com sanção?" (hoje 44 consultas, cobertura parcial dita como total: 43 de 49 fornecedores), e a `cobertura` informar quantos itens a lista mostra do total; (b) a `cobertura` declarar que o CEIS/CNEP de PJ foi carregado inteiro, para "CNPJ não aparece" virar "sem sanção federal registrada em 13/11" em vez de "não sei". Exige repetir ataques e benchmark.
6. [x] **Áudio no WhatsApp**: preparado e verificado com **voz sintética** em 14/11 (`docs/testes-seguranca.md` §2.11): ambiente, modelo, contexto do domínio, **CNPJ falado conferido pelo dígito verificador** e eco "Entendi". **Falta: mandar notas de voz reais pelo celular** (T14), que é o único jeito de saber a taxa de erro de verdade.
8. [x] **`ligar-tudo-e-instalar-docker.bat`** (pedido do dono, 14/11): feito. `scripts/instalar-e-ligar.ps1` instala o Docker Desktop **só se faltar, perguntando antes** (winget; administrador, WSL 2 e reinício possíveis), cria o `.env` se faltar, **só confere** git/Python/PHP/bun/`.venv` (mostra o comando do guia) e chama o `ligar-tudo`. `-Teste` não instala nada; `-Sim` responde sozinho. **Falta verificar a instalação de verdade numa máquina sem Docker** (os dois colegas com Windows). O `ligar-tudo.sh` (Linux) continua exigindo Docker já ligado.

## API para IAs de terceiros (demonstração de 18/11/2026)

Três portas sobre as mesmas consultas, com chave que define o perfil (ver `api/README.md`). Branch `feat/api-demo`, commit `2cc47b9`.

1. [x] **API feita e testada:** REST, MCP e pergunta em português; 50 testes da API e ataques manuais nas portas REST e MCP.
2. [ ] **Bateria de ataques de prompt pela porta pergunta** com o modelo real (cerca de US$ 0,50 por 20 perguntas); repetir quando prompt, modelo ou ferramentas mudarem.
3. [ ] **Rodar atrás da Tailscale** com `API_HOSTS_PERMITIDOS` definido (hoje um `Host` forjado é aceito) e contra o Neo4j grande do bot, não só a base fictícia.
4. [ ] **Cliente MCP de verdade** (hoje só JSON-RPC cru) e **PR da `feat/api-demo`** para a `main`.
5. [ ] **Decidir a abordagem** (REST, MCP ou pergunta, ou combinação) com `python api/medir.py` depois da demonstração. A pergunta precisa de cobrança por consulta (custo cresce com o uso).
6. [ ] **Limites na memória** zeram ao reiniciar a API: guardar em disco se virar produto.
