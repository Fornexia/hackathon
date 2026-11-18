# API da FornexIA para IAs de terceiros (demonstração)

Uma IA de fora consulta o "histórico de fornecedor com prova" por **três portas**, todas sobre as mesmas consultas do agente
(`consulta/mcp_transparencia.py`) e a mesma chave:

| Porta | Como | Para quem | Gasta modelo? |
|---|---|---|---|
| **A. REST** | `GET /v1/...` (JSON) | IA ou sistema que chama HTTP comum | Não |
| **B. MCP** | `POST /mcp` (Streamable HTTP, sem sessão) | IA que já fala MCP: as 9 tools do agente | Não |
| **C. Pergunta** | `POST /v1/perguntar` | Quem quer a resposta pronta em português, com as fontes | **Sim**, com teto diário |

Documentação gerada do código: `GET /openapi.json` (sem chave). Estado: **demonstração**, com dados fictícios. Sem cobrança, sem painel,
limites na memória (zeram ao reiniciar).

## Subir

```bash
python api/gerar_chave.py demo-cliente estado       # imprime a chave UMA vez; o arquivo guarda só o hash
python api/servidor.py                              # http://127.0.0.1:8088 (só esta máquina)
```

Na VM, escute só no IP do Tailscale e libere o nome pelo qual o cliente chega (proteção contra DNS rebinding da porta MCP):

```bash
API_HOSTS_PERMITIDOS="100.127.243.57:*,fornexia-srv:*" python api/servidor.py --host 100.127.243.57
```

Precisa do Neo4j no ar com os dados (`NEO4J_URI`, `NEO4J_SENHA`, `BRUTO` no `.env`) e, para a porta C, do agente configurado como o chat
do site (`claude` logado, ou `AGENTE_PROVEDOR`/`AGENTE_MODELO` com a chave do provedor). **Não exponha na internet aberta.**

## Usar

```bash
CHAVE=fx_...   # a chave gerada
curl -H "Authorization: Bearer $CHAVE" http://127.0.0.1:8088/v1/me                       # perfil, entes e limites da chave
curl -H "Authorization: Bearer $CHAVE" http://127.0.0.1:8088/v1/cobertura                # o que existe na base
curl -H "Authorization: Bearer $CHAVE" "http://127.0.0.1:8088/v1/fornecedores?q=Construtora"
curl -H "Authorization: Bearer $CHAVE" http://127.0.0.1:8088/v1/fornecedores/cnpj:11111111000111/sancoes
curl -H "Authorization: Bearer $CHAVE" http://127.0.0.1:8088/v1/evidencias/e1            # a prova: trecho, fonte, hash
curl -H "Authorization: Bearer $CHAVE" -H "Content-Type: application/json" \
     -d '{"pergunta": "Existe alguma sanção para algum fornecedor?"}' http://127.0.0.1:8088/v1/perguntar
```

A chave também vale no cabeçalho `X-API-Key`. Rotas de dados: `/v1/cobertura`, `/v1/fornecedores?q=`, `/v1/contratos[?q=]`,
`/v1/fornecedores/{id}/contratos|sancoes|cadastro|execucao[?ano=]` e `/v1/evidencias/{id}`.

**MCP** (cliente que aceita servidor remoto): URL `http://<host>:8088/mcp` com o cabeçalho `Authorization: Bearer <chave>`. Sem sessão:
cada chamada é independente, então `tools/list` e `tools/call` funcionam direto. Testado com o **Claude Code** como cliente (`--mcp-config` com `"type":"http"` e `"headers":{"Authorization":"Bearer ..."}`). Atenção: a busca de fornecedor leva `termo` no MCP e `q` na REST.

## Token gerado pela própria pessoa (página da conta)

Na página **Minha conta** do site, a pessoa gera um token MCP (até 3 ativos), copia o comando pronto para o Claude Code ou o Codex e
revoga quando quiser. O site guarda só o SHA-256 do token. `python api/sincronizar_tokens.py` busca a cada 15 s os hashes ativos e os
entes do plano de cada conta pela rota protegida do worker (`GET /api/worker/tokens`, com `X-Worker-Key`) e os grava em `api/chaves.json`
com `origem: "site"`; a API relê o arquivo sozinha. O perfil é o de `consulta/perfis.json` com exatamente os entes do plano e sem dado
pessoal. Chaves criadas à mão ficam intactas; se o site não responder, o arquivo atual é mantido. Testes: `api/testes/test_sincronizar.py`.

Comandos que a página monta (o token entra no lugar de `SEU_TOKEN`):

```bash
claude mcp add --transport http --scope user fornexia https://<host>/mcp --header "Authorization: Bearer SEU_TOKEN"
export FORNEXIA_TOKEN="SEU_TOKEN" && codex mcp add fornexia --url https://<host>/mcp --bearer-token-env-var FORNEXIA_TOKEN
```

## Regras de segurança (e onde estão provadas)

| Regra | Teste |
|---|---|
| O **perfil sai da chave**, guardada no servidor. Nunca de URL, corpo, argumento de tool ou texto de pergunta | `test_o_perfil_vem_da_chave_nunca_do_corpo`, `..._da_url`, `test_o_perfil_nao_muda_por_parametro_de_url`, `test_mcp_nao_aceita_perfil_como_argumento` |
| Um perfil **nunca vaza para outro** quando atendidos ao mesmo tempo (60 chamadas simultâneas, REST e MCP, 3 perfis) | `test_concorrencia_um_perfil_nunca_vaza_para_o_outro` (a mutação "estado global no lugar do contexto" faz este teste falhar) |
| Sem contexto de chave, o núcleo **falha fechado**: zero entes, zero dados | `test_fora_de_uma_requisicao_o_nucleo_falha_fechado` |
| Toda porta exige chave (REST, MCP, pergunta, qualquer outro caminho) | `test_todas_as_portas_exigem_chave` |
| Perfil com **dado pessoal** não pode ter chave | `test_perfil_com_dado_pessoal_e_recusado` |
| O arquivo guarda **só o hash**; a chave nunca vai para log nem para resposta | `test_o_arquivo_guarda_so_o_hash...`, `test_o_log_da_api_nao_guarda_chave_nem_o_texto_da_pergunta` |
| Evidência de outro ente é 404; a prova não revela o caminho do servidor | `test_evidencia_de_outro_ente_da_404_...` |
| Erro interno devolve texto genérico, sem pilha nem caminho | `test_excecao_no_agente_vira_500_generico` |
| Limite por minuto (429 + `Retry-After`) e **teto diário de perguntas** por cliente e no total; pergunta inválida não gasta o teto | `test_limite_por_minuto...`, `test_teto_diario...`, `test_pergunta_invalida_nao_gasta_o_teto` |

As consultas são as do agente (perfil, validação de entrada, limite de 50 linhas, registro por chamada). A API **não escreve consulta nova**
ao grafo. A única mudança fora de `api/` é em `consulta/mcp_transparencia.py`: o perfil passou a poder vir de um contexto por chamada
(`com_perfil`), com o ambiente do processo como padrão, então o agente e o worker se comportam como antes (313 testes de consulta seguem passando).

## Decidir entre as portas: `python api/medir.py`

Cada requisição vira uma linha em `logs/api.jsonl`. O resumo mostra, por porta: chamadas, taxa de erro, tempo mediano e p95; e, na pergunta,
tokens e **custo em dólar só quando o provedor informou** (nada é estimado). Use depois da apresentação e dos testes:

```
python api/medir.py --desde 2026-11-18
```

Medida de uma pergunta real (15/11/2026, base fictícia, `claude-sonnet-5-5`): 5,4 s, 14.840 tokens de entrada, 303 de saída, US$ 0,026, 1 fonte.
Com a base real as respostas das ferramentas são maiores e o custo sobe.

## Testes

```bash
python -m unittest discover -s api/testes -v      # 50 testes; os que precisam do Neo4j são pulados se ele não estiver no ar
```

O agente é trocado por um falso: nenhum teste gasta crédito. O servidor sobe de verdade (uvicorn, porta livre) e é chamado por `urllib`.

## O que NÃO foi feito

- Cobrança, painel de chaves e de uso, termos de uso, página de documentação (só o `openapi.json`).
- Limites persistentes (zeram ao reiniciar) e limite de tamanho do corpo antes de lê-lo (hoje confere depois; a exposição é só pelo Tailscale).
- Teste de ataques de prompt **pela porta C** com o modelo real (a bateria do projeto roda no agente, não nesta API). Fazer antes de abrir para cliente de verdade.
- Dado real e a revisão de LGPD que ele exige.
