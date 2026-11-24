"""Caminhos do Raio-X. Tudo relativo à raiz do repositório, ou à pasta em RAIOX_BASE.

  RAIOX_BASE   raiz com a pasta dados/ (padrão: a pasta acima de scripts/)
  RAIOX_SAIDA  onde gravar a saída de cada dia (padrão: RAIOX_BASE/saida)
"""
import os
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
BASE = Path(os.environ.get("RAIOX_BASE") or AQUI.parent).resolve()
DADOS = BASE / "dados"
SAIDA = Path(os.environ.get("RAIOX_SAIDA") or BASE / "saida").resolve()
FONTES = AQUI / "fontes"
ARQ_APELIDOS = DADOS / "apelidos_times.csv"


def ler(nome, columns=None):
    """Lê dados/<nome>.csv (partidas, agenda, jogador_partida, apelidos_times)."""
    return pd.read_csv(DADOS / f"{nome}.csv", usecols=columns, dtype={"temporada": str}, low_memory=False)
