"""Cartões do carrossel do Instagram (1080x1350, JPEG): capa, um cartão por jogo e encerramento."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

L, A = 1080, 1350
FUNDO = (11, 20, 38)
FUNDO2 = (18, 31, 56)
TEXTO = (241, 245, 249)
SUAVE = (148, 163, 184)
DESTAQUE = (43, 213, 118)
FONTES = Path(__file__).resolve().parent / "fontes"  # Inter Display (licença OFL, fontes/OFL.txt)
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
M = 72  # margem
ARROBA_INSTAGRAM = "@RaioXJogo"
ARROBA_X = "@RaioXJogo"
ARROBA = ARROBA_INSTAGRAM  # trocado em gerar() para a capa que vai no X
LEGENDA = {"vitorias_seguidas": "vitórias seguidas", "invicto": "jogos sem perder", "derrotas_seguidas": "derrotas seguidas",
           "sem_vencer": "jogos sem vencer", "sem_sofrer": "jogos sem sofrer gol", "sem_marcar": "jogos sem marcar",
           "marcou_todos": "jogos seguidos marcando", "vitorias_casa": "vitórias seguidas em casa",
           "vitorias_fora": "vitórias seguidas fora", "invicto_casa": "sem perder em casa", "invicto_fora": "sem perder fora",
           "sem_vencer_casa": "sem vencer em casa", "sem_vencer_fora": "sem vencer fora", "h2h_geral": "vitórias · empates · vitórias",
           "tabu_visitante": "visitas sem vencer", "tabu_mandante": "vitórias em casa no duelo", "h2h_vitorias": "vitórias seguidas no duelo",
           "h2h_invicto": "sem perder no duelo", "h2h_gols_muitos": "gols por jogo no duelo", "h2h_gols_poucos": "gols por jogo no duelo",
           "ultimo_elastico": "no último duelo", "jogador_seq_gols": "jogos seguidos com gol", "artilheiro": "gols na temporada"}


# Temas (pedido do Gabriel em 6/11): cores + layout do cartão de cada jogo. Um tema por dia, em rodízio.
TEMAS = {
    "noite":   dict(FUNDO=(11, 20, 38), FUNDO2=(18, 31, 56), TEXTO=(241, 245, 249), SUAVE=(148, 163, 184), DESTAQUE=(43, 213, 118), layout="lista"),
    "papel":   dict(FUNDO=(247, 244, 237), FUNDO2=(228, 221, 207), TEXTO=(22, 26, 33), SUAVE=(98, 104, 114), DESTAQUE=(222, 88, 10), layout="blocos"),
    "placar":  dict(FUNDO=(18, 18, 18), FUNDO2=(40, 40, 40), TEXTO=(250, 250, 250), SUAVE=(165, 165, 165), DESTAQUE=(255, 196, 0), layout="placar"),
    "gramado": dict(FUNDO=(7, 56, 37), FUNDO2=(14, 80, 53), TEXTO=(240, 253, 244), SUAVE=(170, 210, 188), DESTAQUE=(190, 242, 100), layout="destaque"),
}
ORDEM_TEMAS = ["noite", "papel", "placar", "gramado"]
LAYOUT = "lista"


def aplicar_tema(nome):
    global FUNDO, FUNDO2, TEXTO, SUAVE, DESTAQUE, LAYOUT
    t = TEMAS[nome]
    FUNDO, FUNDO2, TEXTO, SUAVE, DESTAQUE, LAYOUT = t["FUNDO"], t["FUNDO2"], t["TEXTO"], t["SUAVE"], t["DESTAQUE"], t["layout"]


def tema_do_dia(dia):
    return ORDEM_TEMAS[dia.toordinal() % len(ORDEM_TEMAS)]


def fonte(peso, tam):
    return ImageFont.truetype(str(FONTES / f"InterDisplay-{peso}.otf"), tam)


def larg(d, txt, f):
    return d.textlength(txt, font=f)


def quebrar(d, txt, f, largura):
    linhas, atual = [], ""
    for p in txt.split():
        teste = (atual + " " + p).strip()
        if larg(d, teste, f) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def ajustar(d, txt, peso, tam, largura, minimo=30):
    while tam > minimo and larg(d, txt, fonte(peso, tam)) > largura:
        tam -= 2
    return fonte(peso, tam)


def base():
    im = Image.new("RGB", (L, A), FUNDO)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, L, 10], fill=DESTAQUE)
    return im, d


def marca(d, y=56):
    f = fonte("Black", 40)
    d.text((M, y), "Raio-X ", font=f, fill=DESTAQUE)
    d.text((M + larg(d, "Raio-X ", f), y), "do Jogo", font=f, fill=TEXTO)


def rodape(d):
    d.line([M, A - 110, L - M, A - 110], fill=FUNDO2, width=3)
    d.text((M, A - 82), ARROBA, font=fonte("Bold", 30), fill=TEXTO)
    f = fonte("Regular", 24)
    t = "Resultados dos campeonatos nacionais"
    d.text((L - M - larg(d, t, f), A - 78), t, font=f, fill=SUAVE)


def capa(jogos, dia, destino):
    im, d = base()
    marca(d)
    d.text((M, 200), "CURIOSIDADES", font=fonte("Black", 104), fill=TEXTO)
    d.text((M, 310), "DO DIA", font=fonte("Black", 104), fill=DESTAQUE)
    d.text((M, 440), f"{DIAS[dia.weekday()]}, {dia.day} de {MESES[dia.month - 1]}", font=fonte("Medium", 40), fill=SUAVE)
    y = 540
    passo = min(96, (A - 200 - y) // max(len(jogos), 1))
    for j in jogos:
        d.rounded_rectangle([M, y, L - M, y + passo - 14], radius=18, fill=FUNDO2)
        y += (passo - 96) // 2
        d.text((M + 28, y + 22), j["hora"], font=fonte("Bold", 32), fill=DESTAQUE)
        f = ajustar(d, f"{j['casa']} x {j['fora']}", "SemiBold", 34, 560)
        d.text((M + 150, y + 22), f"{j['casa']} x {j['fora']}", font=f, fill=TEXTO)
        fl = fonte("Regular", 24)
        d.text((L - M - 28 - larg(d, j["liga"], fl), y + 28), j["liga"], font=fl, fill=SUAVE)
        y += passo - (passo - 96) // 2
    d.text((M, A - 172), "Arraste para ver os números →", font=fonte("Medium", 30), fill=SUAVE)
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def cartao_jogo(j, destino):
    {"lista": cartao_lista, "blocos": cartao_blocos, "placar": cartao_placar, "destaque": cartao_destaque}[LAYOUT](j, destino)


def texto_ajustado(d, txt, peso, tam, largura, max_linhas, minimo=24):
    f = fonte(peso, tam)
    linhas = quebrar(d, txt, f, largura)
    while len(linhas) > max_linhas and tam > minimo:
        tam -= 2
        f = fonte(peso, tam)
        linhas = quebrar(d, txt, f, largura)
    return f, linhas


def cartao_blocos(j, destino):
    """Fundo claro; times no topo e cada curiosidade num bloco com o número em destaque."""
    im, d = base()
    marca(d)
    fl = fonte("Medium", 30)
    topo = f"{j['liga']} · {j['hora']}"
    d.text((L - M - larg(d, topo, fl), 64), topo, font=fl, fill=SUAVE)
    ft = ajustar(d, f"{j['casa']} x {j['fora']}", "Black", 68, L - 2 * M, minimo=40)
    if larg(d, f"{j['casa']} x {j['fora']}", ft) > L - 2 * M:
        d.text((M, 160), j["casa"], font=ft, fill=TEXTO)
    linha = f"{j['casa']} x {j['fora']}"
    if larg(d, linha, ft) <= L - 2 * M:
        x = M
        d.text((x, 160), j["casa"], font=ft, fill=TEXTO)
        x += larg(d, j["casa"] + " ", ft)
        d.text((x, 160), "x", font=ft, fill=DESTAQUE)
        x += larg(d, "x ", ft)
        d.text((x, 160), j["fora"], font=ft, fill=TEXTO)
        y = 160 + ft.size + 60
    else:
        y = 160 + ft.size + 10
        d.text((M, y), "x " + j["fora"], font=ft, fill=TEXTO)
        y += ft.size + 60
    n = max(len(j["curiosidades"]), 1)
    alto = (A - 150 - y - (n - 1) * 24) // n
    for c in j["curiosidades"]:
        d.rounded_rectangle([M, y, L - M, y + alto], radius=28, fill=FUNDO2)
        fn = ajustar(d, c["numero"], "Black", 96, 230, minimo=50)
        d.rounded_rectangle([M + 28, y + 28, M + 28 + 250, y + alto - 28], radius=20, fill=DESTAQUE)
        cx = M + 28 + 125
        d.text((cx - larg(d, c["numero"], fn) / 2, y + alto / 2 - fn.size * 0.62), c["numero"], font=fn, fill=FUNDO)
        x0 = M + 310
        ftx, linhas = texto_ajustado(d, c["texto"], "Medium", 34, L - M - 28 - x0, max(1, int((alto - 50) / 44)))
        h = len(linhas) * int(ftx.size * 1.3)
        for i, ln in enumerate(linhas):
            d.text((x0, y + (alto - h) / 2 + i * int(ftx.size * 1.3)), ln, font=ftx, fill=TEXTO)
        y += alto + 24
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def cartao_placar(j, destino):
    """Estilo placar: times lado a lado no topo, curiosidades centralizadas com o número grande."""
    im, d = base()
    marca(d)
    fl = fonte("Medium", 30)
    topo = f"{j['liga']} · {j['hora']}"
    d.text((L - M - larg(d, topo, fl), 64), topo, font=fl, fill=SUAVE)
    d.rounded_rectangle([M, 140, L - M, 330], radius=24, fill=FUNDO2)
    meia = (L - 2 * M - 120) / 2
    for nome, x0 in ((j["casa"], M), (j["fora"], L - M - meia)):
        f, linhas = texto_ajustado(d, nome, "Black", 52, meia - 30, 2, minimo=30)
        h = len(linhas) * int(f.size * 1.15)
        for i, ln in enumerate(linhas):
            d.text((x0 + meia / 2 - larg(d, ln, f) / 2, 235 - h / 2 + i * int(f.size * 1.15)), ln, font=f, fill=TEXTO)
    fx = fonte("Black", 56)
    d.text((L / 2 - larg(d, "x", fx) / 2, 235 - 36), "x", font=fx, fill=DESTAQUE)
    y = 380
    n = max(len(j["curiosidades"]), 1)
    alto = (A - 150 - y) // n
    for k, c in enumerate(j["curiosidades"]):
        fn = ajustar(d, c["numero"], "Black", 120, L - 2 * M, minimo=60)
        d.text((L / 2 - larg(d, c["numero"], fn) / 2, y), c["numero"], font=fn, fill=DESTAQUE)
        ftx, linhas = texto_ajustado(d, c["texto"], "Regular", 34, L - 2 * M - 40, max(1, int((alto - fn.size - 50) / 44)))
        yy = y + fn.size + 18
        for i, ln in enumerate(linhas):
            d.text((L / 2 - larg(d, ln, ftx) / 2, yy + i * int(ftx.size * 1.3)), ln, font=ftx, fill=TEXTO)
        y += alto
        if k < n - 1:
            d.line([L / 2 - 60, y - 22, L / 2 + 60, y - 22], fill=FUNDO2, width=4)
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def cartao_destaque(j, destino):
    """A curiosidade mais forte ocupa o centro com um número enorme; as outras vão numa faixa embaixo."""
    im, d = base()
    marca(d)
    fl = fonte("Medium", 30)
    topo = f"{j['liga']} · {j['hora']}"
    d.text((L - M - larg(d, topo, fl), 64), topo, font=fl, fill=SUAVE)
    ft = ajustar(d, f"{j['casa']} x {j['fora']}", "Bold", 48, L - 2 * M, minimo=30)
    d.text((M, 150), f"{j['casa']} x {j['fora']}", font=ft, fill=TEXTO)
    cs = sorted(j["curiosidades"], key=lambda c: -c["nota"])
    top, resto = cs[0], cs[1:]
    fn = ajustar(d, top["numero"], "Black", 300, L - 2 * M, minimo=120)
    d.text((M - 6, 250), top["numero"], font=fn, fill=DESTAQUE)
    y = 250 + int(fn.size * 1.05)
    fleg = fonte("Bold", 34)
    d.text((M, y), LEGENDA.get(top["tipo"], "").upper(), font=fleg, fill=SUAVE)
    y += 60
    limite = A - 150 - (len(resto) * 170)
    ftx, linhas = texto_ajustado(d, top["texto"], "SemiBold", 44, L - 2 * M, max(1, int((limite - y) / 58)))
    for i, ln in enumerate(linhas):
        d.text((M, y + i * int(ftx.size * 1.3)), ln, font=ftx, fill=TEXTO)
    y = A - 140 - len(resto) * 170
    for c in resto:
        d.rounded_rectangle([M, y, L - M, y + 150], radius=22, fill=FUNDO2)
        fnn = ajustar(d, c["numero"], "Black", 64, 170, minimo=36)
        d.text((M + 28, y + 75 - fnn.size * 0.62), c["numero"], font=fnn, fill=DESTAQUE)
        x0 = M + 220
        f2, l2 = texto_ajustado(d, c["texto"], "Regular", 30, L - M - 28 - x0, 3, minimo=22)
        h = len(l2) * int(f2.size * 1.3)
        for i, ln in enumerate(l2):
            d.text((x0, y + 75 - h / 2 + i * int(f2.size * 1.3)), ln, font=f2, fill=TEXTO)
        y += 170
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def cartao_lista(j, destino):
    im, d = base()
    marca(d)
    fl = fonte("Medium", 30)
    topo = f"{j['liga']} · {j['hora']}"
    d.text((L - M - larg(d, topo, fl), 64), topo, font=fl, fill=SUAVE)
    ft = ajustar(d, max(j["casa"], j["fora"], key=len), "Black", 84, L - 2 * M)
    d.text((M, 150), j["casa"], font=ft, fill=TEXTO)
    d.text((M, 150 + ft.size + 8), "x", font=fonte("Bold", 44), fill=DESTAQUE)
    d.text((M, 150 + ft.size + 70), j["fora"], font=ft, fill=TEXTO)
    y = 150 + 2 * ft.size + 120
    d.line([M, y, L - M, y], fill=FUNDO2, width=3)
    y += 40
    espaco = (A - 140 - y) // max(len(j["curiosidades"]), 1)
    for c in j["curiosidades"]:
        fn = ajustar(d, c["numero"], "Black", 120, 300, minimo=60)
        d.text((M, y - 10), c["numero"], font=fn, fill=DESTAQUE)
        fleg = fonte("Medium", 24)
        for i, ln in enumerate(quebrar(d, LEGENDA.get(c["tipo"], ""), fleg, 300)):
            d.text((M, y + fn.size + 14 + i * 30), ln, font=fleg, fill=SUAVE)
        ftx = fonte("Regular", 34)
        x0 = M + 340
        linhas = quebrar(d, c["texto"], ftx, L - M - x0)
        while len(linhas) * 44 > espaco - 20 and ftx.size > 26:
            ftx = fonte("Regular", ftx.size - 2)
            linhas = quebrar(d, c["texto"], ftx, L - M - x0)
        for i, ln in enumerate(linhas):
            d.text((x0, y + i * int(ftx.size * 1.3)), ln, font=ftx, fill=TEXTO)
        y += espaco
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def encerramento(destino):
    im, d = base()
    marca(d)
    d.text((M, 420), "Siga", font=fonte("Black", 120), fill=TEXTO)
    d.text((M, 550), ARROBA, font=ajustar(d, ARROBA, "Black", 120, L - 2 * M), fill=DESTAQUE)
    for i, t in enumerate(["Curiosidades dos jogos de futebol", "todos os dias, logo cedo."]):
        d.text((M, 740 + i * 58), t, font=fonte("Medium", 44), fill=SUAVE)
    rodape(d)
    im.save(destino, "JPEG", quality=92)


def gerar(jogos, dia, pasta, tema=None):
    aplicar_tema(tema or tema_do_dia(dia))
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in pasta.glob("*.jpg"):
        velho.unlink()
    global ARROBA
    ARROBA = ARROBA_X
    capa(jogos, dia, pasta / "x_capa.jpg")  # capa do resumo no X, com o @ do X
    ARROBA = ARROBA_INSTAGRAM
    arquivos = [pasta / "01_capa.jpg"]
    capa(jogos, dia, arquivos[0])
    for i, j in enumerate(jogos, start=2):
        arq = pasta / f"{i:02d}_jogo.jpg"
        cartao_jogo(j, arq)
        arquivos.append(arq)
    fim = pasta / f"{len(jogos) + 2:02d}_siga.jpg"
    encerramento(fim)
    arquivos.append(fim)
    return arquivos
