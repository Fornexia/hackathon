# FornexIA · histórico de fornecedor com prova

[![Testes](https://github.com/Fornexia/hackathon/actions/workflows/testes.yml/badge.svg)](https://github.com/Fornexia/hackathon/actions/workflows/testes.yml)

Projeto da equipe **Nexus** no **Desafio 1 (Portal Inteligente de Transparência com IA)** do Hack Garanhuns Tech 2026.

Você pergunta em português, pelo site ou pelo WhatsApp, sobre um fornecedor. O FornexIA consulta contratos, sanções e pagamentos em
portais públicos e responde mostrando, para cada fato, **o trecho original da fonte, a data da captura e um hash** que qualquer pessoa
pode reconferir. Cada cliente enxerga só os entes do seu plano, e a IA não consegue mudar isso.

| | |
|---|---|
| **Produto** | [fornexia.figueiredo.dev](https://fornexia.figueiredo.dev) |
| **Site institucional** | [nexus.figueiredo.dev](https://nexus.figueiredo.dev) |
| **Relatório do teste de capacidade (18/11)** | [PDF](docs/relatorios/2026-11-18-capacidade/fornexia-teste-100-pessoas.pdf) · [dados](docs/relatorios/2026-11-18-capacidade/dados.json) |
| **Manual técnico** | [docs/guia-tecnico.md](docs/guia-tecnico.md) |

## Em números

| O que medimos | Resultado | Como |
|---|---|---|
| **Acerto com prova** | **47 de 50** (94%) | Benchmark com gabarito congelado sobre a base real; o mesmo modelo sem acesso à base acertou **0 de 36** (06/11) |
| **Modelos comparados** | 4 modelos entre **90,7% e 95,3%** | Benchmark de 150 perguntas sobre uma base fictícia; nenhum par se separou de forma estatisticamente significativa, então a escolha é por tempo e custo |
| **Capacidade** | **100 pessoas em 5 minutos**: 100 de 100 respondidas, **0 s de fila**, resposta típica de **11,4 s** | Simulação com 10 agentes em duas máquinas (18/11) |
| **Qualidade sob carga** | **90%** das respostas certas e com prova; **6 de 6** ataques barrados | Mesmo teste, corrigido automaticamente pelo gabarito |
| **Resistência a ataques** | **164 de 165** execuções passaram, a outra foi barrada pelo código; **nenhum vazamento** | 46 ataques de prompt e 2 conversas longas contra o agente real, em até 4 perfis (14/11) |
| **Busca de fornecedor** | **458 de 460** variações acham o fornecedor certo | Nome sem acento, com letra errada, em ordem trocada ou pelo nome fantasia (14/11) |
| **Testes automáticos** | **739** a cada pull request | GitHub Actions: consulta (313), chat (262) e site (164, entre login, API e pacote de prova) |

## O que avançou desde a apresentação de 06/11

| Área | Em 06/11 | Hoje, 18/11 |
|---|---|---|
| **Site** | Protótipo, com as fontes em blocos expansíveis | Site novo em [fornexia.figueiredo.dev](https://fornexia.figueiredo.dev) com o **mapa da consulta ao vivo** (o caminho da pergunta até a prova, desenhado enquanto a IA consulta), tema claro e escuro, e o site institucional em [nexus.figueiredo.dev](https://nexus.figueiredo.dev) |
| **Contas** | Cadastro por e-mail e senha | **Entrar com o Google**, confirmação do e-mail no cadastro, recuperação de senha, senhas com Argon2id e páginas de privacidade e termos |
| **Atendimento** | Um computador com 3 agentes | **Dois computadores dividindo a mesma fila**: um servidor dedicado e o notebook. Se um cair, o outro continua. Teste de 100 pessoas aprovado |
| **Modelos de IA** | Claude e Codex, escolhidos à mão | **Quatro modelos comparados** no benchmark, **troca automática de provedor** quando um falha e a página **Modelos**, com nota, tempo, evidência e custo lado a lado |
| **Fontes de dados** | Amostra do Estado de PE e de Garanhuns | **Coletores da União prontos e testados:** sanções federais (CEIS e CNEP), contratos federais por CNPJ e cadastro da Receita, além dos contratos de Garanhuns no PNCP |
| **Prova** | Trecho e hash em cada fato | **Pacote de prova exportável:** um ZIP que um auditor reconfere sem acesso ao sistema. Se a IA esquece de abrir a evidência, **o código abre sozinho** |
| **Segurança** | 20 ataques catalogados | **Bateria de 46 ataques** contra o agente real, **auditoria por um segundo modelo** que procura vazamento até por paráfrase, e perfil que nunca vem do pedido |
| **Busca** | Nome exato | **Tolerante** a acento, erro de digitação, ordem trocada e nome fantasia |
| **WhatsApp** | Texto | **Nota de voz** transcrita no próprio computador, com trava para CNPJ falado (14 dígitos e dígito verificador) |
| **Integração** | Não havia | **API para IAs de terceiros** (REST, MCP e pergunta em português, com chave que define o perfil) e **alertas por e-mail** quando muda algo num CNPJ acompanhado, os dois em versão de demonstração com testes |
| **Engenharia** | Testes rodados à mão | **CI no GitHub** a cada pull request, roda em **Windows e Linux**, logs por peça do sistema, reconstrução de uma pergunta de ponta a ponta e vigia de quedas |
| **Negócio** | Planos de demonstração | Plano único, documentos comerciais, análise de rentabilidade, proposta preliminar e manual de marca |

## Teste de capacidade: 100 pessoas em 5 minutos

<img src="docs/relatorios/2026-11-18-capacidade/fornexia-teste-100-pessoas-1.png" width="420" alt="Resumo do teste: 100 de 100 respondidas, 0 s de fila, 11,4 s de resposta típica, 27,6 s para 95% das respostas, 90% certas e com prova, 6 de 6 ataques barrados"> <img src="docs/relatorios/2026-11-18-capacidade/fornexia-teste-100-pessoas-2.png" width="420" alt="Linha do tempo das 100 perguntas: cada uma começa a ser atendida no instante em que chega">

Simulamos 100 pessoas fazendo uma pergunta cada, ao longo de 5 minutos, como uma plateia que entra pelo QR code. As perguntas foram
sorteadas do gabarito do benchmark: fatos, coisas que não existem na base, limites do sistema e tentativas de ataque. Atenderam 10
agentes numa fila única: 6 no notebook (Codex) e 4 num servidor dedicado (Claude).

- **Nenhuma pergunta esperou na fila.** Resposta típica de 11,4 s, e 95% delas em até 27,6 s.
- **A qualidade não caiu com a carga:** 90% das respostas certas e com a prova conferida, e todos os ataques barrados.
- **Sobrou capacidade:** os agentes ficaram ocupados 45% do tempo, e o servidor dedicado não passou de 12% de CPU.

O relatório completo, com o tempo de cada resposta, os acertos por tipo de pergunta e o uso das máquinas, está no
[PDF](docs/relatorios/2026-11-18-capacidade/fornexia-teste-100-pessoas.pdf).

## Como funciona

```mermaid
flowchart LR
    P([Pessoa]) -->|site ou WhatsApp| F[Fila de perguntas]
    F --> W1[Worker no notebook]
    F --> W2[Worker no servidor dedicado]
    W1 --> A[Agente de IA isolado]
    W2 --> A
    A -->|só ferramentas de consulta| M[Servidor MCP transparência]
    M -->|filtro pelo perfil do plano| G[(Grafo Neo4j: fatos e evidências)]
    A -->|resposta com as fontes| P
```

1. **Coleta.** Robôs capturam os portais públicos e guardam o arquivo bruto com o hash.
2. **Extração.** Cada contrato, sanção ou pagamento vira um fato no grafo, ligado à evidência: o trecho literal, a tabela, a linha e a data da captura.
3. **Pergunta.** A pessoa pergunta pelo site ou pelo WhatsApp. O site guarda a pergunta numa fila; os workers buscam a próxima e não abrem nenhuma porta para a internet.
4. **Consulta.** O agente de IA só enxerga as ferramentas de consulta. O perfil (quais entes a pessoa pode ver) vem do plano dela, nunca da conversa.
5. **Resposta com prova.** Cada fato da resposta aponta para a evidência, e a tela mostra o caminho percorrido no mapa da consulta.

## Segurança, privacidade e prova

- **Perfil fora do alcance da IA.** Os entes visíveis vêm do plano da conta e são aplicados na consulta ao banco, não no texto da pergunta.
- **Texto dos portais é dado, nunca instrução.** As consultas validam cada argumento, e sinais de tentativa de injeção são registrados.
- **Dado pessoal protegido.** CPF digitado é mascarado nos registros; pessoa física aparece só como código, nunca com nome ou CPF.
- **Prova reconferível.** O pacote de prova traz pergunta, resposta, trechos e hashes, e um auditor confere sem acesso ao sistema.
- **Contas seguras.** Senhas com Argon2id, confirmação do e-mail, limite de tentativas, sessão protegida e login com o Google só para e-mail verificado.
- **API com chave.** Só o hash da chave é guardado, e a chave define o perfil; dado pessoal nunca sai pela API.
- **Registro de cada consulta.** Quem perguntou, com que perfil, quais ferramentas foram usadas e quais evidências sustentam a resposta.

## Área técnica e página Modelos

Para quem tem conta, o site mostra como o sistema funciona por dentro:

- **[Área técnica](https://fornexia.figueiredo.dev/tecnico.html):** como uma pergunta vira resposta com prova, do dado cru ao fato com prova,
  como a ontologia foi construída, o grafo da amostra, como o negócio se sustenta, o que medimos com gabarito, o teste de carga e as camadas de proteção.
- **[Modelos](https://fornexia.figueiredo.dev/modelos.html):** os modelos de IA lado a lado, com nota, nota por tipo de pergunta, tempo por resposta,
  evidência conferida, custo por 100 perguntas, pergunta a pergunta e onde os modelos divergem.

## Documentação

| Documento | O que tem |
|---|---|
| [Guia técnico](docs/guia-tecnico.md) | Estrutura do código, como rodar, perfis, registros, testes e arquitetura em detalhe |
| [Rodar no Windows e no Linux](docs/rodar-no-windows-e-no-linux.md) | Passo a passo completo, do zero ao chat funcionando, incluindo o benchmark |
| [Pronto × planejado](docs/pronto-x-planejado.md) | O que o FornexIA faz hoje e o que ainda é plano, com a evidência de cada item |
| [Roteiro das atualizações](docs/roteiro-das-atualizacoes.md) | As atualizações de 13 a 15/11 explicadas para quem não programa |
| [Ataques de prompt](docs/seguranca/ataques-de-prompt.md) e [testes de segurança](docs/testes-seguranca.md) | O catálogo de ataques, as proteções e os resultados |
| [Pacote de prova](docs/pacote-de-prova.md) | Como a prova exportável é montada e conferida |
| [Autenticação](docs/AUTENTICACAO.md) | Cadastro, confirmação, recuperação de senha e login com Google |
| [Observabilidade](docs/observabilidade.md) | Logs por peça do sistema e reconstrução de uma pergunta |
| [API para IAs](api/README.md) e [alertas por e-mail](alertas/README.md) | As duas integrações em demonstração |
| [Comercial](docs/comercial/) | Documentos comerciais, rentabilidade e proposta |
| [Diários de sessão](docs/sessoes/LEIAME.md) | O registro de cada dia de trabalho, por pessoa |

## Onde estamos e próximos passos

- **Base em produção:** uma amostra com 100 contratos de Pernambuco (70 do Estado, de 2024, e 30 de Garanhuns), 95 sanções e 1.467 linhas
  de execução financeira, cada fato com a evidência. Os coletores da União e o PNCP estão prontos e testados e entram na próxima carga.
- **API para IAs e alertas por e-mail:** prontos e testados em versão de demonstração. Para abrir a clientes, faltam a tela de acompanhamento
  de CNPJ no site e o agendamento da coleta.
- **Capacidade:** o teste de 18/11 mediu o motor de respostas (fila, agentes, consulta e correção). Acima de 100 pessoas, a capacidade é estimativa;
  cada computador a mais soma agentes à mesma fila.
- **Atualidade das fontes:** cada resposta diz a data da captura; o cadastro de sanções de Pernambuco disponível é de 05/06/2025.
- **Próximos passos:** carregar os dados da União na produção, tela de acompanhamento de CNPJ, selo de tempo assinado por terceiro e a API comercial.

## Equipe Nexus

Cecília, Gabriella, Isaac, Lucas, Rafaella, Rodrigo e Victor. O trabalho de cada dia está nos [diários de sessão](docs/sessoes/LEIAME.md).
