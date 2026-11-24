"""Calcula as curiosidades de cada jogo da agenda a partir do histórico.

Cada curiosidade é um dict com:
  tipo, time (casa/fora/None), nota (raridade), numero (destaque do cartão),
  rotulo (texto curto ao lado do número), texto (frase completa), curto (versão para o resumo)
  e prova (dados usados, para a checagem independente em checagem.py).
"""
from collections import Counter

import pandas as pd

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
PAUSA_MAXIMA = pd.Timedelta(days=200)  # mais que isso entre dois jogos na liga = rebaixamento, a sequência recomeça


def data_extenso(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def mes_ano(d):
    return f"{MESES[d.month - 1]} de {d.year}"


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def jogos_do_time(hist, time, ate):
    """Jogos do time na liga antes da data, do mais recente para o mais antigo, sem atravessar rebaixamento."""
    h = hist[((hist.time_casa == time) | (hist.time_fora == time)) & (hist.data < ate)].sort_values("data", ascending=False)
    linhas, anterior = [], None
    for r in h.itertuples():
        if anterior is not None and anterior - r.data > PAUSA_MAXIMA:
            break
        casa = r.time_casa == time
        gp, gc = (r.gols_casa, r.gols_fora) if casa else (r.gols_fora, r.gols_casa)
        linhas.append(dict(id=r.Index, data=r.data, casa=casa, adv=r.time_fora if casa else r.time_casa,
                           gp=int(gp), gc=int(gc), res="V" if gp > gc else "E" if gp == gc else "D"))
        anterior = r.data
    return linhas


def contar(seq, cond):
    n = 0
    for j in seq:
        if not cond(j):
            break
        n += 1
    return n


def seq_time(nome, lado, jogos, liga):
    """Sequências atuais de um time na liga."""
    out = []
    if len(jogos) < 3:
        return out
    v = contar(jogos, lambda j: j["res"] == "V")
    inv = contar(jogos, lambda j: j["res"] != "D")
    d = contar(jogos, lambda j: j["res"] == "D")
    sv = contar(jogos, lambda j: j["res"] != "V")
    ss = contar(jogos, lambda j: j["gc"] == 0)
    sm = contar(jogos, lambda j: j["gp"] == 0)
    mt = contar(jogos, lambda j: j["gp"] > 0)

    def add(tipo, n, nota, rotulo, texto, curto):
        out.append(dict(tipo=tipo, grupo="sequencia", time=lado, nota=nota, numero=str(n), rotulo=rotulo,
                        texto=texto, curto=curto, prova=dict(time=nome, n=n, ids=[j["id"] for j in jogos[:n + 1]])))

    if v >= 4:
        add("vitorias_seguidas", v, v * 1.2, f"vitórias seguidas · {nome}",
            f"{nome} vem de {v} vitórias seguidas {liga['na']}.", f"{nome}: {v} vitórias seguidas")
    elif inv >= 7:
        add("invicto", inv, inv * 0.8, f"jogos sem perder · {nome}",
            f"{nome} está há {inv} jogos sem perder {liga['na']}.", f"{nome}: {inv} jogos sem perder")
    if d >= 4:
        add("derrotas_seguidas", d, d * 1.2, f"derrotas seguidas · {nome}",
            f"{nome} perdeu os últimos {d} jogos {liga['na']}.", f"{nome}: {d} derrotas seguidas")
    elif sv >= 6:
        add("sem_vencer", sv, sv * 0.8, f"jogos sem vencer · {nome}",
            f"{nome} está há {sv} jogos sem vencer {liga['na']}.", f"{nome}: {sv} jogos sem vencer")
    if ss >= 4:
        add("sem_sofrer", ss, ss * 1.1, f"jogos sem sofrer gol · {nome}",
            f"{nome} não sofre gol há {ss} jogos {liga['na']}.", f"{nome}: {ss} jogos sem sofrer gol")
    if sm >= 3:
        add("sem_marcar", sm, sm * 1.3, f"jogos sem marcar · {nome}",
            f"{nome} não marca há {sm} jogos {liga['na']}.", f"{nome}: {sm} jogos sem marcar")
    elif mt >= 12:
        add("marcou_todos", mt, mt * 0.5, f"jogos seguidos marcando · {nome}",
            f"{nome} marcou em todos os últimos {mt} jogos {liga['na']}.", f"{nome}: gol em {mt} jogos seguidos")

    # recorte de mando: casa para o mandante, fora para o visitante
    sub = [j for j in jogos if j["casa"] == (lado == "casa")]
    onde = "em casa" if lado == "casa" else "fora de casa"
    vm = contar(sub, lambda j: j["res"] == "V")
    im = contar(sub, lambda j: j["res"] != "D")
    svm = contar(sub, lambda j: j["res"] != "V")
    if vm >= (5 if lado == "casa" else 4):
        add(f"vitorias_{lado}", vm, vm * (0.9 if lado == "casa" else 1.1), f"vitórias seguidas {onde}",
            f"{nome} venceu os últimos {vm} jogos {onde} {liga['na']}.", f"{nome}: {vm} vitórias seguidas {onde}")
    elif im >= 10:
        add(f"invicto_{lado}", im, im * 0.6, f"jogos sem perder {onde}",
            f"{nome} não perde {onde} há {im} jogos {liga['na']}.", f"{nome}: {im} jogos sem perder {onde}")
    if svm >= 8:
        add(f"sem_vencer_{lado}", svm, svm * 0.6, f"jogos sem vencer {onde}",
            f"{nome} não vence {onde} há {svm} jogos {liga['na']}.", f"{nome}: {svm} jogos sem vencer {onde}")
    for c in out:
        if c["tipo"].endswith(lado):
            c["prova"]["ids"] = [j["id"] for j in sub[:int(c["numero"]) + 1]]
            c["prova"]["mando"] = lado
    return out


def confronto(hist, casa, fora, ncasa, nfora, liga, ate):
    """Curiosidades do confronto direto na liga."""
    h = hist[(((hist.time_casa == casa) & (hist.time_fora == fora)) |
              ((hist.time_casa == fora) & (hist.time_fora == casa))) & (hist.data < ate)].sort_values("data")
    out = []
    n = len(h)
    if n < 5:
        return out
    vc = int(((h.time_casa == casa) & (h.gols_casa > h.gols_fora)).sum() + ((h.time_fora == casa) & (h.gols_fora > h.gols_casa)).sum())
    vf = int(((h.time_casa == fora) & (h.gols_casa > h.gols_fora)).sum() + ((h.time_fora == fora) & (h.gols_fora > h.gols_casa)).sum())
    e = n - vc - vf
    desde = h.data.min().year
    ids = list(h.index)

    def add(tipo, grupo, nota, numero, rotulo, texto, curto, prova):
        out.append(dict(tipo=tipo, grupo=grupo, time=None, nota=nota, numero=numero, rotulo=rotulo,
                        texto=texto, curto=curto, prova=prova))

    # retrospecto geral
    dom = abs(vc - vf) / n
    nota = 2 + dom * 6 + (3 if min(vc, vf) == 0 and n >= 6 else 0)
    lider, vl, outro, vo = (ncasa, vc, nfora, vf) if vc >= vf else (nfora, vf, ncasa, vc)
    add("h2h_geral", "h2h", nota, f"{vc}-{e}-{vf}", f"{ncasa} x {nfora}: vitórias, empates e derrotas desde {desde}",
        (f"Em {n} jogos {liga['pela']} desde {desde}: {ncasa} venceu {vc}, {nfora} venceu {vf} e houve {plural(e, 'empate', 'empates')}."
         if min(vc, vf) > 0 else
         f"Em {n} jogos {liga['pela']} desde {desde}, {outro} nunca venceu: foram {plural(vl, 'vitória', 'vitórias')} de {lider} e {plural(e, 'empate', 'empates')}."),
        f"{lider} {vl} x {vo} {outro} em {n} jogos",
        dict(casa=casa, fora=fora, n=n, vc=vc, e=e, vf=vf, ids=ids))

    # o mandante recebendo este visitante
    hc = h[h.time_casa == casa]
    if len(hc) >= 5:
        vit_fora = hc[hc.gols_fora > hc.gols_casa]
        if len(vit_fora) == 0:
            add("tabu_visitante", "tabu", 4 + len(hc) * 0.5, str(len(hc)), f"visitas sem vitória · {nfora}",
                f"Como visitante contra {ncasa}, {nfora} nunca venceu {liga['pela']}: são {len(hc)} jogos desde {hc.data.min().year}.",
                f"{nfora} nunca venceu lá ({len(hc)} jogos)", dict(casa=casa, fora=fora, n=len(hc), ids=list(hc.index)))
        vit_casa = hc[hc.gols_casa > hc.gols_fora]
        if len(vit_casa) <= len(hc) * 0.2:
            ult = vit_casa.data.max() if len(vit_casa) else None
            quando = f"A última vitória foi em {mes_ano(ult)}." if ult is not None else ""
            add("tabu_mandante", "tabu", 3 + (0.2 - len(vit_casa) / len(hc)) * 30 + min(len(hc), 20) * 0.2, f"{len(vit_casa)}/{len(hc)}", f"vitórias de {ncasa} em casa contra {nfora}",
                (f"Em casa contra {nfora}, {ncasa} venceu só {len(vit_casa)} de {len(hc)} jogos {liga['pela']} desde {hc.data.min().year}. {quando}" if len(vit_casa)
                 else f"Em casa contra {nfora}, {ncasa} nunca venceu {liga['pela']}: são {len(hc)} jogos desde {hc.data.min().year}.").strip(),
                f"{ncasa} venceu só {len(vit_casa)} de {len(hc)} em casa" if len(vit_casa) else f"{ncasa} nunca venceu em casa ({len(hc)} jogos)",
                dict(casa=casa, fora=fora, n=len(hc), v=len(vit_casa), ids=list(hc.index)))

    # sequências dentro do confronto
    rec = h.sort_values("data", ascending=False)

    def resultado(r, t):
        gp, gc = (r.gols_casa, r.gols_fora) if r.time_casa == t else (r.gols_fora, r.gols_casa)
        return "V" if gp > gc else "E" if gp == gc else "D"

    for t, nome, outro in [(casa, ncasa, nfora), (fora, nfora, ncasa)]:
        res = [resultado(r, t) for r in rec.itertuples()]
        v = contar(res, lambda x: x == "V")
        inv = contar(res, lambda x: x != "D")
        if v >= 4:
            add("h2h_vitorias", "h2h_seq", v * 1.0, str(v), f"vitórias seguidas · {nome} contra {outro}",
                f"{nome} venceu os últimos {v} confrontos com {outro} {liga['pela']}.",
                f"{nome} venceu os últimos {v} contra {outro}", dict(time=t, n=v, ids=list(rec.index[:v + 1])))
        elif inv >= 6 and inv < n:
            add("h2h_invicto", "h2h_seq", inv * 0.7, str(inv), f"jogos sem perder · {nome} contra {outro}",
                f"{nome} não perde para {outro} há {inv} jogos {liga['pela']}.",
                f"{nome} não perde para {outro} há {inv} jogos", dict(time=t, n=inv, ids=list(rec.index[:inv + 1])))

    # gols no confronto
    if n >= 8:
        tot = h.gols_casa + h.gols_fora
        media = tot.mean()
        tres = int((tot >= 3).sum())
        if media >= 3.2 or tres / n >= 0.7:
            add("h2h_gols_muitos", "gols", 2.5 + (media - 3) * 3, f"{media:.1f}".replace(".", ","), "gols por jogo no confronto",
                f"O confronto tem média de {media:.1f} gols por jogo {liga['pela']}, e {tres} dos {n} jogos tiveram 3 gols ou mais.".replace(".", ",", 1),
                f"média de {media:.1f} gols".replace(".", ","), dict(casa=casa, fora=fora, n=n, media=round(media, 2), tres=tres, ids=ids))
        elif media <= 1.9 or tres / n <= 0.25:
            add("h2h_gols_poucos", "gols", 2.5 + (2.3 - media) * 3, f"{media:.1f}".replace(".", ","), "gols por jogo no confronto",
                f"Confronto de poucos gols: média de {media:.1f} por jogo {liga['pela']}, e só {tres} dos {n} jogos tiveram 3 gols ou mais.".replace(".", ",", 1),
                f"média de só {media:.1f} gols".replace(".", ","), dict(casa=casa, fora=fora, n=n, media=round(media, 2), tres=tres, ids=ids))

    # último confronto elástico e recente
    u = rec.iloc[0]
    if abs(u.gols_casa - u.gols_fora) >= 4 and (ate - u.data).days < 400:
        gan = u.time_casa if u.gols_casa > u.gols_fora else u.time_fora
        ng = ncasa if gan == casa else nfora
        placar = f"{int(max(u.gols_casa, u.gols_fora))} a {int(min(u.gols_casa, u.gols_fora))}"
        add("ultimo_elastico", "ultimo", 3.0, placar, "no último confronto",
            f"No último encontro, em {data_extenso(u.data)}, {ng} venceu por {placar}.",
            f"último jogo: {ng} {placar}", dict(id=int(rec.index[0]), ids=[int(rec.index[0])]))
    return out


def jogadores(jp, time_us, nome_time, lado, liga, ate):
    """Sequência de gols e artilharia de jogadores (Understat, 5 grandes ligas)."""
    out = []
    if jp is None or not time_us:
        return out
    j = jp[(jp.time == time_us) & (jp.data < ate)]
    if j.empty:
        return out
    ultimo_jogo = j.understat_id.loc[j.data.idxmax()]
    temporada = j.loc[j.data.idxmax(), "temporada"]
    for jid, g in j.groupby("understat_id_jogador"):
        g = g.sort_values("data", ascending=False)
        if g.understat_id.iloc[0] != ultimo_jogo:  # só quem jogou a última partida (evita lesionados)
            continue
        nome = g.jogador.iloc[0]
        s = contar(list(g.itertuples()), lambda r: r.gols > 0)
        if s >= 4:
            gols = int(g.gols.iloc[:s].sum())
            out.append(dict(tipo="jogador_seq_gols", grupo="jogador", time=lado, nota=s * 1.1, numero=str(s),
                            rotulo=f"jogos seguidos com gol · {nome}",
                            texto=f"{nome} ({nome_time}) marcou nos últimos {s} jogos que disputou {liga['na']} ({gols} gols no período).",
                            curto=f"{nome}: gol em {s} jogos seguidos",
                            prova=dict(jogador=jid, time=time_us, n=s, gols=gols)))
    # artilheiro da liga na temporada
    tl = jp[(jp.temporada == temporada) & (jp.liga_us == jp.loc[j.index[0], "liga_us"]) & (jp.data < ate)]
    art = tl.groupby(["understat_id_jogador", "jogador", "time"]).gols.sum().reset_index().sort_values("gols", ascending=False)
    if len(art) and art.iloc[0].time == time_us and art.iloc[0].gols >= 5:
        top = art.iloc[0]
        vantagem = int(top.gols - (art.iloc[1].gols if len(art) > 1 else 0))
        empate = vantagem == 0
        out.append(dict(tipo="artilheiro", grupo="jogador", time=lado, nota=3.5 + min(vantagem, 3) * 0.5, numero=str(int(top.gols)),
                        rotulo=f"gols na temporada · {top.jogador}",
                        texto=(f"{top.jogador} é {'um dos artilheiros' if empate else 'o artilheiro'} {liga['da']} na temporada, com {int(top.gols)} gols."),
                        curto=f"{top.jogador}, artilheiro com {int(top.gols)} gols",
                        prova=dict(jogador=int(top.understat_id_jogador), temporada=temporada, gols=int(top.gols))))
    return out


CONFRONTO = {"h2h", "tabu", "h2h_seq", "gols", "ultimo"}


def escolher(cands, maximo=3):
    """As melhores curiosidades do jogo, sem repetir o mesmo grupo nem concentrar tudo num time."""
    escolhidas, grupos, times, vistos = [], Counter(), Counter(), set()
    for c in sorted(cands, key=lambda c: -c["nota"]):
        if grupos[c["grupo"]] >= (2 if c["grupo"] == "sequencia" else 1):
            continue
        if c["time"] and times[c["time"]] >= 2:
            continue
        if c["time"] and (c["time"], c["grupo"]) in vistos:
            continue
        if c["grupo"] in CONFRONTO and sum(grupos[g] for g in CONFRONTO) >= 2:
            continue
        escolhidas.append(c)
        grupos[c["grupo"]] += 1
        if c["time"]:
            times[c["time"]] += 1
            vistos.add((c["time"], c["grupo"]))
        if len(escolhidas) == maximo:
            break
    return escolhidas
