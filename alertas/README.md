# Alertas por e-mail

Avisa o cliente por e-mail quando muda algo nos fornecedores (CNPJs) que ele acompanha: sanção nova, atualizada ou que deixou de constar (CEIS, CNEP e cadastro estadual),
contrato novo ou alterado, e mudança da situação cadastral na Receita. Versão de demonstração (arquivos JSON em `dados/alertas/`, que o git ignora).

**Por e-mail e não por WhatsApp:** o WhatsApp só deixa a empresa começar a conversa com modelos aprovados pela Meta e cobra por conversa. O e-mail não tem essa barreira.

## Como funciona

```
cron diário: recoleta (coleta/federal.py ...) -> extrai -> carrega no Neo4j -> python alertas/cli.py verificar
                                                                                    |
                          para cada assinatura: lê o grafo COM O PERFIL DELA -> compara com a foto da última vez -> e-mail
```

- Não consulta o portal: lê o grafo, pelas **mesmas consultas do agente**, com o perfil da assinatura. O cliente nunca é avisado de algo que o plano dele não enxerga.
- No **CLI**, a primeira verificação só tira a linha de base. Na ponte do site, envia o retrato inicial identificado como tal, sem apresentar registros antigos como novidade.
- A foto só é gravada **depois** que o e-mail saiu. Se o envio falha, a próxima rodada tenta de novo.
- CNPJ que tinha dados e agora não tem nenhum (recarga ou queda da base) **não** vira "tudo foi removido": fica sem aviso e a foto anterior é mantida.
- **Um e-mail por assinatura por rodada**, com todos os avisos juntos. O CLI usa código de cancelamento; assinaturas do site levam o link de Minha conta.
- O texto diz o que a fonte registra, com o endereço e a data da captura (a evidência), e que **uma ocorrência não prova irregularidade**.
- Texto vindo dos portais entra no e-mail limpo (sem quebra de linha) e escapado no HTML; nada de fora vai para o assunto nem para os cabeçalhos.

## E-mail verificado (regra de entrada)

Só recebe aviso quem **provou que o e-mail é dele**: entrou com o Google (que só entrega e-mail verificado) ou confirmou um código enviado ao endereço.
Quem se cadastrou por senha, sem verificar, **não pode marcar acompanhamentos** no site; se tentar, é levado a verificar. A mesma trava existe aqui no monitor,
como segunda camada: assinatura sem `email_verificado` não é lida nem enviada, e a linha de base nasce só depois da confirmação (não chega o passado inteiro de uma vez).
Cada assinatura guarda `origem` (`cli`, `site`, `google`), `usuario_id` (o usuário do site) e `consentimento_em` (quando o e-mail foi confirmado: serve de registro de consentimento).

## Comandos

```bash
python alertas/cli.py assinar EMAIL PERFIL CNPJ [CNPJ ...] [--verificado]   # perfis: python consulta/perfis.py (perfil com dado pessoal é recusado; só CNPJ, não CPF)
python alertas/cli.py confirmar ID_OU_EMAIL                  # marca o e-mail como verificado (sem isso nenhum aviso sai)
python alertas/cli.py listar
python alertas/cli.py verificar [--ensaio]                   # --ensaio mostra o que seria enviado, sem enviar nem gravar
python alertas/cli.py cancelar CODIGO_OU_EMAIL
python alertas/cli.py enviar-teste EMAIL                     # confere o canal de e-mail configurado
```

Precisa do Neo4j no ar (`NEO4J_URI`, `NEO4J_SENHA`, `BRUTO`), como o agente. Sem `ALERTAS_SMTP_HOST`, os e-mails viram arquivos `.eml` em `dados/alertas/saida/`.
Variáveis do e-mail real: ver `.env.exemplo` (seção "Alertas por e-mail").

## Ensaio completo (com o Neo4j de teste)

```bash
docker run -d --rm --name neo4j-teste-api -p 127.0.0.1:7699:7687 -e NEO4J_AUTH=neo4j/SENHA neo4j:5.26.0-community
export NEO4J_URI=bolt://127.0.0.1:7699 NEO4J_SENHA=SENHA BRUTO=fixtures/exemplo/bruto ALERTAS_PASTA=/tmp/alertas-demo
python coleta/carregar_neo4j.py --zerar --exemplo

python alertas/cli.py assinar financeiro@empresa-exemplo.com.br estado-exemplo 33333333000133 --verificado
python alertas/cli.py verificar                              # foto de hoje, nenhum aviso
python alertas/simular.py sancao-nova --banco-de-teste       # a "fonte mudou" (só no ente fictício ex-estado)
python alertas/cli.py verificar --ensaio                     # mostra o aviso
python alertas/cli.py verificar                              # envia (grava o .eml)
python alertas/simular.py restaurar --banco-de-teste         # desfaz
```

`simular.py` recusa rodar sem `--banco-de-teste` e recusa o banco padrão do bot (porta 7689). Outras simulações: `sancao-encerrada`, `contrato-novo`.

## Testes

```bash
NEO4J_URI=... NEO4J_SENHA=... python -m unittest discover -s alertas/testes -v
```

46 testes: assinaturas (e-mail, CPF, limite, cancelar), comparação (sanção nova, alterada, removida; contrato; cadastro), entrega (arquivo e um SMTP de brincadeira numa
porta local), injeção de cabeçalho e HTML, falha no envio (e e-mail que saiu sem gravar o horário), modo de envio escrito errado, recarga da base, consulta cheia (50 itens),
contratos de mesmo número, e-mail verificado (trava, linha de base ao confirmar, conta Google, pedido de terceiro) e, com o Neo4j de teste, o isolamento entre perfis. Sem o banco, 3 são pulados.
Nenhum teste manda e-mail de verdade nem gasta crédito de modelo.

## Limites conhecidos

- **Consulta cheia:** as consultas do agente devolvem no máximo 50 contratos e 50 sanções por fornecedor. Quando uma volta cheia, a foto é só uma janela: o que já se conhecia fica na foto,
  então nada vira "removido" nem "novo" por ter saído ou voltado à janela. O custo é que remoção e mudança de itens fora da janela não são vistas (o relatório da rodada avisa).
- **Pedido sem verificar:** quem pede aviso para um e-mail que já tem assinatura verificada é recusado; quem confirma o e-mail descarta o que foi pedido antes sem confirmação.
- **Cancelar por e-mail e confirmar por e-mail** (`cancelar`, `confirmar`) são do CLI local. Na ponte com o site, exigir o código aleatório, nunca só o e-mail.
- **CLI com arquivos JSON sem trava:** não execute dois comandos CLI de escrita ao mesmo tempo. O site guarda os acompanhamentos no MariaDB; sua ponte tem estado separado e trava local.
- `ALERTAS_ENVIO` com valor diferente de `arquivo` ou `smtp` falha em vez de cair em arquivo.

## O que não está feito

- O cadastro pelo site e o cancelamento pela conta estão implementados; a publicação depende do merge e da instalação do monitor.
- **Consentimento e LGPD:** a tela explica os avisos antes da inclusão e oferece cancelamento; revisão jurídica e política de retenção continuam pendentes.
- **Recoleta agendada** (cron/systemd): este módulo só compara; a coleta que alimenta o grafo é a de sempre (`coleta/`).
- **Canal definitivo de e-mail:** o envio real já foi provado pelo SMTP de uma conta Gmail com senha de app (variáveis `ALERTAS_SMTP_*` no `.env`; veja `.env.exemplo`). Limite de cerca de 500 por dia e remetente `@gmail.com`. Para clientes de verdade falta um endereço no domínio da empresa (SPF/DKIM) e o teste de entrega a um endereço externo.
- **Aviso por webhook** para o sistema do cliente (combina com a API para IAs) e **resumo semanal**.
- Os avisos valem a atualização da fonte: o cadastro de sanções de PE é de 05/06/2025, então para ele não haverá novidade.


## Acompanhamento pela conta do site

Em **Minha conta → Acompanhar fornecedores**, contas com plano ativo e e-mail confirmado podem incluir até dez CNPJs válidos.
O botão Parar de acompanhar cancela o item. A API exige sessão, CSRF e propriedade da conta.
`GET /api/worker/acompanhamentos`, protegido por `X-Worker-Key`, só devolve contas com plano ativo e e-mail confirmado.
A migração `site/migrar-acompanhamentos.php` é aditiva, repetível e executada pelo deploy.

A ponte `alertas/ponte_site.py` busca a lista atual a cada 60 segundos e usa o monitor existente. Envia um **retrato inicial** identificado
como tal, com os registros disponíveis e suas evidências; nas rodadas seguintes, só envia quando algo muda. Uma falha no SMTP não avança
a foto, permitindo nova tentativa. Sem registros, o retrato inicial explica os limites da amostra. O monitor não recaptura portais:
a atualização depende da coleta e carga do grafo. Não é monitoramento em tempo real das fontes.

O perfil deve corresponder exatamente aos entes do plano e não permitir dados pessoais. Plano sem perfil correspondente não é atendido.
Mudança de plano ou endereço começa outra linha de base. Cancelamento remove a foto; reincluir o mesmo CNPJ gera outro retrato,
mesmo que a remoção e inclusão ocorram entre duas rodadas. Uma falha na consulta ao site impede envios daquela rodada.
A lista é consultada no início da rodada; um cancelamento simultâneo pode coincidir com um envio que já esteja em andamento.

O estado local fica em `dados/alertas-site/estado.json`, separado das assinaturas CLI, com modo 600 e escrita atômica. A trava do monitor
impede dois processos locais de enviarem a mesma rodada. Execute a ponte em **uma máquina**; não há coordenação entre computadores.
Uma queda entre a aceitação do SMTP e a gravação da foto pode repetir um aviso; SMTP não garante entrega exatamente uma vez.

A ponte reutiliza `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASS` e `MAIL_FROM` do login, sem sobrescrever
as opções explícitas `ALERTAS_SMTP_*` e `ALERTAS_DE`. Exige modo SMTP para execução real; `--ensaio` não envia nem grava.
Os logs mostram apenas contagens e tipos de falha, sem destinatários ou segredos.

Depois do merge e do deploy do site, no clone Linux que contém a `.env` de produção:

```bash
.venv/bin/python alertas/ponte_site.py --ensaio   # consulta real, sem enviar nem gravar
./alertas/instalar-servico.sh                    # serviço da conta Linux atual
systemctl --user status fornexia-alertas
journalctl --user -u fornexia-alertas --since today
# Para desligar:
systemctl --user disable --now fornexia-alertas
```

O serviço requer o notebook ligado e conectado, como o WhatsApp e o MCP. Para funcionamento após reiniciar sem login,
confira o linger da conta (`loginctl show-user "$USER" -p Linger`). Não execute este instalador no servidor de outro worker.
Os testes da ponte e do monitor são incluídos em `scripts/testes_ci.py`, além dos testes PHP de autenticação e acompanhamento.
