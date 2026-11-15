"""Limites de uso da API, na memória do processo (zeram ao reiniciar; para a demonstração basta).

- por minuto, por cliente: janela deslizante de 60 s;
- perguntas em português por dia, por cliente e no total: cada pergunta chama o modelo e custa dinheiro, então tem teto.
"""

import threading
import time
from collections import defaultdict, deque


class Limites:
    def __init__(self, relogio=time.time):
        self._relogio = relogio
        self._trava = threading.Lock()
        self._janela: dict[str, deque] = defaultdict(deque)
        self._dia: dict[tuple[str, str], int] = defaultdict(int)

    def _hoje(self) -> str:
        return time.strftime("%Y-%m-%d", time.localtime(self._relogio()))

    def requisicao(self, cliente: str, por_minuto: int) -> int | None:
        """None se pode; senão, quantos segundos esperar."""
        agora = self._relogio()
        with self._trava:
            fila = self._janela[cliente]
            while fila and agora - fila[0] >= 60:
                fila.popleft()
            if len(fila) >= por_minuto:
                return max(1, int(60 - (agora - fila[0])) + 1)
            fila.append(agora)
            return None

    def reservar_pergunta(self, cliente: str, por_dia_cliente: int, por_dia_total: int) -> str | None:
        """Conta a pergunta ANTES de chamar o modelo. None se coube; senão, o motivo."""
        dia = self._hoje()
        with self._trava:
            if self._dia[(cliente, dia)] >= por_dia_cliente:
                return "limite diário de perguntas deste cliente atingido"
            if self._dia[("*", dia)] >= por_dia_total:
                return "limite diário de perguntas do serviço atingido"
            self._dia[(cliente, dia)] += 1
            self._dia[("*", dia)] += 1
            return None

    def restantes_hoje(self, cliente: str, por_dia_cliente: int) -> int:
        with self._trava:
            return max(0, por_dia_cliente - self._dia[(cliente, self._hoje())])
