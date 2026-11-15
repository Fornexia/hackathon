"""Conferência do que foi ouvido numa nota de voz, antes de virar pergunta.

Um CNPJ transcrito errado leva o bot a falar de OUTRA empresa, e o usuário não percebe. Medido em 14/11/2026 com voz sintética (só prova o caminho; voz humana
vai melhor, mas não é garantia): o Whisper `small` escreveu "26.852.688.00." (truncado), "26 852-688-0002-3" (dígito trocado) e "1.0, 2.3.0, 4.8.0..." (sem forma de CNPJ).
Por isso, depois de transcrever:

1. Se há um CNPJ no que foi ouvido, ele precisa ter 14 números e o dígito verificador tem de fechar. Se não fechar, o bot NÃO consulta: pede para o usuário digitar.
2. Quando está tudo certo, a resposta começa com "🎙️ Entendi: ...", para o usuário perceber um erro de transcrição que a conferência não pegaria
   (por exemplo, um CNPJ com os 14 números e o dígito certo, mas de outra empresa; a chance disso por acaso é de 1 em 100).
"""

import re

MARCADOR_DO_TRANSCRITOR = "[CNPJ não entendido]"          # `inferencia/transcrever.py` escreve isto quando o Whisper copia o exemplo do contexto
PALAVRA_CNPJ = re.compile(r"\bcnpj\b", re.IGNORECASE)
DEPOIS_DA_PALAVRA = re.compile(r"^\W*(?:(?:n[úu]mero|de|do|da|é|e|igual)\W+)*(\d[\d.,/\-\s]*)")
SEQUENCIA_LONGA = re.compile(r"\d[\d.,/\-\s]*\d")
MIN_DIGITOS_SOLTOS = 12          # sem a palavra "CNPJ", só uma sequência com 12 ou mais números parece CNPJ (CPF tem 11 e número de contrato é curto)


def so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cnpj_valido(d: str) -> bool:
    if len(d) != 14 or not d.isascii() or not d.isdigit() or len(set(d)) == 1:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        resto = sum(int(a) * b for a, b in zip(d[:n], pesos)) % 11
        if int(d[n]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


def candidatos(texto: str) -> list[str]:
    """Os números que parecem CNPJ no texto: o que vem depois da palavra "CNPJ" e as sequências longas soltas. Só dígitos, sem repetir."""
    achados: list[str] = []
    cobertos: list[tuple[int, int]] = []
    for m in PALAVRA_CNPJ.finditer(texto):
        resto = DEPOIS_DA_PALAVRA.match(texto[m.end():m.end() + 120])
        if resto:
            achados.append(so_digitos(resto.group(1)))
            cobertos.append((m.end() + resto.start(1), m.end() + resto.end(1)))
    for m in SEQUENCIA_LONGA.finditer(texto):
        d = so_digitos(m.group())
        if len(d) >= MIN_DIGITOS_SOLTOS and not any(a <= m.start() < b for a, b in cobertos):
            achados.append(d)
    return [d for d in dict.fromkeys(achados) if d]


def conferir_cnpj_falado(texto: str) -> str | None:
    """None se está tudo certo (ou não há CNPJ no que foi dito); senão uma frase curta dizendo o que não fechou."""
    if MARCADOR_DO_TRANSCRITOR in (texto or ""):
        return "não consegui entender o CNPJ"
    for d in candidatos(texto or ""):
        if len(d) != 14:
            return f"o CNPJ que ouvi tem {len(d)} números, e ele precisa ter 14"
        if not cnpj_valido(d):
            return "o CNPJ que ouvi não fecha (o dígito final está errado)"
    return None


def _curto(texto: str, limite: int = 300) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


def pedir_para_digitar(texto: str, motivo: str) -> str:
    return (f"🎙️ Ouvi: “{_curto(texto)}”\n\nNão vou consultar: {motivo}. Nota de voz erra número com facilidade. "
            "Pode digitar o CNPJ (os 14 números) por texto?")


def eco(texto: str) -> str:
    """Primeira linha da resposta a uma pergunta por voz: o que o bot entendeu."""
    return f"🎙️ Entendi: “{_curto(texto)}”\n\n"
