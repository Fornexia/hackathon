# Como testar a nota de voz no WhatsApp (passo a passo)

Para quem vai testar com o celular (Rodrigo, Lucas ou qualquer número liberado no bot). Tempo: cerca de 20 minutos.
Contexto e medições: [`testes-seguranca.md`](testes-seguranca.md) §2.11. Matriz geral do WhatsApp: [`whatsapp-ativacao.md`](whatsapp-ativacao.md) (teste T14).

**O que esperar, em uma frase:** o bot transcreve a nota **na própria máquina** (o áudio não sai daqui; o **texto** transcrito vai ao modelo, como qualquer pergunta digitada), escreve o que entendeu na primeira linha da resposta ("🎙️ Entendi: ...") e responde como a uma pergunta de texto. Se o **CNPJ falado não fechar** (menos ou mais de 14 números, ou dígito final errado), ele **não consulta** e pede para você digitar.

## Parte 1: antes de pegar o celular (5 minutos)

1. **Pré-voo.** Na raiz do projeto: `python chat/provas/whatsapp_preparar.py`. O fim tem de dizer `Pronto para o TESTE ponta a ponta:  SIM`, e o bloco **5. Áudio** tem de ter 4 linhas `[OK]` (venv, bibliotecas, ffmpeg, modelo). O aviso "mais de um processo de gateway" é normal no Windows (lançador e filho).
2. **Worker no ar.** A última linha de `logs/worker.log` tem de ser `worker no ar: ...`. Se não for, dê dois cliques em `ligar-tudo.bat` (ele só sobe o que falta).
3. **Seu número está liberado.** `cd canal-whatsapp` e `bun acesso.ts list`: o número do celular que vai mandar o áudio precisa aparecer em `allowFrom`. Se não estiver, `bun acesso.ts add 55DDDNUMERO` (só o dono faz isso, no terminal). Número fora da lista não recebe resposta nenhuma, de propósito.
4. **A base do bot hoje é a de demonstração (dado real):** contratos de Garanhuns, sanções federais, e a Bernhoeft e a Ferreira Costa. As frases abaixo foram escolhidas para ela.

**Teste sem celular (opcional, não gasta modelo):** `python chat/provas/voz_conferir.py arquivo.ogg` transcreve um áudio e diz o que o bot faria (o que ouviu, e se consultaria ou pediria para digitar). As notas que o bot já recebeu ficam em `%USERPROFILE%\.claude\channels\whatsapp-hackathon\midia\`; dá para repetir a conferência com elas.

## Parte 2: no celular (15 minutos)

Mande cada nota de voz **como nota de voz do WhatsApp** (segurando o microfone), no chat com o número do bot. Fale em ritmo normal, com o celular perto. Cada teste tem o que falar e o que deve acontecer.

| # | Fale | O que deve acontecer |
|---|---|---|
| **T1** | "Existe sanção para algum fornecedor?" | O bot reage com 👀, e a resposta começa com **"🎙️ Entendi: “Existe sanção para algum fornecedor?”"**, seguida da resposta. Confira se o "Entendi" é o que você disse (por exemplo, "sanção" não pode virar "sensação"). |
| **T2** | "Quais contratos tem o CNPJ **dois seis, oito cinco dois, seis oito oito, zero zero zero dois, zero dois**" (devagar, em grupos, com uma pequena pausa entre eles) | O "Entendi" traz o CNPJ, e a resposta é sobre a **GRT / Bernhoeft** com **2 contratos da Receita Federal** (R$ 110.712,00 e R$ 276.061,44, cada um com o valor final à parte). |
| **T3** | O mesmo do T2, mas terminando em **"zero três"** (dígito errado de propósito) | O bot **não consulta**. Responde "🎙️ Ouvi: ... Não vou consultar: o CNPJ que ouvi não fecha (o dígito final está errado) ... Pode digitar o CNPJ por texto?". |
| **T4** | "Me fale sobre o CNPJ **um zero, dois três zero, quatro oito zero, zero zero zero um, três zero**" | Cadastro da **Ferreira Costa & Cia** (ativa, Garanhuns), o contrato federal de 2014 e "nenhuma sanção". |
| **T5** | "Quais são os maiores contratos de Garanhuns?" | "Entendi" com **Garanhuns** certo (testamos: sem o vocabulário do projeto saía "garanhos"), e a lista com a **Konex** em primeiro lugar. |
| **T6** | O CNPJ da Bernhoeft **de uma vez, rápido, sem pausa** | **Pode ser barrado** ("o CNPJ que ouvi tem N números"): é o comportamento esperado, porque CNPJ lido em bloco costuma sair truncado. Anote se passou ou não. |
| **T7** | Repita o T2 **com barulho** (rua, carro, ventilador ligado) | Ou acerta, ou o bot pede para digitar. **Não pode** consultar uma empresa diferente da que você falou: se acontecer, é falha séria, guarde o áudio e avise. |
| **T8** | Uma nota **longa** (30 a 60 segundos), por exemplo: "Oi, bom dia, preciso saber se existe algum fornecedor com sanção que possa afetar os contratos públicos da prefeitura" | Responde, mas o tempo total é maior. Anote quantos segundos levou. |
| **T9** | Mande **silêncio** (segure o microfone sem falar uns 3 segundos) | "Não consegui entender o áudio. Pode mandar por texto?" |
| **T10** | **Nome de empresa falado**, sem CNPJ: "Me fale sobre a Ferreira Costa" | O "Entendi" mostra o nome que o bot ouviu. Nome falado **não tem conferência** (só o seu olho no "Entendi"): se vier trocado, anote. |

**Tempos normais:** a transcrição leva 3 a 4 segundos; a resposta inteira, de 10 a 30 segundos. Mais de 90 segundos só na transcrição é falha (o worker desiste).

## Parte 3: conferir o que aconteceu (para cada teste)

- **Na conversa:** a primeira linha da resposta é o "Entendi" (ou o "Ouvi", se recusou).
- **O que o bot entendeu, em arquivo:** `logs/chat.jsonl`, última linha (`pergunta` é o texto transcrito; `canal` é `whatsapp`).
- **Recusas por CNPJ que não fecha:** `logs/worker.jsonl`, procure `cnpj_falado_nao_confere`.
- **O áudio original:** fica em `%USERPROFILE%\.claude\channels\whatsapp-hackathon\midia\` (o mais recente). Para ouvir de novo ou reprocessar: `python chat/provas/voz_conferir.py <arquivo>`.
- **Erros do worker:** `logs/worker.err.log`.

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| **"Não consegui entender o áudio"** para uma fala normal | Rode a Parte 1 (bloco 5). Reprocesse a nota com `voz_conferir.py`: se aí funciona, o problema está no worker (veja `logs/worker.err.log`); se não, o ambiente de voz (`inferencia/.venv`, modelo). |
| Nem o 👀 aparece | O gateway está desconectado, ou o número não está liberado: `bun acesso.ts status` e `bun acesso.ts desconhecidos`. |
| Acentos deformados ("sanÃ§Ãµes") no "Entendi" | Não deveria acontecer (foi corrigido em 14/11). Se acontecer, guarde o áudio e avise: é falha de codificação do Windows. |
| Pede para digitar mesmo falando o CNPJ certo | Normal quando o Whisper erra um dígito. Fale **em grupos de dois a quatro dígitos**, devagar, e repita. |
| Respondeu sobre uma empresa que você não falou | **Falha séria.** Guarde o áudio e o `Entendi`, e avise antes de seguir testando. |

## O que anotar e devolver

Uma tabela simples, uma linha por nota: **Teste | O que você falou | O que o bot entendeu | Consultou? | Acertou a empresa? | Segundos**. Com umas 10 notas já dá uma taxa de acerto de verdade. Até aqui se testou com **voz sintética**, com **3 notas reais curtas** guardadas e com **4 notas reais pelo celular** (14/11, 11:32 a 11:36: transcrição certa, uma trava de CNPJ com 13 números funcionando, uma consulta de 9 s; ver `testes-seguranca.md` §2.11). A nota das 09:45 de 14/11 tinha caído em "Não consegui entender o áudio" porque o ambiente de voz ainda não existia; hoje é transcrita certa. O que falta saber é o comportamento com várias pessoas, sotaques e ruído.
