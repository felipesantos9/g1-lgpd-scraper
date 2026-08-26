# Visão geral da arquitetura e estrutura do projeto

Este documento explica o que cada pasta e os principais arquivos do repositório fazem, e como eles se encaixam. Para o *porquê* das decisões, ver os [ADRs](adr/); para o *contrato* que o código implementa, ver as [specs](../specs/).

## Mapa geral

```
g1-lgpd-scraper/
├── README.md                  # ponto de entrada: diagnóstico resumido, instalação, execução
├── pyproject.toml             # dependências e configuração do pacote/pytest
├── Dockerfile                 # imagem Docker (opção B de instalação, ver ADR 0010)
├── docker-compose.yml         # serviços scraper/test/evaluate, com volumes já declarados
├── specs/                     # contrato de dados/comportamento (spec-driven development)
├── docs/                      # diagnóstico, ADRs, proposta de LLM, este documento
├── src/g1_lgpd_scraper/       # código do scraper (pacote Python instalável)
├── tests/                     # testes unitários e de integração + fixtures de HTML real
├── evaluation/                # avaliação de qualidade dos dados coletados
├── data/                      # dataset coletado (saída do scraper)
└── logs/                      # logs de execução (gitignored)
```

## `Dockerfile` e `docker-compose.yml` — instalação via Docker

Caminho alternativo ao venv+pip (ver ADR 0010). `Dockerfile` usa a imagem oficial `mcr.microsoft.com/playwright/python`, que já vem com o Chromium instalado — elimina o passo manual `playwright install`. `docker-compose.yml` declara três serviços (`scraper`, `test`, `evaluate`) com os volumes de `data/`/`logs/` já configurados em YAML, em vez de flags `-v` na linha de comando — isso evita um bug real encontrado no Git Bash/MSYS (Windows), onde o shell reescreve caminhos de container como `/app/data` para caminhos do Windows quando passados como argumento de `docker run`, quebrando o volume mount silenciosamente.

## `specs/` — contrato

- **`0001-scraper-core-spec.md`**: define o schema do registro coletado (quais campos, tipos, obrigatoriedade), a regra de paginação, a chave de deduplicação e as regras de tratamento de erro (o que é "pular card" vs. "pular página" vs. "abortar execução"). É a referência usada para escrever `models.py`, `dedup.py`, `pagination.py`.
- **`0002-data-quality-spec.md`**: define como a amostra de referência é casada com o output do scraper e a fórmula de cada métrica de qualidade (completude, precisão, acurácia, unicidade, atualidade, consistência, rastreabilidade). É a referência usada para escrever `evaluation/evaluate_quality.py`.

## `docs/` — diagnóstico e decisões

- **`diagnosis.md`**: investigação da causa raiz (por que a coleta parou de funcionar), com evidências: HTML capturado do site real, bundles JS inspecionados, `robots.txt`, testes com Playwright confirmando o mecanismo real de paginação e os dois formatos de data.
- **`adr/`**: uma decisão por arquivo, formato MADR (`NNNN-titulo.md`: Contexto → Decisão → Alternativas consideradas → Consequências). Numeração sequencial global; `template.md` é o modelo em branco. Cobrem desde a estratégia de renderização (0001) até a postura sobre `robots.txt` (0011).
- **`llm-assisted-maintenance.md`**: proposta (não implementada) de uso de LLM para apoiar diagnóstico/manutenção do scraper, com pseudocódigo e mecanismos de validação/anti-alucinação.
- **`architecture-overview.md`**: este arquivo.

## `src/g1_lgpd_scraper/` — código do scraper

| Arquivo | Responsabilidade |
|---|---|
| `config.py` | `ScraperConfig`: parâmetros de uma execução (query, páginas, timeouts, diretório de saída) |
| `models.py` | `RawCard` (dado bruto extraído de um card) e `SearchResult` (registro final, com schema completo) |
| `parse/result_parser.py` | Parser central com **BeautifulSoup**. Seletores centralizados e versionados (`SELECTORS_V1`); extrai e decodifica a URL real do link de tracking; isola falhas por card |
| `fetch/browser_client.py` | Caminho de coleta (ADR 0001): Playwright renderiza a página, simula os cliques em "Veja mais", com retry/backoff (`tenacity`) para falhas transitórias de navegação; distingue busca genuinamente sem resultados (`.search-not-found__root`) de falha real (ADR 0005) |
| `pagination.py` | Orquestra a coleta até `max_pages` via `fetch/browser_client.py`, delegando o parsing do HTML resultante para `result_parser` |
| `timeparse.py` | Converte o texto de data da busca (relativo — "há 2 dias" — ou absoluto — "18/08/2026 13:23") para `datetime` |
| `dedup.py` | Chave de dedup (hash da URL canônica), dedup dentro da execução e marcação de duplicatas entre execuções |
| `storage/csv_writer.py`, `storage/json_writer.py` | Persistência da saída em CSV e JSON |
| `logging_config.py` | Configuração de logging (console + arquivo, ver ADR 0006) |
| `pipeline.py` | Orquestrador de ponta a ponta: fetch → parse → enriquecimento (data/dedup key) → dedup → store. Ponto de entrada programático (`run(config)`) |
| `cli.py` | Interface de linha de comando (`python -m g1_lgpd_scraper.cli ...`), monta um `ScraperConfig` a partir de argumentos e chama `pipeline.run` |

Fluxo de uma execução: `cli.py` → `pipeline.run()` → `pagination.collect_raw_cards()` (aciona `fetch/browser_client.py`, entregando o HTML renderizado para `parse/result_parser.py`) → `pipeline.py` enriquece cada `RawCard` em `SearchResult` (usando `timeparse.py` e `dedup.py`) → `storage/*` grava CSV/JSON.

## `tests/` — testes

- **`unit/`**: um arquivo de teste por módulo do pacote (`test_result_parser.py`, `test_dedup.py`, `test_pagination.py`, `test_browser_client.py`, `test_timeparse.py`, `test_models.py`, `test_storage.py`, `test_evaluate_quality.py`). Rodam contra fixtures de HTML real, sem rede.
- **`integration/test_pipeline_with_fixtures.py`**: testa o pipeline parse→dedup→store completo, também contra fixtures, sem rede.
- **`fixtures/html/`**: HTML real capturado do site — `rendered_10_items.html` e `rendered_20_items.html` (Playwright renderizado, antes/depois de clicar em "Veja mais"). São a base de tudo o que os testes de parsing verificam (ver ADR 0007).
- **`conftest.py`**: fixtures do pytest que carregam os arquivos de `fixtures/html/`.

## `evaluation/` — avaliação de qualidade

- **`reference_sample.csv`** + **`reference_sample.md`**: amostra "ground truth" pequena (10 registros), construída por leitura e transcrição **manual, item por item** — o HTML de cada card é obtido isoladamente (uma chamada por item, não um loop de extração) e os campos são lidos e transcritos à mão, sem reusar `BeautifulSoup` nem nenhuma função do parser avaliado (`parse/result_parser.py`); a única etapa compartilhada com o scraper é a navegação via Playwright, inevitável nesta página (ADR 0001). Metodologia completa em `reference_sample.md`.
- **`evaluate_quality.py`**: script que casa a referência com `data/processed/latest.csv` por URL canônica e calcula as métricas definidas em `specs/0002-data-quality-spec.md`.
- **`quality_report.md`**: resultado da avaliação mais recente, com números e interpretação.

## `data/` — dataset

- **`processed/`**: saída do scraper — `g1_lgpd_<query>_<timestamp>.csv|json` (snapshot de cada execução) e `latest.csv|json` (sempre a execução mais recente; é o arquivo que `evaluate_quality.py` consome).
- **`raw/`**: reservado para HTML bruto de depuração, gitignored (vazio por padrão).

## `logs/`

`scraper.log`, gerado a cada execução (console mostra `INFO`+, arquivo grava `DEBUG`+). Gitignored — não faz parte da entrega, é artefato de execução local.
