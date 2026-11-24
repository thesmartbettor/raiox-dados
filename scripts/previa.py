"""Página HTML simples para revisar os posts do dia antes de publicar."""
import html


def gerar(saida, dia, x_posts, legenda, cartoes):
    esc = lambda s: html.escape(s).replace("\n", "<br>")  # noqa: E731
    xs = "".join(f'<div class="post"><div class="hora">{p["horario"]} · {"resumo" if p["tipo"] == "resumo" else "jogo"}'
                 f' · {len(p["texto"])}/280</div>{esc(p["texto"])}</div>' for p in x_posts)
    imgs = "".join(f'<img src="cartoes/{c.name}">' for c in cartoes)
    (saida / "previa.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>Raio-X do Jogo {dia}</title>
<style>body{{font-family:Inter,system-ui,sans-serif;background:#f3f4f6;margin:0;padding:16px;color:#111}}
h2{{margin:24px 0 8px}}.post{{background:#fff;border-radius:12px;padding:14px;margin:10px 0;max-width:560px;line-height:1.45}}
.hora{{font-size:12px;color:#6b7280;margin-bottom:6px}}.car{{display:flex;gap:10px;overflow-x:auto}}
.car img{{width:320px;border-radius:8px}}pre{{white-space:pre-wrap;background:#fff;padding:14px;border-radius:12px;max-width:560px}}</style>
<h1>Raio-X do Jogo · {dia.day}/{dia.month}/{dia.year}</h1><h2>X</h2>{xs}<h2>Instagram (8h)</h2><div class="car">{imgs}</div>
<pre>{html.escape(legenda)}</pre>""")
