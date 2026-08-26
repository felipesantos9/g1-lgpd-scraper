# Spec 0001 — Núcleo do scraper G1/LGPD

Esta spec define o contrato que o código em `src/g1_lgpd_scraper/` deve implementar. Decisões arquiteturais que motivam este contrato estão em `docs/adr/0001-rendering-strategy.md` e `docs/adr/0002-selector-strategy-and-versioning.md`.

## 1. Entrada

Parâmetros de configuração (via `config.py` / argumentos de CLI):

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `query` | str | `"lgpd"` | Termo de busca |
| `start_page` | int | `1` | Primeira página a coletar (1-indexed, espelha a UI) |
| `max_pages` | int | `5` | Número máximo de páginas a tentar coletar |
| `output_dir` | Path | `data/processed` | Diretório de saída dos arquivos gerados |
| `request_delay_seconds` | float | `1.0` | Atraso entre requisições (rate limiting, ADR 0011) |
| `request_timeout_seconds` | float | `30.0` | Timeout de navegação do browser headless (goto + espera do primeiro lote de resultados) |
| `max_retries` | int | `3` | Tentativas com backoff exponencial em falhas transitórias de navegação (`BrowserSession._navigate`) |

## 2. Schema do registro coletado

Cada resultado de busca coletado é um registro com os seguintes campos:

| Campo | Tipo | Obrigatório | Observações |
|---|---|---|---|
| `title` | str | sim | Texto do título, espaços normalizados |
| `url` | str | sim | URL absoluta e canônica da matéria — **extraída do parâmetro `u` do link de tracking** `measures.globo.com/v1/click?...&u=<url-encoded>`, nunca o `href` literal do link de tracking |
| `summary` | str \| None | não | Resumo/subtítulo (`p.widget--info__description`); pode conter marcação `<em>` destacando o termo buscado, removida na extração de texto |
| `published_at_raw` | str \| None | não | Texto como aparece na página: relativo para resultados recentes ("há 45 minutos", "há 2 dias") ou absoluto `dd/mm/aaaa HH:MM` para resultados mais antigos (confirmado na coleta real, `docs/diagnosis.md` Evidência 3) |
| `published_at_iso` | str \| None | não | Para texto relativo: estimativa calculada a partir de `collected_at` menos o intervalo interpretado (aproximação). Para texto absoluto: valor exato convertido para ISO 8601. `None` se o texto não casar com nenhum dos dois formatos |
| `page_number` | int | sim | Página de busca (1-indexed) de onde o registro veio |
| `collected_at` | str | sim | Timestamp ISO 8601 **com timezone** (`datetime.now(timezone.utc)`), momento da coleta |
| `run_id` | str | sim | Identificador único da execução (para rastreabilidade — ver ADR 0008) |
| `dedup_key` | str | sim | Ver seção 4 |

Campos ausentes (quando o site não fornece o dado) são gravados como `None`/vazio — **nunca** interrompem a coleta do registro inteiro (ver seção 5).

## 3. Paginação

**Confirmado com Playwright real (ver `docs/diagnosis.md`, Evidência 3): `?page=N` não tem efeito — devolve sempre os mesmos 10 primeiros resultados.** A paginação real é um botão client-side `.pagination__load-more` ("Veja mais") que faz *append* de +10 itens na mesma `ul.results__list`, sem navegação nem mudança de URL.

Contrato do módulo `pagination.py`: "página N" = N-1 cliques sucessivos no botão de carregar mais, dentro de uma única sessão de página do Playwright (`fetch/browser_client.py`), lendo incrementalmente os itens acumulados a cada N.

Coleta para quando: (a) `page_number > max_pages`, ou (b) uma tentativa de "carregar mais" não aumenta a contagem de itens (fim real da busca — o botão desaparece ou fica inerte), o que ocorrer primeiro. Isso é logado com o motivo exato da parada.

## 4. Deduplicação

- `dedup_key = sha256(canonical_url)`, onde `canonical_url` remove parâmetros de tracking/query string da URL da matéria (mantendo apenas scheme+host+path).
- Dedup ocorre em duas camadas:
  1. Dentro da mesma execução (evita duplicar um resultado que aparece em duas páginas por causa de reordenação/atraso de indexação).
  2. Entre execuções: `dedup.py` pode carregar as `dedup_key` já vistas em execuções anteriores (a partir de `data/processed/latest.json`) e marcar novos registros repetidos, sem descartá-los silenciosamente — eles são gravados com uma flag `is_duplicate_of_previous_run` para rastreabilidade, não simplesmente omitidos.

## 5. Tratamento de erros — regras de escopo de falha

| Nível de falha | Exemplo | Ação |
|---|---|---|
| Campo individual ausente | `summary` não encontrado no card | Grava `None` no campo, loga em nível `WARNING` com a URL do card, **continua** |
| Card malformado (não dá para nem extrair `url`) | seletor de link não casa | Pula o card, loga em nível `WARNING` com o índice do card na página, **continua** com os próximos cards |
| Falha de navegação transitória (timeout, carregamento incompleto) | `playwright.sync_api.TimeoutError` em `page.goto`/`wait_for_selector` | Retry com backoff exponencial até `max_retries` em `BrowserSession._navigate` (ADR 0005); se esgotar, levanta `BrowserFetchError` |
| Falha total da coleta headless (browser ausente, crash, retries esgotados) | `BrowserFetchError` | Capturada em `pagination.py`, loga `ERROR`, `collect_raw_cards` devolve lista vazia — **não propaga exceção** |
| Busca genuinamente sem resultados | `.search-not-found__root` presente (docs/diagnosis.md, Evidência 4) | Não é erro — `load_up_to_page` devolve `genuinely_empty=True`, `pagination.py` loga `INFO` e devolve lista vazia, **sem** passar por `BrowserFetchError` |
| Clique em "Veja mais" não traz itens novos | botão desaparece ou fica inerte | Não é erro — é o sinal de fim real dos resultados; para a coleta e retorna o que já foi acumulado |

Regra geral: **nenhuma falha localizada (registro, card ou toda a coleta) deve abortar o processo com traceback**. Mesmo uma falha total da coleta headless resulta em `pipeline.py` gravando um CSV/JSON vazio, não num crash — o processo sempre termina com código de saída zero. O nível de log (`INFO` vs `ERROR`) já distingue "zero resultados legítimos" de "falha" (ADR 0005); o que ainda não existe é uma forma estruturada de checar isso sem ler o log (ex.: campo em `RunSummary`).

## 6. Saída

- `data/processed/g1_lgpd_<query>_<YYYYMMDD_HHMMSS>.csv` e `.json` — snapshot da execução.
- `data/processed/latest.csv` e `latest.json` — sempre sobrescritos com o resultado da execução mais recente (usado pelo `evaluation/evaluate_quality.py`).
- CSV escrito com `newline=""` e `encoding="utf-8"` (corrige o bug de linhas quebradas no Windows do código legado).
- JSON escrito com `ensure_ascii=False`, indentado, lista de objetos com as mesmas chaves da tabela da seção 2.

## 7. Logging

Ver ADR 0006. Todo log de execução inclui, quando aplicável: `run_id`, `stage` (fetch/parse/dedup/store), `page_number`, `url`. Resumo final da execução loga: total de páginas tentadas, total coletado, total deduplicado, total de falhas por categoria.
