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
- A **primeira verificação** de um CNPJ só tira a foto (linha de base). Senão tudo o que já existia viraria "novidade".
- A foto só é gravada **depois** que o e-mail saiu. Se o envio falha, a próxima rodada tenta de novo.
- CNPJ que tinha dados e agora não tem nenhum (recarga ou queda da base) **não** vira "tudo foi removido": fica sem aviso e a foto anterior é mantida.
- **Um e-mail por assinatura por rodada**, com todos os avisos juntos. Cada e-mail leva o código de cancelamento.
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
- **Arquivos JSON sem trava:** o cron `verificar` e o cadastro pelo site gravando ao mesmo tempo podem perder uma atualização. A tabela no MariaDB resolve.
- `ALERTAS_ENVIO` com valor diferente de `arquivo` ou `smtp` falha em vez de cair em arquivo.

## O que não está feito

- **Cadastro pelo site** e link de cancelamento que se clica (hoje: código e CLI). A troca natural é uma tabela no MariaDB do site e uma página de cancelar.
- **Consentimento e LGPD:** guardar o e-mail exige base legal e descadastro simples. Falta o texto de consentimento no cadastro.
- **Recoleta agendada** (cron/systemd): este módulo só compara; a coleta que alimenta o grafo é a de sempre (`coleta/`).
- **Canal definitivo de e-mail:** o envio real já foi provado pelo SMTP de uma conta Gmail com senha de app (variáveis `ALERTAS_SMTP_*` no `.env`; veja `.env.exemplo`). Limite de cerca de 500 por dia e remetente `@gmail.com`. Para clientes de verdade falta um endereço no domínio da empresa (SPF/DKIM) e o teste de entrega a um endereço externo.
- **Aviso por webhook** para o sistema do cliente (combina com a API para IAs) e **resumo semanal**.
- Os avisos valem a atualização da fonte: o cadastro de sanções de PE é de 05/06/2025, então para ele não haverá novidade.
