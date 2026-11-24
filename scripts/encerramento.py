"""Mensagem de encerramento do dia (pedido do Gabriel em 6/11/2026).

Depois dos jogos, confere na TheStatsAPI o placar de cada jogo do carrossel e diz, para cada
curiosidade publicada, se ela se manteve ou caiu. Gera um cartão (cartoes/fechamento.jpg) e o
texto do post do X, e publica com --publicar (exige o dia aprovado, como o resto).

  python3 encerramento.py --data 2026-11-06            # só gera e mostra
  python3 encerramento.py --data 2026-11-06 --publicar # gera e posta no X
  python3 encerramento.py --data 2026-11-06 --horario  # imprime o horário (Brasília) para agendar

Só estatística de futebol.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import cartoes as C  # noqa: E402
from caminhos import SAIDA  # noqa: E402

BRT = timezone(timedelta(hours=-3))
API = "https://api.thestatsapi.com/api/football/matches/"

CONTINUA = {
    "vitorias_seguidas": lambda r: r["res"] == "V", "vitorias_casa": lambda r: r["res"] == "V",
    "vitorias_fora": lambda r: r["res"] == "V",
    "invicto": lambda r: r["res"] != "D", "invicto_casa": lambda r: r["res"] != "D", "invicto_fora": lambda r: r["res"] != "D",
    "derrotas_seguidas": lambda r: r["res"] == "D",
    "sem_vencer": lambda r: r["res"] != "V", "sem_vencer_casa": lambda r: r["res"] != "V", "sem_vencer_fora": lambda r: r["res"] != "V",
    "sem_sofrer": lambda r: r["gc"] == 0, "sem_marcar": lambda r: r["gp"] == 0, "marcou_todos": lambda r: r["gp"] > 0,
}


def jogos_do_carrossel(dia):
    d = json.loads((SAIDA / dia / "posts.json").read_text())
    n = sum(1 for c in d["instagram"]["cartoes"] if c.endswith("_jogo.jpg"))
    return d["jogos"][:n]


def placar(match_id):
    r = requests.get(API + match_id, headers={"Authorization": "Bearer " + os.environ["THESTATSAPI_KEY"]}, timeout=60)
    if r.status_code != 200:
        return None
    m = r.json()["data"]
    if m.get("status") != "finished" or m.get("score", {}).get("home") is None:
        return None
    reg = m["score"].get("regulation") or m["score"]
    return int(reg["home"]), int(reg["away"])


def visto_de(lado, gc_, gf_):
    gp, gc = (gc_, gf_) if lado == "casa" else (gf_, gc_)
    return dict(gp=gp, gc=gc, res="V" if gp > gc else "E" if gp == gc else "D")


def lado_por_nome(j, rotulo):
    nome = rotulo.split("·", 1)[-1].strip()
    return "casa" if nome.startswith(j["casa"]) else "fora"


def avaliar(j, gc, gf):
    """Lista de (status, frase) para cada curiosidade: status 'manteve', 'caiu' ou 'info'."""
    out = []
    casa, fora = j["casa"], j["fora"]
    for c in j["curiosidades"]:
        t, p = c["tipo"], c.get("prova", {})
        n = p.get("n")
        if t in CONTINUA:
            lado = c["time"]
            nome = casa if lado == "casa" else fora
            if CONTINUA[t](visto_de(lado, gc, gf)):
                out.append(("manteve", re.sub(rf"\b{n}\b", str(n + 1), c["curto"], count=1), c))
            else:
                out.append(("caiu", f"Acabou a série de {nome}: {n} {C.LEGENDA.get(t, '')}", c))
        elif t == "tabu_visitante":
            if gf > gc:
                out.append(("caiu", f"{fora} venceu lá pela primeira vez em {n + 1} jogos", c))
            else:
                out.append(("manteve", f"{fora} segue sem vencer lá ({n + 1} jogos)", c))
        elif t == "tabu_mandante":
            v = p.get("v", 0)
            if gc > gf:
                out.append(("caiu", f"{casa} venceu em casa: agora {v + 1} vitórias em {n + 1} jogos", c))
            else:
                out.append(("manteve", f"{casa} segue com {v} vitórias em {n + 1} jogos em casa", c))
        elif t in ("h2h_vitorias", "h2h_invicto"):
            lado = lado_por_nome(j, c["rotulo"])
            nome, outro = (casa, fora) if lado == "casa" else (fora, casa)
            r = visto_de(lado, gc, gf)
            ok = r["res"] == "V" if t == "h2h_vitorias" else r["res"] != "D"
            if ok:
                o = "vitórias seguidas" if t == "h2h_vitorias" else "jogos sem perder"
                out.append(("manteve", f"{nome}: {n + 1} {o} contra {outro}", c))
            else:
                out.append(("caiu", f"{outro} quebrou a série de {n} de {nome} no duelo", c))
        elif t == "h2h_geral":
            vc, e, vf = p["vc"] + (gc > gf), p["e"] + (gc == gf), p["vf"] + (gf > gc)
            out.append(("info", f"Duelo agora: {casa} {vc} x {vf} {fora}, {e} empates em {n + 1} jogos", c))
        elif t in ("h2h_gols_muitos", "h2h_gols_poucos"):
            tot = gc + gf
            ok = tot >= 3 if t == "h2h_gols_muitos" else tot <= 2
            out.append(("manteve" if ok else "caiu",
                        f"{tot} gols desta vez ({'confirmou' if ok else 'fugiu d'}{'' if ok else 'o'} {'o confronto de muitos gols' if t.endswith('muitos') else 'o confronto de poucos gols'})", c))
        # curiosidades de jogador e de último confronto ficam de fora (não dá para conferir só pelo placar)
    return out


def montar(dia):
    linhas = []
    for j in jogos_do_carrossel(dia):
        pl = placar(j["id"])
        if pl is None:
            linhas.append(dict(jogo=j, placar=None, itens=[]))
            continue
        linhas.append(dict(jogo=j, placar=pl, itens=avaliar(j, *pl)))
    return linhas


def texto_x(dia, linhas):
    """Regras do X (7/11): a curiosidade que mais chamou atenção na 1ª linha, sem emoji no começo,
    sem hashtag nem gancho de clique, até 6 linhas e 280 caracteres. A imagem traz todos os jogos."""
    itens = [i for l in linhas for i in l["itens"] if i[0] != "info"]
    k = sum(1 for i in itens if i[0] == "manteve")
    caidas = sorted([i for i in itens if i[0] == "caiu"], key=lambda i: -i[2]["nota"])
    mantidas = sorted([i for i in itens if i[0] == "manteve"], key=lambda i: -i[2]["nota"])
    abertura = (caidas or mantidas)[0][1] + "." if (caidas or mantidas) else "Como terminaram as curiosidades de hoje."
    partes = [abertura, "", f"Das {len(itens)} curiosidades publicadas hoje, {k} se mantiveram depois dos jogos."]
    if caidas and mantidas:
        partes.append(f"{mantidas[0][1]}, e contando.")
    partes.append("Todos os placares e o que mudou estão no quadro.")
    txt = "\n".join(partes)
    while len(txt) > 280 and len(partes) > 3:
        partes.pop(3)
        txt = "\n".join(partes)
    import regras_x
    return regras_x.conferir(txt)


def cartao(dia, linhas, destino):
    C.aplicar_tema(C.tema_do_dia(date.fromisoformat(dia)))
    C.ARROBA = C.ARROBA_X
    im, d = C.base()
    C.marca(d)
    dd = date.fromisoformat(dia)
    d.text((C.M, 130), "COMO TERMINOU", font=C.fonte("Black", 76), fill=C.TEXTO)
    d.text((C.M, 215), f"{C.DIAS[dd.weekday()]}, {dd.day} de {C.MESES[dd.month - 1]}", font=C.fonte("Medium", 34), fill=C.SUAVE)
    jogadas = [l for l in linhas if l["placar"]]
    n_itens = sum(len(l["itens"]) for l in jogadas)
    disponivel = C.A - 220 - 300
    # tamanho das letras conforme a quantidade de linhas
    passo_j, passo_i = 58, 40
    escala = min(1.0, disponivel / max(1, len(jogadas) * (passo_j + 14) + n_itens * passo_i))
    pj, pi = int(passo_j * escala), int(passo_i * escala)
    fj, fi = C.fonte("Bold", max(22, int(38 * escala))), C.fonte("Regular", max(18, int(28 * escala)))
    y = 300
    for l in jogadas:
        j, (gc, gf) = l["jogo"], l["placar"]
        txt = f"{j['casa']} {gc} x {gf} {j['fora']}"
        d.text((C.M, y), txt, font=C.ajustar(d, txt, "Bold", fj.size, C.L - 2 * C.M, minimo=20), fill=C.TEXTO)
        y += pj
        for st, frase, _ in l["itens"]:
            cor = {"manteve": C.DESTAQUE, "caiu": (235, 87, 87), "info": C.SUAVE}[st]
            r = max(6, int(9 * escala))
            d.ellipse([C.M + 4, y + pi / 2 - r - 2, C.M + 4 + 2 * r, y + pi / 2 + r - 2], fill=cor)
            f = C.ajustar(d, frase, "Regular", fi.size, C.L - 2 * C.M - 40, minimo=16)
            d.text((C.M + 40, y + 2), frase, font=f, fill=C.TEXTO)
            y += pi
        y += 14
    # legenda das cores
    fl = C.fonte("Medium", 24)
    x = C.M
    for cor, rot in ((C.DESTAQUE, "se manteve"), ((235, 87, 87), "caiu"), (C.SUAVE, "atualizado")):
        d.ellipse([x, C.A - 150, x + 18, C.A - 132], fill=cor)
        d.text((x + 28, C.A - 156), rot, font=fl, fill=C.SUAVE)
        x += 60 + C.larg(d, rot, fl)
    C.rodape(d)
    im.save(destino, "JPEG", quality=92)


def horario(dia):
    jogos = jogos_do_carrossel(dia)
    ultimo = max(datetime.fromisoformat(j["inicio"]) for j in jogos)
    return (ultimo + timedelta(hours=2, minutes=20)).astimezone(BRT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=datetime.now(BRT).strftime("%Y-%m-%d"))
    ap.add_argument("--publicar", action="store_true")
    ap.add_argument("--horario", action="store_true")
    a = ap.parse_args()
    if a.horario:
        print(horario(a.data).strftime("%Y-%m-%dT%H:%M"))
        return
    pasta = SAIDA / a.data
    linhas = montar(a.data)
    if not any(l["placar"] for l in linhas):
        sys.exit("nenhum jogo terminado ainda; nada a encerrar")
    img = pasta / "cartoes" / "fechamento.jpg"
    cartao(a.data, linhas, img)
    txt = texto_x(a.data, linhas)
    (pasta / "encerramento.json").write_text(json.dumps(
        dict(texto=txt, jogos=[dict(id=l["jogo"]["id"], placar=l["placar"], itens=[(s, f) for s, f, _ in l["itens"]]) for l in linhas]),
        ensure_ascii=False, indent=1))
    print(txt)
    pend = [l["jogo"]["casa"] + " x " + l["jogo"]["fora"] for l in linhas if not l["placar"]]
    if pend:
        print("sem placar ainda:", ", ".join(pend))
    if a.publicar:
        import publicar as P
        if P.REVISAO_MANUAL and not (pasta / "aprovado.json").exists():
            sys.exit(f"{a.data}: dia não aprovado; encerramento não publicado.")
        arq, feitos = P.registro(pasta)
        if "fechamento" in feitos:
            sys.exit("encerramento já publicado")
        pid = P.postar_x(txt, P.auth_x(), img)
        feitos["fechamento"] = dict(id=pid, publicado_em=datetime.now(BRT).isoformat(timespec="seconds"))
        arq.write_text(json.dumps(feitos, indent=1))
        print(f"encerramento publicado: https://x.com/RaioXJogo/status/{pid}")


if __name__ == "__main__":
    main()
