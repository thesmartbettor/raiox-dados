"""Publica os posts gerados por gerar_posts.py.

Uso:
  python3 publicar.py x --data 2026-10-25 --pendentes   # publica no X os posts cujo horário já chegou
  python3 publicar.py x --texto "Teste"                  # post avulso (teste)
  python3 publicar.py instagram --data 2026-10-25       # publica o carrossel do dia
  python3 publicar.py aprovar --data 2026-10-25          # registra a aprovação do dia

Enquanto REVISAO_MANUAL for True, nada do dia é publicado sem saida/<data>/aprovado.json.
Cada post publicado fica em saida/<data>/publicados.json, o que impede publicar duas vezes.

Chaves do X (variáveis de ambiente): X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.
Instagram: IG_ACCESS_TOKEN (token da Meta; renovar com `publicar.py renovar-ig`) e IMGBB_API_KEY
(hospedagem pública das imagens, exigida pela Meta).
"""
import argparse
import json
import time
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests_oauthlib import OAuth1

AQUI = Path(__file__).resolve().parent
BRT = ZoneInfo("America/Sao_Paulo")
REVISAO_MANUAL = True
API = "https://api.x.com/2"
IG = "https://graph.instagram.com"
sys.path.insert(0, str(AQUI))
from caminhos import SAIDA  # noqa: E402


def auth_x():
    nomes = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]
    faltam = [n for n in nomes if not os.environ.get(n)]
    if faltam:
        sys.exit(f"Faltam as chaves do X no ambiente: {', '.join(faltam)}")
    return OAuth1(*(os.environ[n] for n in nomes))


def subir_imagem(caminho, auth):
    with open(caminho, "rb") as f:
        r = requests.post(f"{API}/media/upload", auth=auth, files={"media": f},
                          data={"media_category": "tweet_image"}, timeout=60)
    r.raise_for_status()
    return r.json()["data"]["id"]


def postar_x(texto, auth, imagem=None):
    corpo = {"text": texto}
    if imagem:
        corpo["media"] = {"media_ids": [subir_imagem(imagem, auth)]}
    r = requests.post(f"{API}/tweets", auth=auth, json=corpo, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"X recusou o post ({r.status_code}): {r.text}")
    return r.json()["data"]["id"]


def registro(pasta):
    arq = pasta / "publicados.json"
    return arq, (json.loads(arq.read_text()) if arq.exists() else {})


def jogos_do_post(p, jogos):
    """Jogos citados no post: o próprio jogo, a lista 'jogos' ou, no resumo, os confrontos do texto."""
    if p.get("jogo"):
        return [j for j in jogos if j["id"] == p["jogo"]]
    if p.get("jogos"):
        return [j for j in jogos if j["id"] in p["jogos"]]
    return [j for j in jogos if f"{j['casa']} x {j['fora']}" in p["texto"]]


def x_pendentes(dia, auth):
    pasta = SAIDA / dia
    if REVISAO_MANUAL and not (pasta / "aprovado.json").exists():
        sys.exit(f"{dia}: posts ainda não aprovados; nada publicado.")
    dados = json.loads((pasta / "posts.json").read_text())
    posts, jogos = dados["x"], dados.get("jogos", [])
    arq, feitos = registro(pasta)
    agora_dt = datetime.now(BRT)
    agora = agora_dt.strftime("%H:%M")
    for i, p in enumerate(posts):
        chave = f"x_{i}"
        if chave in feitos or p["horario"] > agora:
            continue
        # Regra do Gabriel (3/11): post atrasado sai mesmo assim, desde que nenhum jogo citado
        # nele tenha começado; se algum já começou, o post é pulado.
        comecados = [f"{j['casa']} x {j['fora']}" for j in jogos_do_post(p, jogos)
                     if datetime.fromisoformat(j["inicio"]) <= agora_dt]
        if comecados:
            feitos[chave] = dict(id=None, horario=p["horario"], pulado="jogo já começou: " + ", ".join(comecados))
            arq.write_text(json.dumps(feitos, indent=1))
            print(f"pulado {chave} ({p['horario']}): jogo já começou ({', '.join(comecados)})")
            continue
        img = pasta / p["imagem"] if p.get("imagem") else None
        pid = postar_x(p["texto"], auth, img)
        feitos[chave] = dict(id=pid, horario=p["horario"], publicado_em=datetime.now(BRT).isoformat(timespec="seconds"))
        arq.write_text(json.dumps(feitos, indent=1))
        print(f"publicado {chave} ({p['horario']}): https://x.com/RaioXJogo/status/{pid}")


def token_ig():
    """Token do Instagram só pelo ambiente (IG_ACCESS_TOKEN). Tokens da Meta vencem em ~60 dias: renove
    com `python3 publicar.py renovar-ig` e troque o valor da variável pelo token impresso."""
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        sys.exit("Falta IG_ACCESS_TOKEN no ambiente")
    return token


def renovar_ig():
    r = requests.get(f"{IG}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token_ig()}, timeout=30)
    r.raise_for_status()
    d = r.json()
    print(f"Token novo (vale {d.get('expires_in', 0) // 86400} dias). Guarde em IG_ACCESS_TOKEN:\n{d['access_token']}")


def ig_chamar(metodo, caminho, token, **params):
    r = requests.request(metodo, f"{IG}/{caminho}", params={**params, "access_token": token}, timeout=60)
    if r.status_code >= 400:
        sys.exit(f"Instagram recusou {caminho} ({r.status_code}): {r.text}")
    return r.json()


def hospedar(caminho):
    chave = os.environ.get("IMGBB_API_KEY") or sys.exit("Falta IMGBB_API_KEY no ambiente")
    erro = ""
    for tentativa in range(5):
        try:
            with open(caminho, "rb") as f:
                r = requests.post("https://api.imgbb.com/1/upload", params={"key": chave}, files={"image": f}, timeout=60)
            if r.ok:
                break
            erro = f"{r.status_code}: {r.text[:300]}"
        except requests.RequestException as e:  # conexão caída no meio do envio
            erro = str(e)[:300]
        time.sleep(5 * (tentativa + 1))
    else:
        sys.exit(f"ImgBB recusou {caminho.name} ({erro})")
    return r.json()["data"]["url"]


def esperar_pronto(cid, token):
    for _ in range(30):
        st = ig_chamar("GET", cid, token, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram não processou o item {cid}: {st}")
        time.sleep(5)
    sys.exit(f"Instagram demorou demais para processar {cid}")


LIMITE_LEGENDA = 2200  # limite do Instagram


def encurtar_legenda(txt):
    """Tira bullets do fim (mantendo ao menos um por jogo) até caber no limite do Instagram."""
    linhas = txt.split("\n")
    while len("\n".join(linhas)) > LIMITE_LEGENDA:
        for i in range(len(linhas) - 1, 0, -1):
            if linhas[i].startswith("• ") and linhas[i - 1].startswith("• "):
                del linhas[i]
                break
        else:
            break
    return "\n".join(linhas)


def instagram(dia):
    pasta = SAIDA / dia
    if REVISAO_MANUAL and not (pasta / "aprovado.json").exists():
        sys.exit(f"{dia}: posts ainda não aprovados; nada publicado.")
    arq, feitos = registro(pasta)
    if "instagram" in feitos:
        sys.exit(f"{dia}: carrossel já publicado ({feitos['instagram']['id']})")
    ig = json.loads((pasta / "posts.json").read_text())["instagram"]
    token = token_ig()
    uid = ig_chamar("GET", "me", token, fields="user_id,username")["user_id"]
    filhos = []
    for nome in ig["cartoes"][:20]:
        url = hospedar(pasta / "cartoes" / nome)
        filhos.append(ig_chamar("POST", f"{uid}/media", token, image_url=url, is_carousel_item="true")["id"])
    for cid in filhos:
        esperar_pronto(cid, token)
    car = ig_chamar("POST", f"{uid}/media", token, media_type="CAROUSEL", children=",".join(filhos), caption=encurtar_legenda(ig["legenda"]))["id"]
    esperar_pronto(car, token)
    inicio = datetime.now(timezone.utc)
    r = requests.post(f"{IG}/{uid}/media_publish", params={"creation_id": car, "access_token": token}, timeout=60)
    if r.status_code < 400:
        mid = r.json()["id"]
        link = ig_chamar("GET", mid, token, fields="permalink").get("permalink", "")
    else:
        # Desde 6/11 o Instagram devolve "action is blocked" (2207051) mesmo publicando.
        # Antes de tratar como falha, confere se apareceu um post novo no perfil.
        time.sleep(20)
        recentes = ig_chamar("GET", f"{uid}/media", token, fields="id,permalink,timestamp", limit=3)["data"]
        novo = [m for m in recentes if datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z") >= inicio - timedelta(minutes=2)]
        if not novo:
            sys.exit(f"Instagram recusou media_publish ({r.status_code}): {r.text}")
        mid, link = novo[0]["id"], novo[0]["permalink"]
        print("aviso: o Instagram respondeu erro, mas o carrossel apareceu no perfil")
    feitos["instagram"] = dict(id=mid, link=link, publicado_em=datetime.now(BRT).isoformat(timespec="seconds"))
    arq.write_text(json.dumps(feitos, indent=1))
    print(f"carrossel publicado: {link or mid}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["x", "instagram", "aprovar", "renovar-ig"])
    ap.add_argument("--data", default=datetime.now(BRT).date().isoformat())
    ap.add_argument("--pendentes", action="store_true")
    ap.add_argument("--texto")
    ap.add_argument("--imagem")
    a = ap.parse_args()
    if a.acao == "aprovar":
        pasta = SAIDA / a.data
        (pasta / "aprovado.json").write_text(json.dumps({"aprovado_em": datetime.now(BRT).isoformat(timespec="seconds")}))
        print(f"{a.data} aprovado")
    elif a.acao == "renovar-ig":
        renovar_ig()
    elif a.acao == "instagram":
        instagram(a.data)
    elif a.texto:
        print("publicado:", postar_x(a.texto, auth_x(), a.imagem))
    elif a.pendentes:
        x_pendentes(a.data, auth_x())


if __name__ == "__main__":
    main()
