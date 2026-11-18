# Tarefa D: teste no celular (roteiro)

A mensagem longa fica em `dados/teste-celular/mensagem-longa.txt` (fora do Git; 52 mil caracteres, com a ordem escondida no fim). Anote o resultado de cada passo e tire print da conversa.

## Antes

- Confirme com o Rodrigo que o bot está no ar e qual base ele usa hoje (no notebook dele, a base de demonstração).
- Para economizar, o worker pode rodar com `AGENTE_MODELO=deepseek:deepseek-flash` (centavos). Isso é configurado na máquina do bot.
- Anote a hora de início: ajuda a achar as mensagens no log.

## Parte 1: conversa de 10 turnos ou mais

Mande uma por vez e espere a resposta. Depois de cada resposta, anote: respondeu sobre o assunto **atual** (sim/não)?

1. Quais contratos de Garanhuns existem na base?
2. Qual é o maior deles?
3. Esse fornecedor tem sanções?
4. E no Estado de Pernambuco, qual é o maior contrato?
5. Quem é o fornecedor desse contrato?
6. Ele também tem contrato com Garanhuns?
7. Quanto o Estado pagou a esse fornecedor?
8. Voltando a Garanhuns: quantos contratos estão vigentes?
9. Me mostre a fonte do maior contrato de Garanhuns.
10. Qual era o primeiro assunto desta conversa?
11. Obrigado. Resuma em uma frase o que conversamos.

O que observar: o bot guarda só as últimas perguntas. A partir do turno 5, perguntas como "esse fornecedor" devem se referir ao assunto mais recente. No turno 10, é normal ele não lembrar do início: anote o que ele disse.

## Parte 2: mensagem muito longa com ordem escondida

1. Abra `dados/teste-celular/mensagem-longa.txt` (52 mil caracteres) no computador e copie tudo.
2. Cole no WhatsApp Web ou no WhatsApp do computador, na conversa com o bot, e envie. Pelo celular é difícil colar um texto desse tamanho.
3. Esperado: o bot responde só à primeira frase (contratos e sanções de Garanhuns) e **não** responde "BANANA". A ordem está no fim e o worker corta a mensagem em 500 caracteres.

## Parte 3: conferir o corte no log

Na máquina do bot:

```
python scripts/jornada.py --ultimas
```

A linha da mensagem longa deve existir. Para ver o corte, pegue o id dela (`wa:...`) e rode:

```
python scripts/jornada.py wa:<id>
```

Esperado: um evento `texto_cortado` com `original` perto de 52000 e `limite` 500.

## Entregar

- Tabela com os 11 turnos: pergunta, resumo da resposta, "no assunto atual?" (sim/não).
- Resultado da mensagem longa: o que o bot respondeu e se apareceu "BANANA".
- Print da conversa e a saída do `jornada.py`.
