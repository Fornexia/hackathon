# 2026-11-16: rodrigo-backup

- **Quem:** rodrigo-backup (Rodrigo Santana, com Claude Code)
- **Branch e commit de partida:** `feat/backup-restauracao` em `b7dc44b` (= `feat/portabilidade-windows-linux`), no worktree `hackathon-backup`. Arquivo à parte do diário principal do dia (`2026-11-16-rodrigo.md`, na branch `feat/alertas-email`) para os dois não colidirem no merge.
- **Máquina e ambiente:** Windows 11, Docker Desktop, Python 3.14 (venv do projeto, com `cryptography`), sem outra máquina física para o ensaio.

## Resumo

Pedido do dono: se o computador parar de funcionar, outro notebook precisa assumir (a ideia do celular foi trocada por backup e restauração portáteis). Entregues `scripts/backup.py` (criar, verificar e restaurar um arquivo cifrado com segredos, `dados/`, estado do WhatsApp e o grafo do Neo4j) e o guia `docs/backup-e-restauracao.md` com o passo a passo para o outro notebook. Testado com Docker de verdade numa cópia do volume do grafo real: restauração idêntica. **Tudo só no disco, sem commit e sem push** (aguardando o OK do dono).

## Feito

- `scripts/backup.py`: `criar`, `verificar`, `restaurar`. Cifra AES-256-GCM em pedaços de 1 MiB com scrypt (N=2^15), cabeçalho e marca de "último pedaço" autenticados (corte, emenda, bloco removido e byte alterado são detectados). Manifesto com sha256 de cada arquivo, commit e contagem de nós. Restaurador recusa caminho perigoso, link simbólico, arquivo fora do manifesto e conteúdo alterado, e **confere conflitos antes de escrever qualquer coisa** (`--forcar` guarda o antigo ao lado). Grafo: `neo4j-admin database dump/load` por contêiner descartável e `docker cp`, sem montagem de pasta do host (funciona igual no Windows e no Linux); religa o Neo4j mesmo se a cópia falhar; confere o número de nós depois de restaurar.
- **`criar --gerar-senha`** (pedido do dono, em vez de usar o código de 6 números do Authenticator, que não serve como senha: muda a cada 30 s e tem só 1 milhão de combinações): gera 160 bits aleatórios (32 caracteres base32, em grupos de 4), mostra uma vez, só segue depois que a pessoa a digita de volta (3 tentativas) e limpa a tela. A senha vale digitada com ou sem hífens, em maiúsculas ou minúsculas (`normalizar_senha`; qualquer outra senha vale exatamente como digitada). Recusa sem terminal e com `BACKUP_SENHA`. O guia manda guardar no Gerenciador de Senhas da conta da empresa (protegido pelo Authenticator) e numa cópia no papel.
- `scripts/testes/test_backup.py`: 35 testes.
- `docs/backup-e-restauracao.md`: o que entra e o que não, regras da senha, como agendar, **passo a passo no outro notebook**, a troca (um worker por vez, WhatsApp só em um lugar), problemas comuns, o que foi e o que não foi testado.
- `requirements.txt`: `cryptography==50.0.2` (estava instalada na venv, mas nenhum pacote do projeto a exigia). `README.md`: uma linha na tabela de pastas.

## Verificado (e como)

- `python -m unittest discover -s scripts/testes` → **35 testes OK** (2026-11-16, Windows).
- **15 mutações, todas pegas** (aceitar nome perigoso, não checar conflito, não conferir hash, não religar o Neo4j, incluir a mídia, aceitar link simbólico, sem a marca de último bloco, rotação que não apaga, grafo existente sem confirmação; e, do `--gerar-senha`: aceitar qualquer confirmação, não normalizar a senha digitada, não limpar a tela, aceitar com `BACKUP_SENHA`, gerar senha fraca, aceitar sem terminal). A do link simbólico só foi pega depois de o teste passar a usar um link para um arquivo válido do próprio pacote (antes passava por acaso).
- **Docker real, sem tocar no Neo4j real:** copiei o volume do grafo para um volume de teste (montagem só leitura na origem), subi um contêiner de origem sobre a cópia (68.831 nós e 119.934 relações), `criar` parou, copiou e religou (arquivo de 17,1 MB), `verificar` OK, `restaurar` numa pasta vazia com `docker compose` (nomes e portas de teste) devolveu os mesmos 68.831 nós e 119.934 relações em cerca de 27 s; uma segunda restauração por cima recusou sem `--forcar`. Tudo removido depois; o contêiner real continuou `exited`, como estava.

## Não verificado

- Restauração em uma **segunda máquina física** e em **Linux** (o ensaio foi no mesmo computador, com nomes e portas diferentes).
- Tarefa **agendada** (cron e Agendador de Tarefas): só descrita no guia.
- O `--gerar-senha` num **terminal de verdade** (os testes simulam o terminal e a digitação): rodar uma vez à mão e conferir que a tela é limpa.
- Restauração do **estado do WhatsApp** com sessão real em uso (testado só como arquivos).
- Tempo de restaurar um `dados/` bem maior em disco lento.

## Decisões e motivo

- **Backup e restauração portáteis em vez de servidor no celular:** Android mata processos em segundo plano, não tem Docker e o projeto é montado em torno do Docker Compose. O que protege de verdade é ter os dados e os segredos fora do computador e uma restauração ensaiada.
- **Um arquivo cifrado, não várias pastas:** carrega segredos e e-mails de clientes (LGPD). Cifra com `cryptography` em vez de zip com senha, que cifra mal e vaza os nomes dos arquivos.
- **Grafo por dump (`neo4j-admin`), com o contêiner parado:** a edição community não faz dump a quente. O custo é segundos a meio minuto sem grafo durante o backup; o contêiner volta sozinho.
- **Sem montagem de pasta do host nos contêineres do dump:** evita erro de permissão no Linux e de caminho no Windows (`docker cp` resolve os dois).
- **Restaurar nunca sobrescreve em silêncio:** conflito sem `--forcar` aborta antes de escrever; com `--forcar`, o arquivo antigo fica ao lado.

## Em aberto (por prioridade)

1. [ ] **Ensaiar a restauração num segundo notebook** (o do Lucas, por exemplo) antes de 18/11, seguindo a seção 4 do guia, e anotar o tempo real. (origem: 2026-11-16-rodrigo-backup)
2. [ ] Decidir **onde guardar o `.fxbak` fora do PC** e quem guarda a senha do backup (gerenciador de senhas). (origem: 2026-11-16-rodrigo-backup)
3. [ ] **Agendar** o backup diário (o guia traz os comandos) e verificar o arquivo de tempos em tempos. (origem: 2026-11-16-rodrigo-backup)
4. [ ] Abrir o PR de `feat/backup-restauracao` (base: `feat/portabilidade-windows-linux`) com o OK do dono. (origem: 2026-11-16-rodrigo-backup)
5. [ ] Se o worker passar a rodar na VM ou num servidor: incluir no guia a troca de `API_BASE` e a rede (Tailscale). (origem: 2026-11-16-rodrigo-backup)

## Resolvido de sessões anteriores

Nenhum.

## Armadilhas

- O `restaurar` por cima de uma máquina que já tem grafo **recusa** sem `--forcar`, de propósito: com `--forcar` ele apaga o grafo existente (o `.env` e os arquivos antigos ficam ao lado, o grafo não).
- Nunca teste a restauração do grafo com o `docker compose` do projeto na máquina que já tem o contêiner `hackathon-neo4j`: o nome do contêiner é fixo e ela cairia no volume real. O ensaio usou um compose copiado com nome, projeto e portas de teste.
- Quem perde a senha do backup perde o backup. Não há recuperação.
- Os testes de cifra são lentos (scrypt a cada chamada): cerca de 8 s no total.

## Próximo passo sugerido

Ensaiar o guia no segundo notebook e só então agendar o backup diário.
