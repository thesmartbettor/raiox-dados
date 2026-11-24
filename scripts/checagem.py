"""Checagem independente de cada curiosidade antes de ela virar post.

Recalcula o número por outro caminho (SQL no DuckDB ou laço simples sobre as linhas) e
compara com o que a curiosidade afirma. Se não bater, a curiosidade é descartada.
"""
import duckdb
import pandas as pd

from curiosidades import PAUSA_MAXIMA

CONDICOES = {
    "vitorias_seguidas": lambda gp, gc: gp > gc, "vitorias_casa": lambda gp, gc: gp > gc, "vitorias_fora": lambda gp, gc: gp > gc,
    "invicto": lambda gp, gc: gp >= gc, "invicto_casa": lambda gp, gc: gp >= gc, "invicto_fora": lambda gp, gc: gp >= gc,
    "derrotas_seguidas": lambda gp, gc: gp < gc,
    "sem_vencer": lambda gp, gc: gp <= gc, "sem_vencer_casa": lambda gp, gc: gp <= gc, "sem_vencer_fora": lambda gp, gc: gp <= gc,
    "sem_sofrer": lambda gp, gc: gc == 0, "sem_marcar": lambda gp, gc: gp == 0, "marcou_todos": lambda gp, gc: gp > 0,
}


def _seq(c, hl, ate):
    p = c["prova"]
    nome_hist = None
    linhas = hl.loc[[i for i in p["ids"] if i in hl.index]]
    # descobre o nome do time no histórico pelo jogo mais recente da sequência
    if not len(linhas):
        return False, "jogos da prova não encontrados"
    r0 = linhas.iloc[0]
    for t in (r0.time_casa, r0.time_fora):
        if all((r.time_casa == t) or (r.time_fora == t) for r in linhas.itertuples()):
            nome_hist = t
    mando = p.get("mando")
    todos = []
    for r in hl.itertuples():
        if r.data >= ate or nome_hist not in (r.time_casa, r.time_fora):
            continue
        em_casa = r.time_casa == nome_hist
        if mando and em_casa != (mando == "casa"):
            continue
        todos.append((r.data, r.Index, *((r.gols_casa, r.gols_fora) if em_casa else (r.gols_fora, r.gols_casa))))
    todos.sort(reverse=True)
    n, cond = p["n"], CONDICOES[c["tipo"]]
    if len(todos) < n:
        return False, "menos jogos que a sequência"
    if [t[1] for t in todos[:n]] != list(p["ids"][:n]):
        return False, "a sequência não são os últimos jogos"
    if not all(cond(t[2], t[3]) for t in todos[:n]):
        return False, "jogo da sequência não cumpre a condição"
    if len(todos) > n and cond(todos[n][2], todos[n][3]) and todos[n - 1][0] - todos[n][0] <= PAUSA_MAXIMA:
        return False, "a sequência é maior do que a anunciada"
    return True, ""


def _h2h(c, hl, casa, fora, ate):
    con = duckdb.connect()
    con.register("h", hl[["data", "time_casa", "time_fora", "gols_casa", "gols_fora"]])
    base = f"""from h where data < '{ate.date()}' and ((time_casa = $c and time_fora = $f) or (time_casa = $f and time_fora = $c))"""
    p, t = c["prova"], c["tipo"]
    if t == "h2h_geral":
        n, vc, vf = con.execute(f"""select count(*),
            count(*) filter (where (time_casa=$c and gols_casa>gols_fora) or (time_fora=$c and gols_fora>gols_casa)),
            count(*) filter (where (time_casa=$f and gols_casa>gols_fora) or (time_fora=$f and gols_fora>gols_casa)) {base}""",
                                dict(c=casa, f=fora)).fetchone()
        return (n, vc, vf) == (p["n"], p["vc"], p["vf"]), f"SQL deu {n} jogos {vc}-{vf}"
    if t in ("tabu_visitante", "tabu_mandante"):
        n, vcasa, vfora = con.execute(f"""select count(*), count(*) filter (where gols_casa>gols_fora),
            count(*) filter (where gols_fora>gols_casa) {base} and time_casa = $c""", dict(c=casa, f=fora)).fetchone()
        if t == "tabu_visitante":
            return n == p["n"] and vfora == 0, f"SQL deu {n} jogos, {vfora} vitórias do visitante"
        return n == p["n"] and vcasa == p["v"], f"SQL deu {n} jogos, {vcasa} vitórias do mandante"
    if t in ("h2h_vitorias", "h2h_invicto"):
        alvo = p["time"]
        res = con.execute(f"""select case when (time_casa=$a and gols_casa>gols_fora) or (time_fora=$a and gols_fora>gols_casa) then 'V'
            when gols_casa=gols_fora then 'E' else 'D' end {base} order by data desc""", dict(c=casa, f=fora, a=alvo)).fetchall()
        res = [x[0] for x in res]
        ok_set = {"V"} if t == "h2h_vitorias" else {"V", "E"}
        n = 0
        while n < len(res) and res[n] in ok_set:
            n += 1
        return n == p["n"], f"SQL deu sequência de {n}"
    if t in ("h2h_gols_muitos", "h2h_gols_poucos"):
        n, media, tres = con.execute(f"select count(*), avg(gols_casa+gols_fora), count(*) filter (where gols_casa+gols_fora>=3) {base}",
                                     dict(c=casa, f=fora)).fetchone()
        return n == p["n"] and abs(media - p["media"]) < 0.01 and tres == p["tres"], f"SQL deu média {media:.2f}"
    if t == "ultimo_elastico":
        ult = con.execute(f"select gols_casa, gols_fora {base} order by data desc limit 1", dict(c=casa, f=fora)).fetchone()
        r = hl.loc[p["id"]]
        return ult == (r.gols_casa, r.gols_fora), "último jogo diferente"
    return False, "tipo sem checagem"


def _jogador(c, jp, ate):
    p = c["prova"]
    if c["tipo"] == "jogador_seq_gols":
        jogos = [r for r in jp[jp.understat_id_jogador.values == p["jogador"]].itertuples() if r.time == p["time"] and r.data < ate]
        jogos.sort(key=lambda r: r.data, reverse=True)
        n, gols = 0, 0
        for r in jogos:
            if r.gols <= 0:
                break
            n += 1
            gols += r.gols
        return (n, gols) == (p["n"], p["gols"]), f"laço deu {n} jogos e {gols} gols"
    if c["tipo"] == "artilheiro":
        con = duckdb.connect()
        con.register("j", jp[["understat_id_jogador", "liga_us", "temporada", "gols", "data"]])
        liga = jp.loc[jp.understat_id_jogador == p["jogador"], "liga_us"].iloc[-1]
        top = con.execute("""select understat_id_jogador, sum(gols) g from j where temporada = $t and liga_us = $l and data < $d
            group by 1 order by g desc limit 1""", dict(t=p["temporada"], l=liga, d=ate)).fetchone()
        return top[1] == p["gols"], f"SQL deu artilheiro com {top[1]}"
    return False, "tipo sem checagem"


def conferir(c, hl, jp, casa, fora, ate):
    try:
        if c["tipo"] in CONDICOES:
            return _seq(c, hl, ate)
        if c["grupo"] == "jogador":
            return _jogador(c, jp, ate)
        return _h2h(c, hl, casa, fora, ate)
    except Exception as e:  # qualquer erro na checagem descarta a curiosidade
        return False, f"erro na checagem: {e!r}"
