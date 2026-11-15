"""Transcreve áudio (nota de voz do WhatsApp) para texto, na CPU, com faster-whisper.

    inferencia/.venv/bin/python inferencia/transcrever.py <audio> [--modelo small]

Imprime só o texto no stdout (o canal WhatsApp lê daqui). Modelos ficam em inferencia/modelos/whisper,
então funciona offline depois do primeiro download. WHISPER_MODELO troca o padrão (base = mais rápido,
small = mais preciso; medido no notebook antes de escolher).
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

PASTA = Path(__file__).parent / "modelos" / "whisper"
PADRAO = os.environ.get("WHISPER_MODELO", "small")

# O contexto (initial_prompt) ensina o jeito de escrever: CNPJ com pontos e barra ("12.345.678/0001-95") e valor em reais ("R$ 7,77"). Sem ele, o
# Whisper tende a escrever número falado por extenso ou a colar dígitos. Mas, quando o áudio corta no meio do número, ele pode COPIAR o exemplo.
# Por isso os exemplos são SENTINELAS: se o CNPJ 12.345.678/0001-95 ou "R$ 7,77" aparecerem na saída, foram inventados, e viram um marcador
# que o worker trata como "não entendi, digite". (O contexto anterior era de outro produto: preços de compras. A ideia da sentinela é de lá,
# medida em 01/11/2026 com notas de voz reais do Lucas.)
CONTEXTO = ("Mensagem de voz de WhatsApp em português do Brasil, uma pergunta sobre fornecedores, contratos e sanções em Garanhuns, Pernambuco: "
            "CEIS, CNEP, PNCP, Receita Federal, Bernhoeft. Exemplo: o CNPJ 12.345.678/0001-95 tem contrato de R$ 7,77?")
# Palavras que o Whisper tende a errar no nosso assunto ("sanções" saiu "sensações" numa nota real de 11/11/2026). `hotwords` as favorece; com beam 5 a nota real
# passou a sair certa (3 notas reais e 4 sintéticas, em 14/11/2026: amostra pequena). Custa cerca de 2 s por nota em vez de 1,5 s.
HOTWORDS = "sanção sanções fornecedor fornecedores contratos CNPJ Garanhuns Bernhoeft CEIS CNEP"
BEAM = 5
SENTINELA_VALOR = re.compile(r"R\$\s?7[,.]77")
SENTINELA_CNPJ = re.compile(r"12[.\s]?345[.\s]?678\s?/?\s?0001\s?-?\s?95")
NAO_ENTENDIDO = "[valor não entendido]"
CNPJ_NAO_ENTENDIDO = "[CNPJ não entendido]"


def achar_ffmpeg() -> str:
    """O `ffmpeg` do sistema, se houver; senão o que vem no pacote `imageio-ffmpeg` (instalado em inferencia/.venv), que dispensa instalar nada
    no Windows e não depende do PATH de quem sobe o worker."""
    achado = shutil.which("ffmpeg") or os.environ.get("FFMPEG_BIN")
    if achado:
        return achado
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("ffmpeg não encontrado: instale-o, defina FFMPEG_BIN ou rode `pip install imageio-ffmpeg` em inferencia/.venv")


def decodificar(caminho: str) -> np.ndarray:
    """Áudio → float32 mono 16 kHz via ffmpeg. O decodificador embutido do faster-whisper (PyAV) quebra
    com o PyAV 19, e não há wheel de versão antiga para este Python."""
    pcm = subprocess.run(
        [achar_ffmpeg(), "-nostdin", "-loglevel", "error", "-i", caminho, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def transcrever(caminho: str, modelo: str = PADRAO) -> str:
    m = WhisperModel(modelo, device="cpu", compute_type="int8", download_root=str(PASTA))
    segmentos, _ = m.transcribe(
        decodificar(caminho),
        language="pt",
        beam_size=BEAM,
        hotwords=HOTWORDS,
        vad_filter=True,  # corta silêncio do começo/fim da nota de voz
        initial_prompt=CONTEXTO,
    )
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    return SENTINELA_CNPJ.sub(CNPJ_NAO_ENTENDIDO, SENTINELA_VALOR.sub(NAO_ENTENDIDO, texto))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--modelo", default=PADRAO)
    a = p.parse_args()
    print(transcrever(a.audio, a.modelo))
