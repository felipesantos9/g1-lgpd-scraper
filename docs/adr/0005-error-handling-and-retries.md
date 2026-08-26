# 0005 — Tratamento de erros e retries

Status: aceito

## Contexto

O código legado não tratava nenhuma falha: `requests.get(url)` sem `try/except`, sem checagem de `status_code`, e `card.find(...).get_text()` que lança `AttributeError` e aborta a execução inteira se um seletor não casar (ver `docs/diagnosis.md`). O enunciado exige explicitamente que falhas de conexão, respostas HTTP inválidas e campos ausentes não interrompam a execução.

## Decisão

- **Falhas de rede transitórias** (timeout, carregamento incompleto): retry com backoff exponencial via `tenacity`, até `config.max_retries` tentativas, em `fetch/browser_client.py` (`BrowserSession._navigate`). Se esgotar as tentativas, a coleta é interrompida com `BrowserFetchError`, capturada em `pagination.py`, que devolve lista vazia em vez de propagar a exceção.
- **Falha de campo individual ou card malformado**: tratada dentro do parser (`parse/result_parser.py`), isolada por card com `try/except` — ver ADR 0002 e a spec, seção 5. Nunca propaga para fora da função de parsing.
- **Falha total da coleta headless** (browser ausente, crash, todas as tentativas de retry esgotadas): capturada em `pagination.py`, logada como `ERROR`, e `collect_raw_cards` devolve lista vazia — o restante do pipeline (`pipeline.py`) continua e grava um CSV/JSON vazio em vez de abortar com traceback.
- **Zero resultados legítimos vs. falha são distinguidos na origem**: o G1 renderiza uma estrutura própria para busca sem resultados (`.search-not-found__root`, confirmado empiricamente — ver `docs/diagnosis.md`), diferente do container de resultados populado. `BrowserSession._navigate` espera por `.results__list li` **ou** `.search-not-found__root` (o que aparecer primeiro); se for a segunda, `load_up_to_page` devolve `genuinely_empty=True` e `pagination.py` loga **INFO** ("busca não retornou nenhum resultado... não é falha"), não `ERROR`. Se nenhum dos dois aparecer depois de esgotar os retries, isso ainda vira `BrowserFetchError`/`ERROR` — é o sinal real de problema (browser caiu, ou a estrutura da página mudou de um jeito que nem resultados nem a mensagem de erro são reconhecidos, ver ADR 0002).
- **Regra de parada geral**: nenhuma falha de coleta interrompe o processo com traceback — mesmo uma falha total (sinal de problema sistêmico, ex.: site inteiro fora do ar) resulta em um CSV/JSON vazio, não num crash. O processo sempre termina com código de saída zero. O que passou a ser possível distinguir é a **causa** de um resultado vazio, pelo nível de log (`INFO` = zero legítimo, `ERROR` = falha) — o que ainda não existe é uma forma estruturada de checar isso (ex.: campo em `RunSummary`, código de saída diferente): hoje só dá pra saber lendo o log, não só o dataset. Fica registrado como possível extensão futura.

## Alternativas consideradas

- **Deixar exceções propagarem e abortar a run inteira em qualquer erro**: rejeitado — era o comportamento do código legado e é exatamente o requisito que o enunciado pede para corrigir.
- **Engolir todas as exceções silenciosamente (bare `except: pass`)**: rejeitado — esconde problemas reais e dificulta diagnóstico; toda falha tratada é logada com contexto suficiente para investigação.

## Consequências

- Positivas: uma falha pontual (um card, uma página, uma requisição) nunca compromete o resultado das demais; comportamento de retry lida com instabilidade transitória de rede sem intervenção manual.
- Negativas / trade-offs: retries com backoff aumentam o tempo total de execução em cenários de falha parcial; é necessário calibrar `max_retries` para não mascarar por muito tempo uma falha sistêmica real.
