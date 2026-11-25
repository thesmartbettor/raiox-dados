"""Encerramento "Como terminou" também no Instagram (pedido do Gabriel em 10/11/2026).

Roda DEPOIS de `encerramento.py --data <dia>` (com ou sem --publicar), que gera cartoes/fechamento.jpg e
encerramento.json. Publica o cartão como post único no feed, com legenda que lista o placar e o
destino de cada curiosidade. Exige o dia aprovado e registra "fechamento_ig" em publicados.json
(impede post em dobro).

  python3 encerramento_instagram.py --data 2026-11-11            # só mostra a legenda
  python3 encerramento_instagram.py --data 2026-11-11 --publicar # publica no Instagram

Só estatística de futebol.
"""
import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import publicar as P  # noqa: E402
from caminhos import SAIDA  # noqa: E402

BRT = timezone(timedelta(hours=-3))
SIMBOLO = {"manteve": "✅", "caiu": "❌", "info": "➖"}


def legenda(dia, enc, jogos):
    nomes = {j["id"]: f"{j['casa']} x {j['fora']}" for j in jogos}
    dd = date.fromisoformat(dia)
    itens = [s for j in enc["jogos"] if j["placar"] for s, _ in j["itens"] if s != "info"]
    k = sum(1 for s in itens if s == "manteve")
    linhas = [f"📊 Como terminou, {dd.day}/{dd.month}. O que aconteceu com as curiosidades de hoje depois dos jogos.", ""]
    if len(itens) == 1:
        linhas += [f"A curiosidade publicada de manhã {'se manteve' if k else 'caiu'}.", ""]
    elif itens:
        linhas += [f"Das {len(itens)} curiosidades publicadas de manhã, {k} {'se manteve' if k == 1 else 'se mantiveram'}.", ""]
    for j in enc["jogos"]:
        if not j["placar"]:
            continue
        casa, _, fora = nomes.get(j["id"], " x ").partition(" x ")
        gc, gf = j["placar"]
        linhas.append(f"⚽ {casa} {gc} x {gf} {fora}")
        linhas += [f"{SIMBOLO[s]} {re.sub(r'(?<![0-9])1 (gol|empate)s', r'1 \1', f)}" for s, f in j["itens"]]
        linhas.append("")
    linhas += ["✅ se manteve  ❌ caiu  ➖ atualizado", "",
               "Números calculados a partir dos resultados dos campeonatos nacionais.",
               "Siga @RaioXJogo para receber as curiosidades todos os dias.", "",
               "#futebol #estatisticas #RaioXdoJogo"]
    return P.encurtar_legenda("\n".join(linhas))


def publicar_ig(pasta, txt):
    arq, feitos = P.registro(pasta)
    if "fechamento_ig" in feitos:
        sys.exit(f"encerramento do Instagram já publicado ({feitos['fechamento_ig']['id']})")
    img = pasta / "cartoes" / "fechamento.jpg"
    if not img.exists():
        sys.exit("falta cartoes/fechamento.jpg: rode encerramento.py antes")
    token = P.token_ig()
    uid = P.ig_chamar("GET", "me", token, fields="user_id")["user_id"]
    url = P.hospedar(img)
    cid = P.ig_chamar("POST", f"{uid}/media", token, image_url=url, caption=txt)["id"]
    P.esperar_pronto(cid, token)
    inicio = datetime.now(timezone.utc)
    r = requests.post(f"{P.IG}/{uid}/media_publish", params={"creation_id": cid, "access_token": token}, timeout=60)
    if r.status_code < 400:
        mid = r.json()["id"]
        link = P.ig_chamar("GET", mid, token, fields="permalink").get("permalink", "")
    else:
        # desde 6/11 o Instagram responde "action is blocked" (2207051) mesmo publicando: confere o perfil
        time.sleep(20)
        recentes = P.ig_chamar("GET", f"{uid}/media", token, fields="id,permalink,timestamp", limit=3)["data"]
        novo = [m for m in recentes if datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z") >= inicio - timedelta(minutes=2)]
        if not novo:
            sys.exit(f"Instagram recusou media_publish ({r.status_code}): {r.text}")
        mid, link = novo[0]["id"], novo[0]["permalink"]
        print("aviso: o Instagram respondeu erro, mas o post apareceu no perfil")
    feitos["fechamento_ig"] = dict(id=mid, link=link, publicado_em=datetime.now(BRT).isoformat(timespec="seconds"))
    arq.write_text(json.dumps(feitos, indent=1))
    print(f"encerramento publicado no Instagram: {link or mid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=datetime.now(BRT).strftime("%Y-%m-%d"))
    ap.add_argument("--publicar", action="store_true")
    a = ap.parse_args()
    pasta = SAIDA / a.data
    enc_arq = pasta / "encerramento.json"
    if not enc_arq.exists():
        sys.exit("falta encerramento.json: rode encerramento.py antes")
    enc = json.loads(enc_arq.read_text())
    jogos = json.loads((pasta / "posts.json").read_text())["jogos"]
    txt = legenda(a.data, enc, jogos)
    print(txt)
    if a.publicar:
        if P.REVISAO_MANUAL and not (pasta / "aprovado.json").exists():
            sys.exit(f"{a.data}: dia não aprovado; encerramento não publicado.")
        publicar_ig(pasta, txt)


if __name__ == "__main__":
    main()
