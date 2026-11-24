"""Liga os nomes de times da agenda (TheStatsAPI) aos nomes do histórico (football-data).

Gera apelidos_times.csv com a correspondência automática. Para corrigir um caso,
edite a coluna nome_historico e marque manual=1: linhas manuais nunca são sobrescritas.
"""
import difflib
import re
import unicodedata
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
from caminhos import ARQ_APELIDOS  # noqa: E402  (dados/apelidos_times.csv)

# competição da TheStatsAPI -> (país, liga) no football-data, nome de exibição
LIGAS = {
    "Brasileirão Série A": ("Brasil", "Serie A", "Brasileirão", "o"),
    "Premier League": ("Inglaterra", "Premier League", "Premier League", "a"),
    "LaLiga": ("Espanha", "La Liga", "LaLiga", "a"),
    "Serie A": ("Itália", "Serie A", "Serie A", "a"),
    "Bundesliga": ("Alemanha", "Bundesliga", "Bundesliga", "a"),
    "Ligue 1": ("França", "Ligue 1", "Ligue 1", "a"),
    "Liga Portugal Betclic": ("Portugal", "Primeira Liga", "Liga Portugal", "a"),
    "Liga Profesional de Fútbol": ("Argentina", "Liga Profesional", "Campeonato Argentino", "o"),
    "Eredivisie": ("Holanda", "Eredivisie", "Eredivisie", "a"),
    "MLS": ("EUA", "MLS", "MLS", "a"),
    "Championship": ("Inglaterra", "Championship", "Championship", "a"),
    "Trendyol Süper Lig": ("Turquia", "Süper Lig", "Campeonato Turco", "o"),
    "Pro League": ("Bélgica", "Pro League", "Campeonato Belga", "o"),
    "Scottish Premiership": ("Escócia", "Premiership", "Campeonato Escocês", "o"),
    "LaLiga 2": ("Espanha", "Segunda División", "LaLiga 2", "a"),
    "Serie B": ("Itália", "Serie B", "Serie B italiana", "a"),
    "2. Bundesliga": ("Alemanha", "2. Bundesliga", "2. Bundesliga", "a"),
    "Ligue 2": ("França", "Ligue 2", "Ligue 2", "a"),
    "League One": ("Inglaterra", "League One", "League One", "a"),
    "League Two": ("Inglaterra", "League Two", "League Two", "a"),
}

RUIDO = {"fc", "cf", "ac", "sc", "afc", "cd", "ca", "ud", "sd", "rc", "club", "de", "da", "do",
         "the", "fk", "sk", "bk", "if", "ssc", "as", "us", "ec", "se", "cr", "rcd", "sv", "vfb",
         "vfl", "tsg", "fsv", "1", "calcio", "futebol", "clube", "esporte", "real", "athletic"}

# correspondências que a comparação de texto não acerta sozinha
FIXOS = {
    ("Brasil", "Atlético Mineiro"): "Atletico-MG",
    ("Brasil", "Athletico"): "Athletico-PR",
    ("Brasil", "Red Bull Bragantino"): "Bragantino",
    ("Brasil", "Vasco da Gama"): "Vasco",
    ("Brasil", "Flamengo"): "Flamengo RJ",
    ("Brasil", "Botafogo"): "Botafogo RJ",
    ("Inglaterra", "Brighton & Hove Albion"): "Brighton",
    ("Inglaterra", "Wolverhampton Wanderers"): "Wolves",
    ("Inglaterra", "Manchester United"): "Man United",
    ("Inglaterra", "Manchester City"): "Man City",
    ("Inglaterra", "Nottingham Forest"): "Nott'm Forest",
    ("Inglaterra", "Tottenham Hotspur"): "Tottenham",
    ("Inglaterra", "Newcastle United"): "Newcastle",
    ("Inglaterra", "Sheffield Wednesday"): "Sheffield Weds",
    ("Espanha", "Athletic Club"): "Ath Bilbao",
    ("Espanha", "Atlético Madrid"): "Ath Madrid",
    ("Espanha", "Real Betis"): "Betis",
    ("Espanha", "Real Sociedad"): "Sociedad",
    ("Espanha", "Celta Vigo"): "Celta",
    ("Espanha", "Rayo Vallecano"): "Vallecano",
    ("Espanha", "Racing de Santander"): "Santander",
    ("Espanha", "Deportivo La Coruña"): "La Coruna",
    ("Espanha", "Levante UD"): "Levante",
    ("Espanha", "Espanyol"): "Espanol",
    ("Itália", "Inter"): "Inter",
    ("Itália", "Milan"): "Milan",
    ("Alemanha", "Bayern München"): "Bayern Munich",
    ("Alemanha", "Borussia Mönchengladbach"): "M'gladbach",
    ("Alemanha", "Eintracht Frankfurt"): "Ein Frankfurt",
    ("Alemanha", "1. FC Köln"): "FC Koln",
    ("Alemanha", "Bayer Leverkusen"): "Leverkusen",
    ("França", "Paris Saint-Germain"): "Paris SG",
    ("França", "Olympique Marseille"): "Marseille",
    ("França", "Olympique Lyonnais"): "Lyon",
    ("Portugal", "Sporting CP"): "Sp Lisbon",
    ("Portugal", "SL Benfica"): "Benfica",
    ("Portugal", "FC Porto"): "Porto",
    ("Portugal", "SC Braga"): "Sp Braga",
    ("Portugal", "Sporting"): "Sp Lisbon",
    ("Portugal", "Vitória SC"): "Guimaraes",
    ("Inglaterra", "Queens Park Rangers"): "QPR",
    ("Inglaterra", "Wolverhampton"): "Wolves",
    ("França", "Stade Rennais"): "Rennes",
    ("Escócia", "Heart of Midlothian"): "Hearts",
    ("Turquia", "Amed Sportif Faaliyetler"): "Amedspor",
    ("Turquia", "Başakşehir FK"): "Buyuksehyr",
    ("Argentina", "Independiente Rivadavia"): "Ind. Rivadavia",
}


def normalizar(nome: str) -> str:
    s = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(p for p in s.split() if p not in RUIDO) or s.strip()


def _melhor(nome, candidatos):
    alvo = normalizar(nome)
    melhor, nota = None, 0.0
    for c in candidatos:
        n = normalizar(c)
        r = difflib.SequenceMatcher(None, alvo, n).ratio()
        if alvo and n and (alvo in n or n in alvo):
            r = max(r, 0.9)
        if set(alvo.split()) & set(n.split()):
            r = max(r, 0.75 + 0.2 * r)
        if r > nota:
            melhor, nota = c, r
    return melhor, round(nota, 3)


def montar_apelidos(agenda: pd.DataFrame, historico: pd.DataFrame) -> pd.DataFrame:
    """agenda: competicao, time_casa, time_fora. historico: pais, liga, data, time_casa, time_fora."""
    antigos = pd.read_csv(ARQ_APELIDOS) if ARQ_APELIDOS.exists() else pd.DataFrame(
        columns=["competicao", "nome_agenda", "pais", "liga", "nome_historico", "nota", "manual"])
    manuais = antigos[antigos.manual == 1]
    chave_manual = set(zip(manuais.competicao, manuais.nome_agenda))
    recentes = historico[historico.data >= historico.data.max() - pd.Timedelta(days=800)]
    linhas = []
    for comp, (pais, liga, _, _) in LIGAS.items():
        nomes = set(agenda.loc[agenda.competicao == comp, ["time_casa", "time_fora"]].stack())
        if not nomes:
            continue
        h = recentes[(recentes.pais == pais) & (recentes.liga == liga)]
        cand_liga = set(h.time_casa) | set(h.time_fora)
        # times recém-promovidos podem vir de outra divisão do mesmo país
        h_pais = recentes[recentes.pais == pais]
        cand_pais = set(h_pais.time_casa) | set(h_pais.time_fora)
        for nome in sorted(nomes):
            if (comp, nome) in chave_manual:
                continue
            if (pais, nome) in FIXOS and FIXOS[(pais, nome)] in cand_pais:
                m, nota = FIXOS[(pais, nome)], 1.0
            else:
                m, nota = _melhor(nome, cand_liga)
                if nota < 0.8:
                    m2, n2 = _melhor(nome, cand_pais)
                    if n2 > nota:
                        m, nota = m2, n2
            linhas.append(dict(competicao=comp, nome_agenda=nome, pais=pais, liga=liga,
                               nome_historico=m if nota >= 0.6 else "", nota=nota, manual=0))
    tab = pd.concat([manuais, pd.DataFrame(linhas)], ignore_index=True)
    tab = tab.sort_values(["competicao", "nome_agenda"])
    tab.to_csv(ARQ_APELIDOS, index=False)
    return tab


def formas_liga(comp):
    """'na LaLiga', 'pela LaLiga', 'da LaLiga' (ou 'no/pelo/do Brasileirão')."""
    _, _, nome, g = LIGAS[comp]
    return {"nome": nome, "na": f"n{g} {nome}", "pela": f"pel{g} {nome}", "da": f"d{g} {nome}"}
