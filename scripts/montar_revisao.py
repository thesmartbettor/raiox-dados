"""Monta a página de revisão dos posts simulados do @DataJogo."""
import html
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caminhos import SAIDA  # noqa: E402
DEST = SAIDA / "_revisao"  # página + imagens prontas para publicar como Artifact
DIAS = sys.argv[1:]  # ex.: python3 montar_revisao.py 2026-10-26
SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

if DEST.exists():
    shutil.rmtree(DEST)
(DEST / "img").mkdir(parents=True)

esc = lambda s: html.escape(s).replace("\n", "<br>")  # noqa: E731
abas, paineis = [], []
for i, d in enumerate(DIAS):
    p = json.loads((SAIDA / d / "posts.json").read_text())
    dt = date.fromisoformat(d)
    rot = f"{SEMANA[dt.weekday()]} {dt.day}/{dt.month}"
    imgs = []
    for nome in p["instagram"]["cartoes"]:
        alvo = f"img/{d}_{nome}"
        shutil.copy(SAIDA / d / "cartoes" / nome, DEST / alvo)
        imgs.append(alvo)
    posts = []
    for x in p["x"]:
        tipo = "Resumo da manhã" if x["tipo"] == "resumo" else "Antes do jogo"
        img = f'<img class="anexo" src="{imgs[0]}" alt="Capa anexada ao resumo" loading="lazy">' if x.get("imagem") else ""
        posts.append(f'''<article class="tweet"><header><span class="hora">{x["horario"]}</span><span class="tipo">{tipo}</span>
<span class="chars">{len(x["texto"])}/280</span></header><p>{esc(x["texto"])}</p>{img}</article>''')
    car = "".join(f'<img src="{s}" alt="Cartão {k + 1} do carrossel" loading="lazy">' for k, s in enumerate(imgs))
    abas.append(f'<button role="tab" id="aba-{d}" aria-selected="{str(i == 0).lower()}" data-dia="{d}">{rot}</button>')
    paineis.append(f'''<section class="painel" id="p-{d}" {"" if i == 0 else "hidden"}>
<div class="cols"><div class="col"><h2>X <small>{len(p["x"])} posts</small></h2>{"".join(posts)}</div>
<div class="col"><h2>Instagram <small>carrossel às 8h · {len(imgs)} cartões</small></h2><div class="carrossel">{car}</div>
<details><summary>Legenda do carrossel</summary><pre>{html.escape(p["instagram"]["legenda"])}</pre></details></div></div></section>''')

pagina = f'''<title>@DataJogo · posts do dia</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
/* Mesa de revisão: abas por dia, coluna do X à esquerda e carrossel do Instagram à direita */
:root {{ --bg:#eef2f6; --papel:#ffffff; --tinta:#0b1426; --suave:#5b6b82; --linha:#d7dee8; --verde:#14935a;
  --display:"Archivo", "Helvetica Neue", Arial, sans-serif; --texto:"IBM Plex Sans", system-ui, sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#0b1426; --papel:#121f38; --tinta:#eef2f6; --suave:#94a3b8; --linha:#22324f; --verde:#2bd576; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#0b1426; --papel:#121f38; --tinta:#eef2f6; --suave:#94a3b8; --linha:#22324f; --verde:#2bd576; color-scheme:dark }}
body {{ background:var(--bg); color:var(--tinta); font:15px/1.5 var(--texto); padding-block:28px 48px;
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }}
.topo {{ max-width:1160px; margin:0 auto 20px; display:grid; gap:6px }}
h1 {{ font:800 clamp(28px,4vw,40px)/1.1 var(--display); margin:0; letter-spacing:-.01em }}
h1 span {{ color:var(--verde) }}
.topo p {{ margin:0; color:var(--suave); max-width:70ch }}
[role=tablist] {{ max-width:1160px; margin:0 auto 18px; display:flex; gap:8px; flex-wrap:wrap }}
[role=tab] {{ font:700 14px var(--display); padding:9px 16px; border-radius:999px; border:1px solid var(--linha); background:var(--papel); color:var(--tinta); cursor:pointer }}
[role=tab][aria-selected=true] {{ background:var(--tinta); color:var(--bg); border-color:var(--tinta) }}
[role=tab]:focus-visible, summary:focus-visible {{ outline:3px solid var(--verde); outline-offset:2px }}
.painel {{ max-width:1160px; margin:0 auto }}
.cols {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.1fr); gap:28px; align-items:start }}
@media (max-width:860px) {{ .cols {{ grid-template-columns:minmax(0,1fr) }} }}
.col {{ display:grid; gap:12px; min-width:0 }}
h2 {{ font:800 20px var(--display); margin:0; display:flex; gap:10px; align-items:baseline; flex-wrap:wrap }}
h2 small {{ font:500 13px var(--texto); color:var(--suave) }}
.tweet {{ background:var(--papel); border:1px solid var(--linha); border-radius:14px; padding:14px 16px; display:grid; gap:8px }}
.tweet header {{ display:flex; gap:10px; align-items:center; font-size:13px; color:var(--suave) }}
.hora {{ font:700 15px var(--display); color:var(--verde); font-variant-numeric:tabular-nums }}
.chars {{ margin-left:auto; font-variant-numeric:tabular-nums }}
.tweet p {{ margin:0; overflow-wrap:anywhere }}
.anexo {{ width:180px; border-radius:10px; border:1px solid var(--linha) }}
.carrossel {{ display:flex; gap:12px; overflow-x:auto; scroll-snap-type:x mandatory; padding-bottom:8px }}
.carrossel img {{ flex:0 0 auto; width:min(360px, 80vw); max-width:100%; border-radius:10px; scroll-snap-align:start }}
details {{ background:var(--papel); border:1px solid var(--linha); border-radius:14px; padding:12px 16px }}
summary {{ cursor:pointer; font-weight:500 }}
pre {{ white-space:pre-wrap; font:14px/1.5 var(--texto); margin:10px 0 0; overflow-wrap:anywhere }}
</style>
<div class="topo"><h1><span>Raio-X</span> do Jogo · posts do dia</h1>
<p>Posts do dia, aguardando a sua aprovação. Nada foi publicado ainda.</p></div>
<div role="tablist" aria-label="Dia">{"".join(abas)}</div>
{"".join(paineis)}
<script>
const abas=[...document.querySelectorAll('[role=tab]')];
function abrir(d){{abas.forEach(a=>a.setAttribute('aria-selected',a.dataset.dia===d));
document.querySelectorAll('.painel').forEach(p=>p.hidden=p.id!=='p-'+d);}}
abas.forEach(a=>a.addEventListener('click',()=>abrir(a.dataset.dia)));
</script>
'''
(DEST / "datajogo_dia.html").write_text(pagina)
print(sorted(str(p.relative_to(DEST)) for p in (DEST / "img").glob("*")))
