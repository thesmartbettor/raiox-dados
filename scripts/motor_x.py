"""Ajustes do X do Raio-X ao For You de 13/11/2026 (copiar link = 0; like 0,708; reply/quote/DM 5;
reply entre perfis que se seguem +15; 2º post do mesmo autor no feed vale menos; posts com mais de 48 h somem).
Pedido do Gabriel em 14/11/2026.

Roda DEPOIS de gerar_posts.py (dia) e de encerramento.py (encerramento). Não publica nada.

  python3 motor_x.py dia --data 2026-11-15          # reescreve saida/<data>/x.txt e posts.json["x"]
  python3 motor_x.py encerramento --data 2026-11-15 # texto do X do encerramento + respostas por jogo

O que muda no dia:
- Menos posts e mais espaçados: resumo às 8h e no máximo 4 jogos, um por horário de início,
  com pelo menos 2 h entre posts (o 2º post do mesmo perfil no feed perde peso).
- Cada post é uma ideia: a curiosidade mais forte na 1ª linha, no máximo mais uma do mesmo jogo,
  e uma pergunta de torcedor no fim (motivo para responder, sem pedir resposta).
- Cada post de jogo leva o cartão do jogo (tempo de leitura); a capa do X perde o "Arraste" do Instagram.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import regras_x  # noqa: E402
from caminhos import SAIDA  # noqa: E402

BRT = timezone(timedelta(hours=-3))
INTERVALO = timedelta(hours=2)
MAX_JOGOS_X = 4
PRIMEIRO = (9, 30)  # nenhum post de jogo antes das 9h30


def nome_time(j, c):
    p = c.get("prova", {})
    if c.get("time") in ("casa", "fora"):
        return j[c["time"]]
    t = p.get("time")
    if t:
        for k in ("casa", "fora"):
            if t == j[k] or t.split()[0] in j[k]:
                return j[k]
        return t
    return None


def pergunta(j, c):
    """Pergunta de torcedor ligada ao número da 1ª linha. Nada de placar, gols ou palpite."""
    t, n = c["tipo"], c.get("prova", {}).get("n")
    time = nome_time(j, c)
    if t == "vitorias_seguidas" and time and n:
        return f"{time} chega a {n + 1} seguidas hoje?"
    if t == "invicto" and time and n:
        return f"{time} chega a {n + 1} jogos sem perder?"
    if t == "sem_vencer" and time:
        return f"{time} sai da fila hoje?"
    if t == "derrotas_seguidas" and time:
        return f"{time} para de perder hoje?"
    if t == "tabu_visitante":
        return f"{j['fora']} quebra o tabu desta vez?"
    if t == "tabu_mandante":
        return f"{j['casa']} volta a vencer esse jogo em casa?"
    if t == "h2h_invicto" and time:
        return f"{time} mantém a escrita hoje?"
    if t in ("vitorias_casa", "vitorias_fora") and time and n:
        return f"{time} chega a {n + 1} seguidas {'em casa' if t.endswith('casa') else 'fora'}?"
    if t in ("invicto_casa", "invicto_fora") and time:
        return f"{time} segue invicto {'em casa' if t.endswith('casa') else 'fora'} hoje?"
    if t in ("sem_vencer_casa", "sem_vencer_fora") and time:
        return f"{time} volta a vencer {'em casa' if t.endswith('casa') else 'fora'} hoje?"
    if t == "sem_marcar" and time:
        return f"{time} volta a marcar hoje?"
    if t == "sem_sofrer" and time:
        return f"{time} segura mais um jogo sem levar gol?"
    if t == "marcou_todos" and time:
        return f"{time} marca de novo hoje?"
    if t == "jogador_seq_gols":
        return "Ele marca de novo hoje?"
    if t == "artilheiro":
        return "Ele aumenta a conta hoje?"
    p = c.get("prova", {})
    if t == "h2h_geral" and (p.get("vf") == 0 or p.get("vc") == 0) and p.get("n", 0) >= 4:
        sem = j["fora"] if p.get("vf") == 0 else j["casa"]
        return f"{sem} vence esse duelo pela primeira vez?"
    if t == "h2h_vitorias" and time:
        return f"{time} vence mais uma nesse duelo?"
    return "Qual jogo desse confronto você lembra até hoje?"


def frase(c):
    return c["texto"].strip()


def post_jogo(j, pular=0):
    cs = sorted(j["curiosidades"], key=lambda c: -c.get("nota", 0))[pular:]
    fim = f"{j['casa']} x {j['fora']}, {j['liga']}, hoje às {j['hora']}."
    q = pergunta(j, cs[0])
    for extra in ([cs[1]] if len(cs) > 1 else []) + [None]:
        partes = [frase(cs[0])] + ([frase(extra)] if extra else []) + [fim, q]
        txt = "\n\n".join(partes)
        if not regras_x.problemas(txt):
            return txt
    return regras_x.conferir("\n\n".join([frase(cs[0]), fim]))


def post_resumo(destaque, n_jogos):
    c = max(destaque["curiosidades"], key=lambda c: c.get("nota", 0))
    j = destaque
    linhas = [frase(c), f"{j['casa']} x {j['fora']}, {j['liga']}, hoje às {j['hora']}.", pergunta(j, c),
              (f"Os {n_jogos} jogos de hoje que analisamos estão no quadro, e os números de cada um saem ao longo do dia."
               if n_jogos > 1 else "O jogo de hoje que analisamos está no quadro.")]
    txt = "\n\n".join(linhas)
    if regras_x.problemas(txt):
        txt = "\n\n".join(linhas[:3])
    return regras_x.conferir(txt)


def peso_liga(j, bonus=True):
    """Peso da liga (PESO_LIGA do gerar_posts) com bônus de time grande. Brasileirão e grandes ligas
    primeiro; sem elas no dia, as maiores ligas que tiverem jogo (Gabriel, 14/11)."""
    import gerar_posts as G
    nomes = {j["casa"], j["fora"]}
    grande = any(g in nomes or any(g in n for n in nomes) for g in G.GRANDES)
    return round(G.PESO_LIGA.get(j.get("competicao"), 0.3) * (1.3 if grande and bonus else 1.0), 3)


NOTA_MIN = 3.5  # nota mínima do número que abre um post de jogo


def lider(j):
    return max(c.get("nota", 0) for c in j["curiosidades"])


def faixa(j):
    """Brasileirão e grandes ligas (peso >= 1,0) contam como uma faixa só; abaixo disso vale o peso da liga."""
    p = peso_liga(j, False)
    return 1.0 if p >= 1.0 else p


def prioridade(j):
    return (faixa(j), j["nota"])


def legenda_ig(jogos_carrossel, dia):
    """Legenda curta: um número por jogo (o mais forte), na ordem do carrossel, e uma pergunta no fim."""
    um = len(jogos_carrossel) == 1
    mais = any(len(j["curiosidades"]) > 1 for j in jogos_carrossel)
    linhas = [f"📊 Curiosidades do dia, {dia.day}/{dia.month}. "
              + ("O número do jogo de hoje." if um else "Um número de cada jogo de hoje."), ""]
    for j in sorted(jogos_carrossel, key=lambda j: j["inicio"]):
        c = max(j["curiosidades"], key=lambda c: c.get("nota", 0))
        linhas += [f"⚽ {j['casa']} x {j['fora']} | {j['liga']}, {j['hora']}", f"• {frase(c)}", ""]
    if mais:
        linhas += ["Os outros números estão no cartão." if um else "Os outros números estão nos cartões.", ""]
    linhas += ["Qual desses números você não esperava?" if mais or not um else "Você esperava esse número?", "",
               "Números calculados a partir dos resultados dos campeonatos nacionais.",
               "Siga @RaioXJogo para receber as curiosidades todos os dias.", "",
               "#futebol #estatisticas #RaioXdoJogo"]
    return "\n".join(linhas)


def agenda(jogos, dia, ocupados, ja_no_resumo=None, com_cartao=()):
    """Um jogo por horário de início (o da maior liga, depois o de maior nota), nessa mesma ordem; tenta 2h antes e desliza até
    3h antes / 40 min antes para manter 2 h de distância dos outros posts."""
    por_inicio = {}
    # o jogo que já abriu o resumo vai para o fim da sua faixa: outro jogo grande tem a vez antes
    def chave(j):
        f, n = prioridade(j)
        # jogo do carrossel primeiro: tem cartão para acompanhar o post
        return (f, j["id"] in com_cartao, j["id"] != ja_no_resumo, n)
    for j in sorted(jogos, key=chave, reverse=True):
        if j["inicio"] not in por_inicio:
            por_inicio[j["inicio"]] = j
    base = datetime.combine(dia, datetime.min.time(), BRT)
    primeiro = base.replace(hour=PRIMEIRO[0], minute=PRIMEIRO[1])
    escolhidos = []
    for j in sorted(por_inicio.values(), key=chave, reverse=True):
        if len(escolhidos) >= MAX_JOGOS_X:
            break
        ini = datetime.fromisoformat(j["inicio"])
        tentativas = [ini - timedelta(hours=2) + timedelta(minutes=15 * k) for k in
                      sorted(range(-4, 6), key=abs)]
        for h in tentativas:
            if h < primeiro or h > ini - timedelta(minutes=40):
                continue
            if all(abs(h - o) >= INTERVALO for o in ocupados):
                escolhidos.append((j, h))
                ocupados.append(h)
                break
    return sorted(escolhidos, key=lambda x: x[1])


def capa_x(pasta, dia, destaque, lista):
    """Capa do resumo das 8h no X: o número do dia em destaque e, embaixo, a lista dos jogos de hoje
    (Gabriel, 14/11: número do dia sim, mas com a lista também). Usa o tema e as fontes do dia do cartoes.py."""
    import cartoes as C
    C.aplicar_tema(C.tema_do_dia(dia))
    C.ARROBA = C.ARROBA_X
    c = max(destaque["curiosidades"], key=lambda c: c.get("nota", 0))
    M, L, A = C.M, C.L, C.A
    jogos = sorted(lista, key=lambda j: j["inicio"])

    def desenhar(d, desloc):
        y = 150 + desloc
        d.text((M, y), "NÚMERO DO DIA", font=C.fonte("Bold", 34), fill=C.DESTAQUE)
        fn = C.ajustar(d, c["numero"], "Black", 230, L - 2 * M, minimo=120)
        y += 40
        d.text((M - 6, y), c["numero"], font=fn, fill=C.DESTAQUE)
        y += int(fn.size * 1.0) + 10
        # não deixa número ou palavra curta sozinha no fim da linha ("LaLiga" / "2.")
        txt = re.sub(r" (\S{1,3})$", "\u00a7\\1", frase(c))
        ft, linhas = C.texto_ajustado(d, txt, "SemiBold", 44, L - 2 * M, 3, minimo=34)
        for ln in linhas:
            d.text((M, y), ln.replace("\u00a7", " "), font=ft, fill=C.TEXTO)
            y += int(ft.size * 1.25)
        y += 6
        sub = f"{destaque['casa']} x {destaque['fora']} · {destaque['liga']} · {destaque['hora']}"
        d.text((M, y), sub, font=C.ajustar(d, sub, "Medium", 30, L - 2 * M, minimo=22), fill=C.SUAVE)
        y += 70
        d.line([M, y, L - M, y], fill=C.FUNDO2, width=3)
        y += 24
        d.text((M, y), "JOGOS DE HOJE", font=C.fonte("Bold", 28), fill=C.SUAVE)
        y += 50
        passo = max(46, min(92, (A - 130 - y) // max(len(jogos), 1)))
        tam = 34 if passo >= 70 else 28
        for j in jogos:
            if y + passo - 10 > A - 125:
                break
            d.rounded_rectangle([M, y, L - M, y + passo - 10], radius=16, fill=C.FUNDO2)
            cy = y + (passo - 10) / 2
            d.text((M + 24, cy - tam * 0.62), j["hora"], font=C.fonte("Bold", tam), fill=C.DESTAQUE)
            nome = f"{j['casa']} x {j['fora']}"
            fl = C.fonte("Regular", tam - 10)
            livre = L - 2 * M - 180 - C.larg(d, j["liga"], fl) - 40
            fj = C.ajustar(d, nome, "SemiBold", tam, livre, minimo=20)
            d.text((M + 170, cy - fj.size * 0.62), nome, font=fj, fill=C.TEXTO)
            d.text((L - M - 24 - C.larg(d, j["liga"], fl), cy - fl.size * 0.6), j["liga"], font=fl, fill=C.SUAVE)
            y += passo
        return y

    _, rascunho = C.base()
    fim = desenhar(rascunho, 0)
    sobra = (A - 140) - fim  # dias com poucos jogos: centraliza o bloco em vez de deixar o fundo vazio
    im, d = C.base()
    C.marca(d)
    fd = C.fonte("Medium", 30)
    data = f"{C.DIAS[dia.weekday()]}, {dia.day} de {C.MESES[dia.month - 1]}"
    d.text((L - M - C.larg(d, data, fd), 62), data, font=fd, fill=C.SUAVE)
    desenhar(d, max(0, sobra // 2))
    C.rodape(d)
    arq = pasta / "cartoes" / "x_capa.jpg"
    orig = pasta / "cartoes" / "x_capa_original.jpg"
    if arq.exists() and not orig.exists():
        shutil.copy(arq, orig)
    im.save(arq, "JPEG", quality=92)
    return "cartoes/x_capa.jpg"


def cartao_do_jogo(dados, j):
    ordem = sorted(dados["jogos"][:len(dados["instagram"]["cartoes"]) - 2], key=lambda x: x["inicio"])
    nomes = [n for n in dados["instagram"]["cartoes"] if n.endswith("_jogo.jpg")]
    for k, x in enumerate(ordem):
        if x["id"] == j["id"] and k < len(nomes):
            return f"cartoes/{nomes[k]}"
    return None


def escrever_txt(pasta, posts):
    blocos = []
    for p in posts:
        img = f" · imagem {Path(p['imagem']).name}" if p.get("imagem") else " · só texto"
        blocos.append(f"[{p['horario']}{img}]\n{p['texto']}")
    (pasta / "x.txt").write_text("\n\n---\n\n".join(blocos))


def cmd_dia(dia_txt):
    pasta = SAIDA / dia_txt
    arq = pasta / "posts.json"
    dados = json.loads(arq.read_text())
    if "x_original" not in dados:
        dados["x_original"] = dados["x"]
    dia = datetime.strptime(dia_txt, "%Y-%m-%d").date()
    n_car = max(0, len(dados["instagram"]["cartoes"]) - 2)  # capa e "siga" não são jogos
    carrossel = dados["jogos"][:n_car or 7]
    jogos = carrossel  # só jogos do carrossel: têm cartão e entram no encerramento (21/11)
    # resumo: o número mais forte da maior liga do dia (sem o bônus de time grande, que só desempata posts)
    topo = max(faixa(j) for j in jogos)
    destaque = max([j for j in jogos if faixa(j) == topo],
                   key=lambda j: max(c.get("nota", 0) for c in j["curiosidades"]))
    base = datetime.combine(dia, datetime.min.time(), BRT)
    oito = base.replace(hour=8)
    posts = [dict(horario="08:00", texto=post_resumo(destaque, len(carrossel)), tipo="resumo", imagem=capa_x(pasta, dia, destaque, carrossel + ([] if destaque in carrossel else [destaque])))]
    # o jogo do resumo só volta no X se tiver um 2º número forte; jogo com número fraco não vira post
    resto = [j for j in jogos if (j["id"] != destaque["id"] and lider(j) >= NOTA_MIN)
             or (j["id"] == destaque["id"] and len(j["curiosidades"]) > 1
                 and sorted(c.get("nota", 0) for c in j["curiosidades"])[-2] >= NOTA_MIN)]
    for j, h in agenda(resto, dia, [oito], destaque["id"], {j["id"] for j in carrossel}):
        posts.append(dict(horario=h.strftime("%H:%M"), texto=post_jogo(j, 1 if j["id"] == destaque["id"] else 0),
                          tipo="jogo", jogo=j["id"],
                          imagem=cartao_do_jogo(dados, j)))
    for p in posts:
        regras_x.conferir(p["texto"])
    dados["x"] = posts
    if "legenda_original" not in dados["instagram"]:
        dados["instagram"]["legenda_original"] = dados["instagram"]["legenda"]
    dados["instagram"]["legenda"] = legenda_ig(carrossel, dia)
    (pasta / "instagram_legenda.txt").write_text(dados["instagram"]["legenda"])
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1))
    escrever_txt(pasta, posts)
    print((pasta / "x.txt").read_text())
    print("\n======== INSTAGRAM ========")
    print(dados["instagram"]["legenda"])


def cmd_encerramento(dia_txt):
    pasta = SAIDA / dia_txt
    enc = json.loads((pasta / "encerramento.json").read_text())
    dados = json.loads((pasta / "posts.json").read_text())
    jogos = {j["id"]: j for j in dados["jogos"]}
    jogados = [e for e in enc["jogos"] if e["placar"]]
    itens = [i for e in jogados for i in e["itens"] if i[0] != "info"]
    k = sum(1 for s, _ in itens if s == "manteve")
    caidas = [f for e in jogados for s, f in e["itens"] if s == "caiu"]
    mantidas = [f for e in jogados for s, f in e["itens"] if s == "manteve"]
    # mesma abertura do encerramento.py (a curiosidade de maior nota que caiu ou se manteve)
    abertura = (enc.get("texto", "").split("\n")[0].strip()
                or (caidas or mantidas or ["Os jogos de hoje acabaram"])[0].rstrip(".") + ".")
    if len(itens) == 1:
        meio = f"A curiosidade publicada hoje {'se manteve' if k else 'caiu'} depois do jogo."
    elif itens:
        meio = f"Das {len(itens)} curiosidades publicadas hoje, {k} {'se manteve' if k == 1 else 'se mantiveram'} depois dos jogos."
    else:
        meio = ""
    partes = [abertura] + ([meio] if meio else []) + ["Placares e o que mudou estão no quadro. Qual desses números te surpreendeu?"]
    txt = regras_x.conferir("\n\n".join(partes))
    print("[ENCERRAMENTO · X · post original com fechamento.jpg]")
    print(txt)
    # respostas com texto próprio, cada uma embaixo do post daquele jogo (quem segue vê a conversa)
    feitos = {}
    for p in dados["x"]:
        jid = p.get("jogo")
        if p.get("tipo") == "resumo" and not jid:  # resumo das 8h: acha o jogo pelo "Casa x Fora" do texto (22/11)
            jid = next((k for k, j in jogos.items() if f"{j['casa']} x {j['fora']}" in p.get("texto", "")), None)
        if jid and (p.get("tipo") == "jogo" or jid not in feitos):
            feitos[jid] = p
    for e in jogados:
        p = feitos.get(e["id"])
        if not p:
            continue
        j = jogos[e["id"]]
        gc, gf = e["placar"]
        principal = ([f for s, f in e["itens"] if s != "info"] or [f for s, f in e["itens"]])[:1]
        corpo = f"Terminou {j['casa']} {gc} x {gf} {j['fora']}."
        if principal:
            corpo += f" {principal[0].rstrip('.')}."
        print(f"\n[RESPOSTA ao post das {p['horario']} ({j['casa']} x {j['fora']})]")
        print(regras_x.conferir(corpo))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dia", "encerramento"])
    ap.add_argument("--data", default=datetime.now(BRT).strftime("%Y-%m-%d"))
    a = ap.parse_args()
    {"dia": cmd_dia, "encerramento": cmd_encerramento}[a.cmd](a.data)


if __name__ == "__main__":
    main()
