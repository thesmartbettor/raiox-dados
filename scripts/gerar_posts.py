"""Gera os posts do dia do Raio-X do Jogo (antigo @DataJogo; futebol): resumo e posts do X, carrossel do Instagram.

Uso:
  python3 gerar_posts.py                 # jogos de hoje (horário de Brasília)
  python3 gerar_posts.py --data 2026-10-25
  python3 gerar_posts.py --data 2026-10-25 --sem-cartoes

Saída em saida/<data>/: posts.json (tudo), x.txt, instagram_legenda.txt, cartoes/*.jpg e previa.html.
Nada é publicado por este script: a publicação fica em publicar.py.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import checagem  # noqa: E402
import curiosidades as cur  # noqa: E402
import nomes  # noqa: E402
import regras_x  # noqa: E402

from caminhos import SAIDA, ler  # noqa: E402
BRT = ZoneInfo("America/Sao_Paulo")
LIMITE_X = 280

# peso de cada liga na escolha dos jogos do dia (público brasileiro)
PESO_LIGA = {"Brasileirão Série A": 1.6, "Premier League": 1.45, "LaLiga": 1.4, "Serie A": 1.3, "Bundesliga": 1.2,
             "Ligue 1": 1.1, "Liga Portugal Betclic": 1.05, "Liga Profesional de Fútbol": 1.0, "Eredivisie": 0.8,
             "MLS": 0.75, "Championship": 0.7, "Trendyol Süper Lig": 0.7, "Scottish Premiership": 0.6, "Pro League": 0.55,
             "LaLiga 2": 0.45, "Serie B": 0.45, "2. Bundesliga": 0.45, "Ligue 2": 0.4, "League One": 0.3, "League Two": 0.25}
GRANDES = {"Flamengo", "Palmeiras", "Corinthians", "São Paulo", "Santos", "Vasco da Gama", "Fluminense", "Botafogo",
           "Grêmio", "Internacional", "Atlético Mineiro", "Cruzeiro", "Bahia", "Barcelona", "Real Madrid", "Atlético Madrid",
           "Manchester City", "Manchester United", "Liverpool", "Arsenal", "Chelsea", "Tottenham Hotspur", "Juventus",
           "Inter", "Milan", "Napoli", "Roma", "FC Bayern München", "Borussia Dortmund", "Paris Saint-Germain",
           "SL Benfica", "FC Porto", "Sporting", "Boca Juniors", "River Plate"}
EXIBICAO = {"Brighton & Hove Albion": "Brighton", "Tottenham Hotspur": "Tottenham", "Newcastle United": "Newcastle",
            "Red Bull Bragantino": "Bragantino", "Vasco da Gama": "Vasco", "Wolverhampton Wanderers": "Wolves",
            "Wolverhampton": "Wolves", "Paris Saint-Germain": "PSG", "FC Bayern München": "Bayern de Munique",
            "Bayern München": "Bayern de Munique", "Atlético Madrid": "Atlético de Madrid", "Inter": "Inter de Milão",
            "Athletic Club": "Athletic Bilbao", "Levante UD": "Levante", "Racing de Santander": "Racing Santander",
            "Bayer 04 Leverkusen": "Leverkusen", "Borussia Dortmund": "Borussia Dortmund", "Olympique de Marseille": "Olympique de Marselha",
            "SL Benfica": "Benfica", "FC Porto": "Porto", "PSV Eindhoven": "PSV", "Académico Viseu FC": "Académico de Viseu", "Queens Park Rangers": "QPR", "West Bromwich Albion": "West Brom"}
LIGA_UNDERSTAT = {"EPL": "Premier League", "La_liga": "LaLiga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}


PREFIXOS = ("SC ", "TSG ", "CA ", "FC ", "AFC ", "SV ", "VfL ", "VfB ", "RCD ", "CD ", "UD ", "SD ", "AS ", "US ", "SSC ", "ACF ", "AC ")
SUFIXOS = (" FC", " CF", " SC", " AC", " BC")


def exibir(nome):
    if nome in EXIBICAO:
        return EXIBICAO[nome]
    for p in PREFIXOS:
        if nome.startswith(p) and len(nome) > len(p) + 3:
            nome = nome[len(p):]
    for s in SUFIXOS:
        if nome.endswith(s) and len(nome) > len(s) + 3:
            nome = nome[: -len(s)]
    return nome


def carregar(dia):
    ag = ler("agenda")
    ag["inicio"] = pd.to_datetime(ag.data_hora_utc, utc=True).dt.tz_convert(BRT)
    ag["data_local"] = ag.inicio.dt.date
    ag = ag[ag.competicao.isin(nomes.LIGAS)]
    h = ler("partidas",
                        columns=["pais", "liga", "temporada", "data", "time_casa", "time_fora", "gols_casa", "gols_fora"])
    h = h.dropna(subset=["gols_casa", "gols_fora"])
    h["data"] = pd.to_datetime(h.data)
    apelidos = nomes.montar_apelidos(ag, h)
    mapa = {(r.competicao, r.nome_agenda): r.nome_historico for r in apelidos.itertuples() if isinstance(r.nome_historico, str)}

    # jogos já disputados que a TheStatsAPI tem e o football-data ainda não (deixa as sequências em dia)
    fin = ag[(ag.status == "finished") & ag.gols_casa.notna()].copy()
    fin["pais"] = fin.competicao.map(lambda c: nomes.LIGAS[c][0])
    fin["liga"] = fin.competicao.map(lambda c: nomes.LIGAS[c][1])
    fin["c"] = [mapa.get(k) for k in zip(fin.competicao, fin.time_casa)]
    fin["f"] = [mapa.get(k) for k in zip(fin.competicao, fin.time_fora)]
    fin = fin[[isinstance(c, str) and isinstance(f, str) and bool(c) and bool(f) for c, f in zip(fin.c, fin.f)]].reset_index(drop=True)
    fin["d"] = pd.to_datetime(fin.data_local.astype(str))
    # mesmo jogo já no football-data: mesma liga e times, até 2 dias de diferença (busca vetorizada)
    par = fin.reset_index().merge(h[["pais", "liga", "time_casa", "time_fora", "data"]],
                                  left_on=["pais", "liga", "c", "f"], right_on=["pais", "liga", "time_casa", "time_fora"])
    ja = set(par.loc[(par.data - par.d).abs() <= pd.Timedelta(days=2), "index"])
    novos = [dict(pais=r.pais, liga=r.liga, temporada="tsa", data=r.d, time_casa=r.c, time_fora=r.f,
                  gols_casa=r.gols_casa, gols_fora=r.gols_fora) for r in fin.itertuples() if r.Index not in ja]
    if novos:
        h = pd.concat([h, pd.DataFrame(novos)], ignore_index=True)

    jp = ler("jogador_partida",
                         columns=["understat_id", "understat_id_jogador", "jogador", "time", "minutos", "gols", "liga", "temporada", "data_hora"])
    jp = jp[(jp.temporada >= "2024/25") & jp.liga.isin(LIGA_UNDERSTAT) & (jp.minutos > 0)].rename(columns={"liga": "liga_us"})
    jp["data"] = pd.to_datetime(jp.data_hora).dt.normalize()
    jogos_dia = ag[(ag.data_local == dia) & (ag.status == "scheduled")].sort_values("inicio")
    return jogos_dia, h, mapa, jp, len(novos)


def mapa_understat(jp, jogos):
    m = {}
    for lu, comp in LIGA_UNDERSTAT.items():
        times_us = set(jp.loc[jp.liga_us == lu, "time"])
        for nome in set(jogos.loc[jogos.competicao == comp, ["time_casa", "time_fora"]].stack()):
            melhor, nota = nomes._melhor(nome, times_us)
            if nota < 0.85:
                melhor, nota = nomes._melhor(nomes.FIXOS.get((nomes.LIGAS[comp][0], nome), nome), times_us)
            if nota >= 0.85:
                m[(comp, nome)] = melhor
    return m


def frescor_ok(hist_liga, time, dia):
    """O time precisa ter jogo registrado nos últimos 21 dias, se a liga está em andamento."""
    ult_liga = hist_liga.data.max()
    if pd.Timestamp(dia) - ult_liga > pd.Timedelta(days=21):
        return True  # liga parada (pausa ou início de temporada): as sequências continuam valendo
    ult = hist_liga[(hist_liga.time_casa == time) | (hist_liga.time_fora == time)].data.max()
    return pd.notna(ult) and pd.Timestamp(dia) - ult <= pd.Timedelta(days=21)


def montar_post_x(j):
    """Regras do X (7/11): conclusão na 1ª linha (a curiosidade de maior nota), uma ideia por post,
    sem emoji no começo, sem hashtag, até 6 linhas e 280 caracteres. O jogo e o horário fecham o post."""
    fim = f"{j['casa']} x {j['fora']}, {j['liga']}, hoje às {j['hora']}."
    linhas = []
    for c in sorted(j["curiosidades"], key=lambda c: -c.get("nota", 0)):
        t = c["texto"].strip()
        if len("\n\n".join(linhas + [t, fim])) > LIMITE_X or len(linhas) >= 3:
            continue
        linhas.append(t)
    return regras_x.conferir("\n\n".join(linhas + [fim]))


def montar_resumo_x(destaques, dia):
    """Post da manhã, com a capa como imagem: a melhor curiosidade do dia na 1ª linha e mais até 3 jogos."""
    melhor = max(destaques, key=lambda j: max(c.get("nota", 0) for c in j["curiosidades"]))
    c0 = max(melhor["curiosidades"], key=lambda c: c.get("nota", 0))
    cab = f"{c0['texto'].strip()} {melhor['casa']} x {melhor['fora']} é hoje às {melhor['hora']}."
    fim = "Mais um número de cada jogo antes da bola rolar."
    linhas = []
    for j in destaques:
        if j is melhor or len(linhas) >= 3:
            continue
        linha = f"{j['curiosidades'][0]['curto']} ({j['casa']} x {j['fora']}, {j['hora']})"
        if len("\n".join([cab, ""] + linhas + [linha, "", fim])) > LIMITE_X:
            continue
        linhas.append(linha)
    txt = "\n".join([cab, ""] + linhas + ["", fim]) if linhas else f"{cab}\n\n{fim}"
    if len(txt) > LIMITE_X:
        txt = cab
    return regras_x.conferir(txt)


def montar_legenda(destaques, dia):
    partes = [f"📊 Curiosidades do dia, {dia.day}/{dia.month}. Os números por trás dos principais jogos de hoje.\n"]
    for j in destaques:
        partes.append(f"⚽ {j['casa']} x {j['fora']} | {j['liga']}, {j['hora']}")
        partes += [f"• {c['texto']}" for c in j["curiosidades"]]
        partes.append("")
    partes.append("Números calculados a partir dos resultados dos campeonatos nacionais.")
    partes.append("Siga @RaioXJogo para receber as curiosidades todos os dias.\n")
    partes.append("#futebol #estatisticas #RaioXdoJogo")
    return "\n".join(partes)


def agenda_x(destaques, dia):
    """Resumo às 8h; cada jogo 2h antes, nunca antes das 8h30, com pelo menos 30 min entre posts."""
    horarios, ultimo = [], datetime.combine(dia, datetime.min.time(), BRT).replace(hour=8)
    for j in sorted(destaques, key=lambda j: j["inicio"]):
        alvo = max(j["inicio"] - timedelta(hours=2), ultimo + timedelta(minutes=30))
        if alvo >= j["inicio"] - timedelta(minutes=20):
            continue  # não sobra tempo antes do jogo
        horarios.append((j, alvo))
        ultimo = alvo
    return horarios


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="AAAA-MM-DD (padrão: hoje em Brasília)")
    ap.add_argument("--sem-cartoes", action="store_true")
    ap.add_argument("--max-jogos", type=int, default=7, help="jogos no carrossel")
    ap.add_argument("--max-posts", type=int, default=5, help="posts individuais no X")
    a = ap.parse_args()
    dia = datetime.strptime(a.data, "%Y-%m-%d").date() if a.data else datetime.now(BRT).date()

    jogos, hist, mapa, jp, n_novos = carregar(dia)
    m_us = mapa_understat(jp, jogos)
    print(f"{dia}: {len(jogos)} jogos na agenda; {n_novos} resultados recentes completados pela TheStatsAPI")

    resultado = []
    for r in jogos.itertuples():
        pais, liga_fd = nomes.LIGAS[r.competicao][:2]
        L = nomes.formas_liga(r.competicao)
        casa, fora = mapa.get((r.competicao, r.time_casa)), mapa.get((r.competicao, r.time_fora))
        if not casa or not fora:
            continue
        hl = hist[(hist.pais == pais) & (hist.liga == liga_fd)]
        ate = pd.Timestamp(dia)
        nc, nf = exibir(r.time_casa), exibir(r.time_fora)
        cands = []
        for t, n, lado in [(casa, nc, "casa"), (fora, nf, "fora")]:
            if frescor_ok(hl, t, dia):
                cands += cur.seq_time(n, lado, cur.jogos_do_time(hl, t, ate), L)
        cands += cur.confronto(hl, casa, fora, nc, nf, L, ate)
        for nome_ag, n, lado in [(r.time_casa, nc, "casa"), (r.time_fora, nf, "fora")]:
            cands += cur.jogadores(jp, m_us.get((r.competicao, nome_ag)), n, lado, L, ate)
        # checagem independente: o que não confere é descartado
        boas = []
        for c in cands:
            ok, motivo = checagem.conferir(c, hl, jp, casa, fora, ate)
            if ok:
                boas.append(c)
            else:
                print(f"  descartada ({motivo}): {c['texto']}")
        esc = cur.escolher(boas)
        if not esc:
            continue
        peso = PESO_LIGA.get(r.competicao, 0.3) * (1.3 if {r.time_casa, r.time_fora} & GRANDES else 1.0)
        resultado.append(dict(
            id=r.match_id, competicao=r.competicao, liga=L["nome"], casa=nc, fora=nf, inicio=r.inicio.to_pydatetime(),
            hora=r.inicio.strftime("%Hh%M").replace("h00", "h"), nota=round(sum(c["nota"] for c in esc) * peso, 2),
            curiosidades=[{k: v for k, v in c.items()} for c in esc]))

    resultado.sort(key=lambda j: -j["nota"])
    if not resultado:
        sys.exit(f"{dia}: nenhum jogo com curiosidades hoje; nada gerado.")
    destaques = resultado[: a.max_jogos]
    destaques_ordem = sorted(destaques, key=lambda j: j["inicio"])
    posts = agenda_x(destaques[: a.max_posts], dia)

    saida = SAIDA / dia.isoformat()
    saida.mkdir(parents=True, exist_ok=True)
    resumo = montar_resumo_x(destaques[:6], dia)
    legenda = montar_legenda(destaques_ordem, dia)
    x_posts = [dict(horario="08:00", texto=resumo, tipo="resumo", imagem="cartoes/x_capa.jpg")]
    x_posts += [dict(horario=h.strftime("%H:%M"), texto=montar_post_x(j), tipo="jogo", jogo=j["id"]) for j, h in posts]
    for p in x_posts:
        assert len(p["texto"]) <= LIMITE_X, p

    cartoes = []
    if not a.sem_cartoes:
        import cartoes as cart
        cartoes = cart.gerar(destaques_ordem, dia, saida / "cartoes")

    def ser(o):
        return o.isoformat() if isinstance(o, datetime) else str(o)

    (saida / "posts.json").write_text(json.dumps(dict(
        data=dia.isoformat(), gerado_em=datetime.now(BRT).isoformat(timespec="seconds"),
        x=x_posts, instagram=dict(horario="08:00", legenda=legenda, cartoes=[c.name for c in cartoes]),
        jogos=resultado), ensure_ascii=False, indent=1, default=ser))
    (saida / "x.txt").write_text("\n\n---\n\n".join(f"[{p['horario']}]\n{p['texto']}" for p in x_posts))
    (saida / "instagram_legenda.txt").write_text(legenda)
    import previa
    previa.gerar(saida, dia, x_posts, legenda, cartoes)
    print(f"{len(resultado)} jogos com curiosidades; {len(destaques)} no carrossel; {len(x_posts)} posts no X -> {saida}")


if __name__ == "__main__":
    main()
