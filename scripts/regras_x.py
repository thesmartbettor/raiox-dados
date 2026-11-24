"""Checagem dos textos do X antes de publicar (resumo do ranking do X enviado pelo Gabriel em 7/11/2026).

Rejeita: travessão, "não é X, é Y", emoji no começo, hashtag, 2+ contas marcadas, pedido de RT/curtida/
comentário, gancho de clique, mais de 280 caracteres ou mais de 6 linhas com texto.
"""
import re
import unicodedata

LIMITE = 280
MAX_LINHAS = 6
GANCHOS = ["👇", "segue o fio", "leia mais", "abre aí", "abre ai", "clique", "veja na imagem", "rt se", "retuíte",
           "marca um amigo", "marque um amigo", "comente", "curta se", "deixa o like", "🧵", "🚨", "thread"]


def _emoji_inicio(t):
    c = t.lstrip()[:1]
    return bool(c) and (unicodedata.category(c) == "So" or ord(c) > 0x2000 and not c.isalnum())


def problemas(t):
    p = []
    low = t.lower()
    if len(t) > LIMITE:
        p.append(f"{len(t)} caracteres")
    if sum(1 for l in t.splitlines() if l.strip()) > MAX_LINHAS:
        p.append("mais de 6 linhas")
    if "—" in t or "–" in t:
        p.append("travessão")
    if re.search(r"\bnão é\b[^.\n]{1,60},\s*é\b", low):
        p.append("'não é X, é Y'")
    if _emoji_inicio(t):
        p.append("emoji no começo")
    if re.search(r"(^|\s)#\w", t):
        p.append("hashtag")
    if len(re.findall(r"(^|\s)@\w", t)) >= 2:
        p.append("2+ contas marcadas")
    p += [f"gancho '{g}'" for g in GANCHOS if g in low]
    return p


def conferir(t):
    p = problemas(t)
    if p:
        raise ValueError("post do X fora das regras (" + ", ".join(p) + "):\n" + t)
    return t
