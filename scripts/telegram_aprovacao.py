"""Aprovação dos posts do dia pelo Telegram (bot do Gabriel).

  python3 telegram_aprovacao.py enviar  --data 2026-11-02   # manda prévia + botões
  python3 telegram_aprovacao.py esperar --data 2026-11-02 --ate 10:50
      fica ouvindo o bot até uma decisão ou até o horário (Brasília) e imprime
      uma linha: DECISAO aprovar | DECISAO nao_publicar | DECISAO ajustes <texto> | SEM_RESPOSTA
  python3 telegram_aprovacao.py avisar "texto"              # mensagem simples
  python3 telegram_aprovacao.py limpar --data 2026-11-02    # apaga as mensagens do dia
Depois de qualquer decisão, as mensagens que o Raio-X enviou no dia são apagadas (só as dele).

Só valem toques e mensagens do chat em TELEGRAM_CHAT_ID.
Também aceita comandos escritos: /aprovar, /naopublicar, /ajustes <o que mudar>.
Token em TELEGRAM_BOT_TOKEN e chat em TELEGRAM_CHAT_ID (variáveis do ambiente, nunca em arquivo).
Link opcional da página de revisão em RAIOX_REVISAO_URL.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BRT = timezone(timedelta(hours=-3))
CHAT_GABRIEL = int(os.environ.get("TELEGRAM_CHAT_ID") or 0)
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from caminhos import SAIDA  # noqa: E402
OFFSET = SAIDA / "_telegram" / "offset.json"
REVISAO = os.environ.get("RAIOX_REVISAO_URL", "")


def api(metodo, arquivos=None, **params):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{metodo}"
    for tentativa in range(4):
        try:
            if arquivos:
                r = requests.post(url, data=params, files=arquivos, timeout=120)
            else:
                r = requests.post(url, json=params, timeout=70)
            j = r.json()
            if j.get("ok"):
                return j["result"]
            erro = j
        except (requests.RequestException, ValueError) as e:
            erro = str(e)[:300]
        time.sleep(3 * (tentativa + 1))
    sys.exit(f"Telegram falhou em {metodo}: {erro}")


def enviar(dia):
    pasta = SAIDA / dia
    posts = json.loads((pasta / "posts.json").read_text())
    cartoes = sorted((pasta / "cartoes").glob("0*.jpg"))[:10]
    # carrossel como álbum
    media, arquivos = [], {}
    for i, c in enumerate(cartoes):
        media.append({"type": "photo", "media": f"attach://f{i}"})
        arquivos[f"f{i}"] = open(c, "rb")
    media[0]["caption"] = f"Carrossel do Instagram de {dia[8:]}/{dia[5:7]}"
    ids = [x["message_id"] for x in api("sendMediaGroup", arquivos=arquivos, chat_id=CHAT_GABRIEL, media=json.dumps(media))]
    for f in arquivos.values():
        f.close()
    # posts do X, um bloco só (limite de 4096 caracteres por mensagem)
    blocos, atual = [], ""
    for p in posts["x"]:
        trecho = f"🕐 {p['horario']}\n{p['texto']}\n\n"
        if len(atual) + len(trecho) > 3900:
            blocos.append(atual)
            atual = ""
        atual += trecho
    blocos.append(atual)
    for i, b in enumerate(blocos):
        cab = "Posts do X de hoje\n\n" if i == 0 else ""
        ids.append(api("sendMessage", chat_id=CHAT_GABRIEL, text=cab + b.strip(), disable_web_page_preview=True)["message_id"])
    horarios = ", ".join(p["horario"] for p in posts["x"])
    teclado = {"inline_keyboard": [
        [{"text": "✅ Aprovar", "callback_data": f"aprovar:{dia}"}],
        [{"text": "✏️ Ajustes", "callback_data": f"ajustes:{dia}"},
         {"text": "⛔ Não publicar hoje", "callback_data": f"nao_publicar:{dia}"}],
    ]}
    m = api("sendMessage", chat_id=CHAT_GABRIEL, reply_markup=teclado, disable_web_page_preview=True,
            text=(f"Aprova os posts de {dia[8:]}/{dia[5:7]}?\n\nInstagram às 8h (ou na aprovação), "
                  f"X às {horarios}.\nPrévia completa: {REVISAO}"))
    ids.append(m["message_id"])
    anteriores = ler_ids(dia)  # um reenvio depois de ajustes acumula
    (pasta / "telegram.json").write_text(json.dumps({"mensagem_id": m["message_id"], "ids": anteriores + ids}))
    print("enviado ao Telegram, mensagem", m["message_id"])


def ler_ids(dia):
    try:
        return json.loads((SAIDA / dia / "telegram.json").read_text()).get("ids", [])
    except Exception:
        return []


def anotar_id(dia, mid):
    arq = SAIDA / dia / "telegram.json"
    try:
        d = json.loads(arq.read_text())
    except Exception:
        d = {}
    d.setdefault("ids", []).append(mid)
    arq.write_text(json.dumps(d))


def limpar_chat(dia):
    """Apaga do chat só as mensagens que o próprio Raio-X enviou no dia (prévia, botões, pedidos).
    Nunca apaga mensagens do Gabriel nem de outros projetos. Pedido do Gabriel em 2/11.
    O Telegram só deixa apagar mensagens com menos de 48 h."""
    ids = sorted(set(ler_ids(dia)))
    for i in range(0, len(ids), 100):
        try:
            api("deleteMessages", chat_id=CHAT_GABRIEL, message_ids=ids[i:i + 100])
        except SystemExit as e:
            print("aviso: não consegui apagar algumas mensagens:", e, file=sys.stderr)
    arq = SAIDA / dia / "telegram.json"
    if arq.exists():
        d = json.loads(arq.read_text())
        d["ids"] = []
        d["apagado_em"] = datetime.now(BRT).isoformat(timespec="seconds")
        arq.write_text(json.dumps(d))


def ler_offset():
    try:
        return json.loads(OFFSET.read_text())["offset"]
    except Exception:
        return None


def gravar_offset(n):
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(json.dumps({"offset": n}))


def fechar_botoes(dia, texto):
    # depois da decisão o chat fica limpo: nada de confirmação, tudo apagado
    limpar_chat(dia)


def esperar(dia, ate):
    h, m = map(int, ate.split(":"))
    agora = datetime.now(BRT)
    fim = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    # O bot é compartilhado com outros projetos do Gabriel. Para não "comer" mensagens deles,
    # o offset só avança sobre atualizações que são nossas; as dos outros ficam no servidor.
    offset = ler_offset()
    vistos = set()     # tudo o que já passou por aqui
    alheios = set()    # atualizações de outros projetos (nunca confirmadas)
    esperando_ajuste = False
    acoes = {"aprovar", "ajustes", "nao_publicar"}

    def consumir(uid):
        nonlocal offset
        vistos.add(uid)
        if not any(a < uid for a in alheios):
            offset = max(offset or 0, uid + 1)
            gravar_offset(offset)

    while datetime.now(BRT) < fim:
        restante = int((fim - datetime.now(BRT)).total_seconds())
        params = {"timeout": max(1, min(50, restante)), "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        novos = [u for u in api("getUpdates", **params) if u["update_id"] not in vistos]
        if not novos:
            time.sleep(3)  # com mensagens alheias pendentes o getUpdates volta na hora
            continue
        for u in novos:
            uid = u["update_id"]
            cb = u.get("callback_query")
            msg = u.get("message")
            if cb:
                acao, _, dia_cb = cb.get("data", "").partition(":")
                if cb["from"]["id"] != CHAT_GABRIEL or acao not in acoes or dia_cb != dia:
                    vistos.add(uid)  # de outro projeto: não responde nem confirma
                    alheios.add(uid)
                    continue
                consumir(uid)
                if acao == "ajustes":
                    api("answerCallbackQuery", callback_query_id=cb["id"])
                    anotar_id(dia, api("sendMessage", chat_id=CHAT_GABRIEL, text="Escreva aqui o que você quer mudar.")["message_id"])
                    esperando_ajuste = True
                    continue
                api("answerCallbackQuery", callback_query_id=cb["id"], text="Recebido")
                fechar_botoes(dia, "")
                print("DECISAO", acao)
                return
            if msg and msg.get("chat", {}).get("id") == CHAT_GABRIEL and msg.get("text"):
                t = msg["text"].strip()
                cmd = t.split()[0].lower().split("@")[0]
                decisao = None
                if cmd in ("/aprovar", "aprovar", "aprovo"):
                    decisao = "aprovar"
                elif cmd in ("/naopublicar", "/nao_publicar"):
                    decisao = "nao_publicar"
                elif cmd == "/ajustes" or (esperando_ajuste and not t.startswith("/")):
                    pedido = t[len(cmd):].strip() if cmd == "/ajustes" else t
                    consumir(uid)
                    if not pedido:
                        anotar_id(dia, api("sendMessage", chat_id=CHAT_GABRIEL, text="Escreva aqui o que você quer mudar.")["message_id"])
                        esperando_ajuste = True
                        continue
                    fechar_botoes(dia, "")
                    print("DECISAO ajustes", pedido.replace("\n", " "))
                    return
                if decisao:
                    consumir(uid)
                    fechar_botoes(dia, "")
                    print("DECISAO", decisao)
                    return
            vistos.add(uid)  # mensagem que não é para o Raio-X: fica para os outros projetos
            alheios.add(uid)
    print("SEM_RESPOSTA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["enviar", "esperar", "avisar", "limpar"])
    ap.add_argument("texto", nargs="?")
    ap.add_argument("--data", default=datetime.now(BRT).strftime("%Y-%m-%d"))
    ap.add_argument("--ate", default="10:50")
    a = ap.parse_args()
    if a.acao == "enviar":
        enviar(a.data)
    elif a.acao == "esperar":
        esperar(a.data, a.ate)
    elif a.acao == "limpar":
        limpar_chat(a.data)
    else:
        api("sendMessage", chat_id=CHAT_GABRIEL, text=a.texto)


if __name__ == "__main__":
    main()
