# Raio-X do Jogo: dados de futebol

Atualizado todo dia por volta das 6h30 (horário de Brasília). Só estatística de futebol (resultados, agenda e jogadores).

## Para ler todo dia

| Arquivo | Link fixo | O que é |
|---|---|---|
| `hoje.json` | https://raw.githubusercontent.com/thesmartbettor/raiox-dados/main/hoje.json | Jogos de hoje com os últimos 5 jogos de cada time e os últimos 5 confrontos diretos; resultados de ontem |
| `hoje.md` | https://raw.githubusercontent.com/thesmartbettor/raiox-dados/main/hoje.md | O mesmo em tabela, para leitura rápida |
| `manifesto.json` | https://raw.githubusercontent.com/thesmartbettor/raiox-dados/main/manifesto.json | Data/hora da geração, linhas de cada tabela, sha1 de cada arquivo |

Confira `data_brasilia` em `hoje.json`: se não for a data de hoje, a atualização do dia ainda não saiu.

## hoje.json

- `jogos_hoje[]`: `hora_brasilia`, `competicao`, `mandante`, `visitante`, `status`, `rodada`, `match_id`, `data_hora_utc`,
  `ultimos_jogos_mandante[]` / `ultimos_jogos_visitante[]` (do mais recente ao mais antigo: `data`, `competicao`, `local` casa/fora, `adversario`, `placar` mandante x visitante, `resultado` V/E/D, todas as 20 ligas da agenda),
  `confronto_direto[]` (últimos 5: `data`, `liga`, `mandante`, `visitante`, `placar`; histórico do football-data desde 1993 + jogos recentes).
- `resultados_ontem[]`: `hora_brasilia`, `competicao`, `mandante`, `gols_mandante`, `gols_visitante`, `visitante`, `placar`, `match_id`.
- `observacoes[]`: avisos do dia (ex.: agenda sem jogos hoje).

## Tabelas completas (pasta `dados/`, CSV UTF-8)

Datas `AAAA-MM-DD`; data e hora UTC `AAAA-MM-DDTHH:MM:SSZ`; Brasília = UTC-3. Link de cada uma: `https://raw.githubusercontent.com/thesmartbettor/raiox-dados/main/dados/<tabela>.csv`.

**partidas**: resultados dos campeonatos nacionais (football-data.co.uk), ~31 ligas, desde 1993.
`pais`, `liga`, `temporada` (2025/26 ou 2026), `data`, `time_casa`, `time_fora`, `gols_casa`, `gols_fora` (inteiros; vazio sem placar).

**agenda**: jogos marcados e realizados das 20 ligas da TheStatsAPI (Premier League desde 2014/15, Championship desde 2015/16, demais desde ~2020).
`match_id`, `competicao_id`, `competicao`, `temporada_id`, `rodada`, `status` (scheduled, finished, postponed, cancelled), `data_hora_utc`, `time_casa`, `time_fora`, `time_casa_id`, `time_fora_id`, `gols_casa`, `gols_fora`, `xg_disponivel` (1/0).

**jogador_partida**: minutos e gols por jogador e jogo (Understat), 5 grandes ligas + RFPL, desde 2024/25.
`understat_id` (jogo), `understat_id_jogador`, `jogador`, `time`, `minutos`, `gols`, `liga` (EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL), `temporada`, `data_hora` (como o Understat informa).
Atenção: o Understat está fora do ar desde 03/11/2026; o último jogo é de 31/10/2026.

**apelidos_times**: liga os nomes da agenda aos do histórico.
`competicao`, `nome_agenda` (= agenda.time_casa/time_fora), `pais`, `liga`, `nome_historico` (= partidas.time_casa/time_fora), `nota` (confiança 0 a 1), `manual` (1 = corrigido à mão).

**atualizacao**: uma linha por dia: `gerado_em`, `inicio`, `fim` (da atualização das bases), `scripts_ok`, `scripts_total`, `observacoes`.

## Histórico

Cada dia é um commit. Para ver um dia antigo, abra o histórico de commits do arquivo no GitHub.

## Como rodar

Os scripts que geram o conteúdo do Raio-X do Jogo ficam em `scripts/` e leem os CSV de `dados/` deste repositório. Eles são atualizados no mesmo commit diário dos dados.

```
git clone https://github.com/thesmartbettor/raiox-dados && cd raiox-dados
pip install -r requirements.txt        # Python 3.11+
```

**Conteúdo da manhã** de um dia (rodar depois da atualização das 6h30):

```
python3 scripts/gerar_posts.py --data AAAA-MM-DD
```

Grava em `saida/AAAA-MM-DD/`: `posts.json` (tudo: jogos, curiosidades checadas, posts do X, legenda e cartões), `x.txt` (posts do X com horário), `instagram_legenda.txt`, `cartoes/*.jpg` (carrossel 1080x1350 e `x_capa.jpg`) e `previa.html`. Opções: `--sem-cartoes`, `--max-jogos 7`, `--max-posts 5`. Não precisa de nenhuma chave.

Em seguida, **sempre depois do `gerar_posts.py`**, rode o motor do X:

```
python3 scripts/motor_x.py dia --data AAAA-MM-DD
```

Ele reescreve a saída da manhã para o formato atual do X (algoritmo de 13/11/2026): resumo das 08:00 com a capa "número do dia" + lista dos jogos (`cartoes/x_capa.jpg`; a capa antiga fica em `x_capa_original.jpg`), no máximo 4 posts de jogo (só jogos do carrossel, um por horário de início, 2 h entre posts, nunca antes das 9h30, cada um com o cartão do jogo e uma pergunta de torcedor) e a legenda curta do Instagram (um número por jogo). Atualiza `posts.json` (guarda as versões anteriores em `x_original` e `instagram.legenda_original`), `x.txt` e `instagram_legenda.txt`. Não precisa de nenhuma chave. Sequência da manhã: `gerar_posts.py` → `motor_x.py dia`.

**Encerramento** do dia (depois dos jogos; confere cada curiosidade publicada com o placar final):

```
python3 scripts/encerramento.py --data AAAA-MM-DD --horario   # imprime o horário (Brasília) para rodar
python3 scripts/encerramento.py --data AAAA-MM-DD             # gera o texto e o cartão
python3 scripts/encerramento.py --data AAAA-MM-DD --publicar  # gera e posta no X (exige o dia aprovado)
```

Lê `saida/AAAA-MM-DD/posts.json` da manhã e grava `saida/AAAA-MM-DD/cartoes/fechamento.jpg` e o texto do post. Usa a TheStatsAPI para os placares.

Depois do `encerramento.py`, gere o texto final do X e a versão do Instagram:

```
python3 scripts/motor_x.py encerramento --data AAAA-MM-DD            # post do X com fechamento.jpg + uma resposta por post do dia (resultado do jogo)
python3 scripts/encerramento_instagram.py --data AAAA-MM-DD          # legenda do "Como terminou" para o Instagram (post único com fechamento.jpg)
python3 scripts/encerramento_instagram.py --data AAAA-MM-DD --publicar  # publica no Instagram (exige o dia aprovado)
```

Os dois leem `saida/AAAA-MM-DD/encerramento.json` e `posts.json`. Sequência da noite: `encerramento.py` → `motor_x.py encerramento` → `encerramento_instagram.py`.

**Publicação e aprovação** (opcionais):

```
python3 scripts/telegram_aprovacao.py enviar --data AAAA-MM-DD        # prévia e botões no Telegram
python3 scripts/telegram_aprovacao.py esperar --data AAAA-MM-DD --ate 10:50
python3 scripts/publicar.py aprovar --data AAAA-MM-DD                 # cria saida/AAAA-MM-DD/aprovado.json
python3 scripts/publicar.py x --data AAAA-MM-DD --pendentes           # posta no X os posts cujo horário chegou
python3 scripts/publicar.py instagram --data AAAA-MM-DD               # carrossel do Instagram
```

Nada é publicado sem `aprovado.json`. O que já saiu fica em `saida/AAAA-MM-DD/publicados.json`, para não publicar duas vezes.

**Variáveis de ambiente** (só os nomes; nenhuma chave fica no repositório):

| Variável | Usada por |
|---|---|
| `RAIOX_BASE` | opcional: pasta com `dados/` (padrão: raiz do repositório) |
| `RAIOX_SAIDA` | opcional: onde gravar a saída (padrão: `saida/` na raiz) |
| `THESTATSAPI_KEY` | `encerramento.py` |
| `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` | `publicar.py x`, `encerramento.py --publicar` |
| `IG_ACCESS_TOKEN`, `IMGBB_API_KEY` | `publicar.py instagram`, `encerramento_instagram.py --publicar` (renovar o token: `publicar.py renovar-ig`) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | `telegram_aprovacao.py` |
| `RAIOX_REVISAO_URL` | opcional: link da página de revisão na mensagem do Telegram |

Arquivos em `scripts/`: `gerar_posts.py` (principal), `curiosidades.py` (sequências, confronto direto, jogadores), `checagem.py` (recalcula cada número por outro caminho), `nomes.py` (liga os nomes da agenda aos do histórico, grava `dados/apelidos_times.csv`), `regras_x.py` (limites de texto do X), `cartoes.py` (imagens), `previa.py`, `encerramento.py`, `motor_x.py` (formato do X e legenda curta, manhã e encerramento), `encerramento_instagram.py` ("Como terminou" no Instagram), `publicar.py`, `telegram_aprovacao.py`, `montar_revisao.py`, `caminhos.py` e `fontes/` (Inter Display, licença OFL).
