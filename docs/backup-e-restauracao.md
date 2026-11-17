# Backup e restauração: subir o servidor em outro notebook

Objetivo: se o computador onde o FornexIA roda parar de funcionar, outro notebook assume em cerca de 30 minutos, com os mesmos segredos,
os mesmos dados e o mesmo grafo. Tudo vem de **um arquivo cifrado** (`fornexia-AAAAMMDD-HHMMSS.fxbak`) e do código no GitHub.

Ferramenta: [`scripts/backup.py`](../scripts/backup.py). Só biblioteca padrão e `cryptography` (já está no `requirements.txt`).

## 1. O que o backup guarda

| Entra | Por quê |
|---|---|
| `.env`, `google-sa.json`, `api/chaves.json` | Segredos. Não estão no git e não dá para refazer sem pedir tudo de novo (chaves de API, conta de serviço, chaves de clientes). |
| `dados/` (inclui `dados/alertas/`) | Captura dos portais, cara de refazer (limites das APIs), e as assinaturas de alerta com e-mails de clientes. |
| Grafo do Neo4j | `neo4j-admin database dump`, com o contêiner parado por alguns segundos. É o que o agente e a API consultam. |
| Estado do WhatsApp (`~/.claude/channels/whatsapp-hackathon/`, sem a pasta `midia/`) | Sessão pareada e lista de acesso. Opcional (`--sem-whatsapp`). |

| Não entra | Onde está |
|---|---|
| O código | GitHub. A restauração usa o `git clone`. |
| O banco do site (MariaDB, contas e perguntas) | Na hospedagem. O `site/deploy.sh` guarda um backup dele no servidor (`~/backups-fornexia/`, os 10 últimos) antes de cada publicação. |
| Mídia do WhatsApp, `logs/` | Descartáveis e grandes. |

O backup contém segredos e dados pessoais (e-mails de clientes). Por isso ele é **sempre cifrado**: AES-256-GCM, chave derivada da senha
com scrypt. Senha errada, arquivo adulterado ou cortado: a restauração recusa e **não escreve nada**.

## 2. Regras da senha

- **Deixe o script gerar a senha** (`criar --gerar-senha`). Ela é aleatória, de 160 bits, no formato `ABCD-EFGH-...` (32 letras e números, sem os que se confundem). Uma senha inventada por pessoa é bem mais fraca.
- **Guarde a senha em dois lugares:** no **Gerenciador de Senhas do Google** da conta da empresa (abrir exige o código do Authenticator) e **numa cópia no papel**, em lugar seguro. Se o celular e o computador se perderem juntos, o papel salva o backup.
- **Quem perde a senha perde o backup**: não há recuperação.
- Nunca escreva a senha no `.env`, no diário, em commit ou em chat.
- O código de 6 números do Authenticator **não pode** ser a senha do backup: ele muda a cada 30 segundos (o arquivo não abriria depois) e tem só 1 milhão de combinações (quem roubasse o arquivo testaria todas em segundos). O Authenticator protege a **conta** onde a senha e o arquivo ficam.
- Guarde o arquivo `.fxbak` **fora do computador** (outro PC, nuvem, pendrive), por exemplo no Google Drive da conta da empresa. Um backup no mesmo disco não protege contra o disco.

## 3. Fazer o backup (no computador atual)

Na raiz do projeto, com a venv ativa e o Docker ligado:

```bash
# Windows (PowerShell):  .venv\Scripts\python scripts\backup.py criar --gerar-senha
# Linux:                 .venv/bin/python scripts/backup.py criar --gerar-senha
```

Com `--gerar-senha`, o script:
1. gera a senha e a **mostra uma única vez**;
2. espera você **guardá-la** (Gerenciador de Senhas e papel) e **digitá-la de volta** para provar que guardou (3 tentativas; se errar todas, não cria backup);
3. **limpa a tela**, para a senha não ficar no histórico do terminal, e só então cria o backup.

Sem `--gerar-senha`, ele pede uma senha sua duas vezes (12 caracteres ou mais). Para **restaurar**, digite a senha guardada: vale com ou sem hífens, em maiúsculas ou minúsculas.
O `--gerar-senha` precisa de um terminal e não combina com `BACKUP_SENHA`.

Opções: `--destino PASTA` (padrão: `~/backups-fornexia`, ou a variável `BACKUP_DESTINO`), `--sem-grafo`, `--sem-dados`,
`--sem-whatsapp`, `--manter N` (guarda só os N mais novos; padrão 10).

Medido com o grafo real (68.831 nós, 119.934 relações): arquivo de 17 MB, cerca de 30 segundos. O **Neo4j fica parado durante a cópia**
(alguns segundos a meio minuto): faça fora de uma demonstração. Se o contêiner já estava parado, o script não o liga.

No fim ele mostra o **sha256 do arquivo**. Depois de copiar para fora, confira que o número é o mesmo.

Para ver se o arquivo está bom, sem mexer em nada:

```bash
python scripts/backup.py verificar ~/backups-fornexia/fornexia-AAAAMMDD-HHMMSS.fxbak
```

Faça isso de vez em quando: **backup que nunca foi verificado não é backup**.

### Agendar (opcional)

Tarefa agendada não tem terminal, então ela **não usa `--gerar-senha`**: use a senha que o primeiro backup manual gerou, na variável `BACKUP_SENHA`.
O script lê a senha dessa variável quando não há terminal. Isso deixa a senha no ambiente do usuário que roda a tarefa: protege
o arquivo `.fxbak` se ele vazar, mas não protege contra quem já tem acesso à sua conta no computador (essa pessoa já teria o `.env`).

```bash
# Linux (cron, todo dia às 3h):  0 3 * * *  cd /caminho/hackathon && BACKUP_SENHA='...' .venv/bin/python scripts/backup.py criar
# Windows: Agendador de Tarefas > nova tarefa diária > programa: .venv\Scripts\python.exe, argumentos: scripts\backup.py criar,
#          iniciar em: a raiz do projeto, com BACKUP_SENHA definida como variável de ambiente do usuário.
```

Depois de cada backup, copie o arquivo para fora (por exemplo, uma pasta sincronizada com a nuvem como `--destino`).

## 4. Subir no outro notebook, passo a passo

Faça um ensaio **antes** de precisar. Reserve uns 30 minutos, de preferência antes de 18/11.

### 4.1 Preparar o notebook (uma vez)

Siga as etapas 2, 3 e 4 de [`rodar-no-windows-e-no-linux.md`](rodar-no-windows-e-no-linux.md): Docker, Git, Python (a venv e o `pip install -r requirements.txt`).
Para o WhatsApp, também o `bun` (etapa 11). Não crie o `.env` à mão: ele vem do backup.

```bash
git clone https://github.com/Luks108/hackathon.git
cd hackathon
git checkout <branch>        # a do manifesto: o `verificar` mostra a branch e o commit do backup
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -r requirements.txt     Linux: .venv/bin/python -m pip install -r requirements.txt
```

### 4.2 Trazer o arquivo e conferir

1. Copie o `.fxbak` para o notebook.
2. Compare o sha256 com o que o script mostrou na hora do backup.
3. `python scripts/backup.py verificar ARQUIVO`: deve dizer **"Backup íntegro e senha correta"** e mostrar a data, o commit, o número de arquivos e de nós do grafo.

### 4.3 Restaurar

Com o Docker ligado, na raiz do projeto:

```bash
python scripts/backup.py restaurar ARQUIVO
```

O que ele faz, em ordem:
1. Decifra e confere cada arquivo pelo hash. Se algo estiver errado, para antes de escrever.
2. Confere **tudo o que poderia atrapalhar antes de escrever qualquer coisa**: arquivo que já existe e é diferente, ou um Neo4j que já tem dados. Se houver, recusa e lista. Para seguir mesmo assim: `--forcar` (o arquivo antigo fica ao lado, com `.antes-AAAAMMDD-HHMMSS`).
3. Restaura `.env`, chaves, `dados/` e o estado do WhatsApp.
4. Cria o contêiner do Neo4j pelo `docker compose` do projeto, carrega o grafo, liga e **confere o número de nós** com o do backup.

Se aparecer "Docker não está ligado", ligue-o. Para restaurar só os arquivos e refazer o grafo depois: `--sem-grafo`, e então
`python coleta/carregar_neo4j.py --zerar` (mais lento, a partir de `dados/`).

### 4.4 Ligar tudo

```bash
# Windows: ligar-tudo.bat        Linux: ./ligar-tudo.sh
```

(sobe os bancos, o site local, o gateway do WhatsApp e o worker, por último.) Para ver só o estado: `./ligar-tudo.sh --status`.

### 4.5 Conferir que está tudo certo

- [ ] `restaurar` terminou com "Grafo: N nós (no backup: N) OK".
- [ ] `python chat/worker.py --simular "Existe alguma sanção para algum fornecedor?"` responde com fonte.
- [ ] No site publicado, o chat responde (o worker novo atende a fila).
- [ ] Se a API for usada: `python api/servidor.py` sobe e `GET /v1/saude` responde (`api/chaves.json` veio do backup).
- [ ] Se os alertas forem usados: `python alertas/cli.py listar` mostra as assinaturas.
- [ ] WhatsApp: `bun canal-whatsapp/acesso.ts status` diz se está conectado (ver 5.2).

## 5. A troca: o computador caiu, o outro assume

### 5.1 Ordem (para não haver dois atendendo)

O worker só faz conexões de saída: ele busca a pergunta na fila do site e devolve a resposta. Por isso, **trocar de máquina é subir o worker na nova**, com
o mesmo `.env` (a mesma `WORKER_KEY`) e **sem `API_BASE`**, para ele apontar ao site publicado.

1. Confirme que o computador antigo está **mesmo fora**. Se ele só estiver lento ou sem internet, desligue o worker e o gateway nele (`parar-tudo`). Dois workers no mesmo site disputam a fila.
2. Restaure o backup mais recente na máquina nova (seção 4.3) e ligue tudo (4.4).
3. O que chegou depois do último backup (novas assinaturas de alerta, contas do site) se perde ou vem de outro lugar: as **contas do site ficam na hospedagem** e não dependem do computador. O grafo e os alertas voltam ao estado do backup. Por isso, quanto mais recente o backup, menos se perde.

### 5.2 WhatsApp

A sessão do WhatsApp só pode estar **em um lugar por vez**. Se o computador antigo realmente morreu, a sessão restaurada normalmente volta a funcionar.
Se o WhatsApp mostrar "desconectado" ou "sessão encerrada", pareie de novo na máquina nova (`canal-whatsapp/parear.sh`, que pede o número na hora).
Não ligue o gateway nas duas máquinas ao mesmo tempo: o WhatsApp derruba uma das sessões.

### 5.3 Voltar para o computador principal

Faça um backup na máquina que está atendendo, desligue o gateway e o worker dela, restaure no computador principal com `--forcar` e ligue tudo lá.

## 6. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `senha incorreta, ou o arquivo foi alterado` | Senha errada, ou o arquivo se corrompeu na cópia. Compare o sha256. Tente outra cópia do backup. |
| `arquivo truncado` | A cópia foi interrompida. Copie de novo. |
| `N item(ns) já existem e são diferentes` | A máquina já tem um `.env` ou um grafo. Se for a máquina certa, use `--forcar` (o antigo fica ao lado). |
| `o Docker não está ligado` | Ligue o Docker Desktop (Windows) ou `sudo systemctl start docker` (Linux). |
| `a porta 7689 está em uso` ao subir o Neo4j | Outro serviço usa a porta. Feche-o ou ajuste a porta no `infra/docker-compose.yml` e o `NEO4J_URI` no `.env`. |
| `número de nós difere` | Não use esse grafo. Rode a restauração de novo; se repetir, restaure com `--sem-grafo` e refaça com `coleta/carregar_neo4j.py --zerar`. |
| `não restaura esta versão` / `formato desconhecido` | Use o `scripts/backup.py` do mesmo commit que criou o arquivo. |

## 7. O que foi testado e o que não foi

**Testado:**
- 35 testes automáticos (`python -m unittest discover -s scripts/testes`): cifra (várias partes, arquivo vazio, senha errada, byte alterado, cortado, emendado, bloco removido), criação, verificação, restauração, conflito sem `--forcar`, idempotência, rotação, pacotes forjados (caminho perigoso, link simbólico, arquivo fora do manifesto, conteúdo alterado), a ordem das chamadas ao Docker (parar, copiar e religar mesmo se a cópia falhar) e a senha gerada (formato, aparece uma vez, tela limpa, confirmação obrigatória, valendo com hífens e minúsculas).
- 15 mutações no script (por exemplo, não checar conflito, não conferir o hash, não religar o Neo4j, aceitar caminho perigoso, aceitar qualquer confirmação da senha gerada, gerar senha fraca): todas derrubam algum teste.
- **Docker de verdade**, numa cópia do volume do grafo real (o real não foi tocado): `criar` parou, copiou e religou o contêiner; `restaurar` num "outro notebook" vazio (pasta nova, volume novo, `docker compose`) devolveu **68.831 nós e 119.934 relações, idênticos** aos da origem, em cerca de 30 s. Uma segunda restauração por cima recusou sem `--forcar`.

**Não testado:**
- Restauração numa **segunda máquina física** e em **Linux**: o teste usou o mesmo computador, com nomes e portas diferentes.
- A tarefa **agendada** (cron e Agendador de Tarefas): só descrita.
- O `--gerar-senha` num **terminal de verdade**: os testes simulam o terminal e a digitação. Rode uma vez à mão e confira que a tela é limpa.
- A restauração do **estado do WhatsApp** com a sessão em uso (o teste automático cobre os arquivos, não o pareamento real).
- O tempo de restaurar `dados/` inteiro grande (81 MB hoje) em disco lento.
