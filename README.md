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
