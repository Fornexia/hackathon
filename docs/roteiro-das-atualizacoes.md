# Roteiro das atualizações do FornexIA (13 a 15/11/2026)

Para a equipe, sem precisar conhecer o código. Cada ponto diz **o que é**, **por que importa**, **como foi conferido** e **o que falta**. Os detalhes técnicos estão em
[`testes-seguranca.md`](testes-seguranca.md) (seções 2.3 a 2.11) e no diário [`sessoes/2026-11-14-rodrigo.md`](sessoes/2026-11-14-rodrigo.md).

## O problema que começou tudo
Três CNPJs reais foram testados pelo WhatsApp (a **Ferreira Costa**, a **filial da Bernhoeft** e um MEI de Garanhuns) e o bot respondeu "não encontrei" nos três.
**Causa:** a base era uma amostra de 100 contratos, e o banco do notebook estava com dados de exemplo. A busca por CNPJ funcionava. O que faltava era **mais fontes**. Foi isso que os pontos 1 a 7 resolveram.

## 15/11: API para IAs de terceiros e site novo

**13. API para a IA de outra empresa (versão de demonstração para 18/11).** Uma empresa recebe uma **chave**, e é a chave que define o que ela enxerga (município, estado etc.); o perfil nunca vem do pedido. Foram feitas **três portas sobre as mesmas consultas do agente**, para decidir depois com números:
- **REST** (`/v1/...`): para o sistema da empresa. Entrada fixa (busca de fornecedor, contratos, sanções, cadastro, execução, evidência), resposta em JSON com a fonte. Custo para nós quase zero e resposta previsível.
- **MCP** (`/mcp`): para a **IA da empresa** usar as mesmas ferramentas por conta própria. Custo quase zero; é o formato natural de vender "dados para a sua IA".
- **Pergunta em português** (`POST /v1/perguntar`): para quem não tem IA; o nosso agente pesquisa e devolve o texto com fontes. É a que mais impressiona e a única que custa (cerca de **US$ 0,026 por pergunta**, 5 s numa pergunta real).
*Segurança nas três:* só o hash da chave é guardado; limite por minuto e teto diário de perguntas; chave revogada para de valer na hora; **dado pessoal nunca sai pela API**; cada chamada é isolada (teste com 60 chamadas simultâneas, e o teste falha se o isolamento for quebrado de propósito).
*Como foi conferido:* 50 testes automáticos da API, ataques manuais nas portas REST e MCP (chave forjada, perfil forjado, injeção, caminho ../, limite, revogação: todos barrados), `consulta` 313 e `chat` 262 passando depois da mudança.
*O que falta:* a bateria de ataques de prompt pela porta pergunta (cerca de US$ 0,50), rodar atrás da Tailscale restringindo o `Host`, testar com um cliente MCP de verdade e abrir o PR. O código está na branch `feat/api-demo` (commit `2cc47b9`). Detalhes: `api/README.md` e o diário `sessoes/2026-11-15-rodrigo.md`.

**14. Site novo da empresa e fluxo para o chat.** O site institucional da Rafaella (React) foi trazido para a pasta `site-institucional/`, sem o histórico antigo da branch dela. Na tela **Testar o nosso sistema**, o botão leva direto ao **chat** (quem já tem conta cai na conversa) e há a linha "Sem conta ativa? **Criar conta** · Já tem conta? **Entrar**"; o link de criar conta abre a aba de cadastro do chat.
*O que falta:* o `./site/deploy.sh` para a aba de cadastro funcionar em produção, e **login com Google** (tarefa da Gabriella, depende de criar o Client ID no Google).

**15. Servidor de teste (VM) para o Lucas.** Máquina virtual `fornexia-srv` no PC do Rodrigo (Ubuntu 24.04, Docker, Tailscale). Falta compartilhar com o Lucas, fechar a segurança (tirar a chave de acesso temporária e o login por senha), criptografia e backup, e conferir se ela liga sozinha com o Windows.

## 14/11: o que foi acrescentado (pontos 1 a 12)

**1. Sanções federais (CEIS e CNEP).** Dois cadastros públicos da União com empresas punidas (23.667 e 1.845 registros em 13/11). *Importa:* uma empresa punida pela União saía como "não localizei", o que passava falsa tranquilidade. Agora o bot diz se há sanção, de que tipo, de quando a quando e **onde ela vale**.
*Conferido:* 300 sanções sorteadas bateram com o arquivo original, sem nenhuma diferença. Pessoa física fica só como código (hash), nunca com nome ou CPF. *Resultado nos três CNPJs:* nenhum tem sanção.

**2. Cadastro da Receita Federal.** Razão social, situação (ativa ou não), atividade, porte, matriz ou filial e município de um CNPJ, pela BrasilAPI (que repassa o cadastro da Receita; não é a Receita falando). *Importa:* responde "quem é essa empresa" mesmo sem nenhum contrato na base. Só 17 campos são guardados; **sócios, telefone, e-mail e endereço nunca são gravados**.
*Conferido:* a prova confere pelo "hash" do arquivo, e deixa de conferir se alguém alterar uma letra. *Achado:* o CNPJ 26.852.688/0002-02 é a **filial de Olinda da GRT Auditoria de Terceiros, nome fantasia "Bernhoeft GRT"**.

**3. Contratos federais por CNPJ.** Pela API do Portal da Transparência (precisa da chave, que já está configurada). É a **única rota oficial que consulta por fornecedor**. *Importa:* mostra contratos reais de qualquer empresa que venda ao governo federal.
*Resultado:* a **filial da Bernhoeft tem 2 contratos com a Receita Federal** (R$ 110.712,00 em 2021 e R$ 276.061,44 em 2024, com os valores finais depois dos aditivos mostrados à parte); a Ferreira Costa tem 1 contrato de 2014 (R$ 577,00); o MEI não tem nenhum. O contato do responsável pela compra, que é nome de pessoa, não é guardado.

**4. PNCP (contratos de Garanhuns).** Portal Nacional de Contratações Públicas. *Importa:* trouxe os **55 contratos reais de Garanhuns em 2026**, o que deixa a demonstração com dado local. *Limite:* o PNCP **não consulta por fornecedor** (só por órgão e período, no máximo 365 dias por vez), então ele amplia os contratos de um órgão, não resolve "qualquer CNPJ". Um contrato que esteja também no portal municipal contaria duas vezes.

**5. Busca pela marca (nome fantasia).** Buscar "bernhoeft" não achava nada, porque a razão social é "GRT Auditoria". Agora a busca olha também o nome fantasia. *Achado* da verificação com dado real.

**6. Perfil "Estado e União" e o plano do site.** O acesso é por plano: quem não tem a União **não enxerga nada federal** (testado com os dados e com os modelos). O plano "Único" do site agora inclui a União, e a tela escreve "Estado de Pernambuco, Município de Garanhuns e União (governo federal)". Os números liberados no terminal já tinham.
*Falta:* publicar na Hostinger (sem acesso hoje): primeiro o worker novo, depois o `setup.php`.

**7. Base de demonstração.** O banco do bot agora tem só **dado real e público**: 58 contratos (55 de Garanhuns e 3 da União), 25.491 sanções e 4 cadastros. *Atenção:* a base de exemplo (fictícia) deixou de ser a do bot; para voltar a ela há 3 passos no diário. Perguntas reais ao bot: contratos da Bernhoeft, cadastro e contrato da Ferreira Costa, o MEI sem sanção nem contrato, e os maiores contratos de Garanhuns responderam certo, com fonte.

**12. Nota de voz no WhatsApp.** Agora o bot entende áudio. A transcrição acontece **na própria máquina** (Whisper; o áudio não sai daqui, só o texto transcrito vai ao modelo, como qualquer pergunta), leva uns 3 a 4 segundos, e a resposta vem como a de uma pergunta de texto. *Importa:* é o jeito natural de usar no celular.
*O que já existia e o que faltava:* o código de áudio já estava no projeto, mas a máquina não tinha o ambiente de voz. Preparei o ambiente (com o ffmpeg **dentro** dele, sem instalar nada no Windows), baixei o modelo (464 MB) e ensinei o transcritor o vocabulário do projeto (Garanhuns, Bernhoeft, CEIS...). A nota de voz real que você mandou às 09:45 de hoje tinha caído em "Não consegui entender o áudio"; agora é transcrita certa.
*O risco que medimos:* **número falado sai errado** (um CNPJ truncado ou com dígito trocado levaria a outra empresa). Por isso: (a) o CNPJ falado precisa ter 14 números e o **dígito verificador tem de fechar**, senão o bot **não consulta** e pede para digitar; (b) a resposta começa com **"🎙️ Entendi: ..."**, para a pessoa ver o que foi ouvido.
*Conferido:* com 6 notas de uma voz natural do Windows, 2 CNPJs certos consultaram (a Bernhoeft respondeu com os 2 contratos), 1 com dígito errado e 1 truncado foram barrados. Com **3 notas reais** (a sua voz), "sanções" saía "sensações"; as palavras-chave do projeto no Whisper corrigiram (amostra pequena). Um defeito achado no caminho (acento chegando deformado, "sanÃ§Ãµes") foi corrigido.
*Primeiro teste real pelo celular (4 notas, 14/11 de manhã):* transcrição certa, **uma trava de CNPJ funcionando com voz de verdade** (o Whisper ouviu 13 números e o bot pediu para digitar) e respostas em 9 a 22 s. O teste mostrou dois pontos de melhoria que **não são da voz**: a pergunta "existe fornecedor com sanção?" gera 44 consultas e cobriu 43 de 49 fornecedores, e para um CNPJ fora da base o bot diz "não sei" quando o arquivo de sanções federais, completo, permitiria dizer "sem sanção federal registrada" (ver o diário).
*Falta:* **testar com voz humana pelo celular, em volume.** O passo a passo está em [`testar-audio-whatsapp.md`](testar-audio-whatsapp.md): 10 testes (inclusive barulho, nota longa, silêncio e dígito errado de propósito) e como conferir cada um nos registros. Há também `python chat/provas/voz_conferir.py <áudio>` para repetir a conferência de qualquer gravação sem celular e sem gastar modelo.

## Segurança e honestidade das respostas

**8. Dado da União fora do perfil (ataque AP-21).** Cinco ataques novos tentam arrancar sanção, cadastro ou contrato federal de quem não tem a União, e dado de outro estado ou de pessoa física de quem tem. *Resultado:* nenhum vazamento, com o Sonnet e com o DeepSeek Flash.

**9. Três defeitos achados e corrigidos na verificação.** (a) A resposta dizia "o cadastro de sanções é de 05/06/2025" para sanções que são de 14/11/2026: a data de Pernambuco valia para tudo; agora cada ente mostra **a sua data de coleta**. (b) Campos vazios faziam o modelo comentar "a fonte não informa multa" sobre algo que a fonte nem tem; agora campos vazios **somem**. (c) Contrato sem valor aparecia no topo da lista dos "maiores"; agora vai para o fim.
*Por que importa:* o projeto promete **não dizer o que não sabe**; estes eram três jeitos de dizer errado sem querer.

## Acesso e configuração

**10. Números liberados no bot e a chave da API.** Três números foram liberados no WhatsApp pelo comando do dono (`acesso.ts`), e a chave da API do Portal da Transparência foi criada e testada. O passo a passo está em [`chave-api-portal-transparencia.md`](chave-api-portal-transparencia.md). Nenhum dos dois entra no git.

## Como foi medido

**11. Testes e medições com os modelos.**
- Testes automáticos de 14/11: `consulta` 313 OK, `chat` 262 OK (12 pulados no Windows; 20 deles são só da voz), site 82 e 33 OK, todos passando.
- Bateria de ataques (Sonnet e Flash): 9 reprovações na primeira rodada, **todas explicadas** (8 pelo defeito (b) e 1 por uma pergunta mal escrita por nós); depois das correções, **0 reprovações** nos 12 casos refeitos.
- Subconjunto do benchmark (59 perguntas): **Sonnet 57/59 e Flash 57/59**, aprovados. Antes de achar a causa chegou a dar 40/59, por um problema de configuração do ambiente, não dos modelos.
- Cada parte nova passou por "mutações": quebramos o código de propósito para ver se algum teste percebe. Todas foram percebidas (uma só depois de escrevermos o teste que faltava).

## 13/11: o que já tinha sido feito (resumo)
- **Ataques de prompt rodando sozinhos:** 41 ataques e 2 conversas longas contra os 4 modelos, com **0 vazamento de dado**; uma falha real de modelo (resposta "sim/não" sobre o que está fora do plano) levou à **regra 12**, que baixou a falha para 0 de 30.
- **Prova aberta pelo código:** a evidência do que a resposta cita é aberta automaticamente, sem depender do modelo lembrar.
- **Busca por texto:** acha fornecedor e contrato sem acento e com um erro de digitação.
- **Custo do cache de prompt medido:** nenhuma opção do `claude -p` reduz o custo; a saída seria a API direta, e só compensa com volume.

## O que ficou pendente
- **Publicar na Hostinger** (precisa de acesso): worker novo antes, `php site/setup.php` depois.
- **Repetir** o catálogo completo de ataques e as conversas (só os casos afetados foram refeitos) e o benchmark de 150 perguntas.
- **Mais órgãos no PNCP** (hoje só a Prefeitura de Garanhuns) e evitar a contagem dupla com o portal municipal.
- **MEI:** a razão social de um empresário individual traz o nome da pessoa (é dado público no cadastro). Decisão do dono: **manter**.
- **Áudio no WhatsApp:** feito e testado com voz sintética (ponto 12). **Falta mandar notas de voz reais pelo celular** para saber a taxa de erro de verdade.
- **N033 e N034** do benchmark (razão social por CNPJ): decisão do dono sobre a prova.

## Roteiro de demonstração (uns 5 minutos)
Perguntas para fazer ao bot, na ordem, e o que cada uma mostra.
1. **"Quais contratos federais tem a Bernhoeft, CNPJ 26.852.688/0002-02?"**: dado real de uma empresa conhecida, com dois valores (inicial e final) que não se somam e a fonte de cada contrato.
2. **"Me fale sobre o CNPJ 10.230.480/0001-30"**: cadastro da Receita, contrato federal e "nenhuma sanção", dizendo a data da coleta.
3. **"O CNPJ 27.756.971/0001-12 tem alguma sanção ou contrato?"**: o bot diz que **não encontrou na base e que isso não prova que não exista**.
4. **"Quais são os maiores contratos de Garanhuns?"**: 55 contratos reais, os três primeiros conferidos na fonte.
5. **Mostrar uma fonte:** abrir a evidência e mostrar que o arquivo guardado confere com o hash.
6. **(Opcional) Isolamento:** com um número de plano sem União, pedir as sanções federais; o bot não enxerga.
7. **(Voz) Mandar uma nota de voz** (siga o [passo a passo](testar-audio-whatsapp.md)) dizendo "Quais contratos tem o CNPJ dois seis, oito cinco dois, seis oito oito, zero zero zero dois, zero dois" (o CNPJ da Bernhoeft, **falado em grupos de dígitos**): o bot começa com "🎙️ Entendi: ..." e responde. Depois, de propósito, falar um dígito errado: o bot **recusa consultar** e pede para digitar.
