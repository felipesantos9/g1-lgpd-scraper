# g1-lgpd-scraper

Correção da rotina de web scraping dos resultados de busca do G1 para o termo **"lgpd"** (`https://g1.globo.com/busca/?q=lgpd`), desenvolvida como parte de um processo seletivo (NetLab UFRJ).

## Diagnóstico (resumo)

A coleta parou de funcionar porque **o G1 migrou a página de busca para uma arquitetura de micro-frontends renderizados no cliente**, o HTML devolvido pelo servidor não contém nenhum resultado; eles são inseridos no DOM depois, via JavaScript. Nenhum seletor CSS, por mais atualizado que fosse, resolveria isso sozinho. Além disso, a paginação `?page=N` não tem mais efeito: a paginação real hoje é um botão client-side "Veja mais".

Diagnóstico completo em [`docs/diagnosis.md`](docs/diagnosis.md). Visão geral da estrutura do repositório e do que cada pasta/arquivo faz: [`docs/architecture-overview.md`](docs/architecture-overview.md).

## Decisões técnicas

Documentadas como ADRs (Architecture Decision Records) em [`docs/adr/`](docs/adr/), seguindo o formato MADR. Principais:

- [0001 — Estratégia de renderização](docs/adr/0001-rendering-strategy.md): headless direto como único caminho de coleta; **BeautifulSoup é o parser único** do HTML renderizado.
- [0002 — Seletores centralizados e versionados](docs/adr/0002-selector-strategy-and-versioning.md)
- [0003 — Formato de armazenamento](docs/adr/0003-storage-format.md) (CSV + JSON)
- [0004 — Deduplicação](docs/adr/0004-deduplication-strategy.md)
- [0005 — Tratamento de erros e retries](docs/adr/0005-error-handling-and-retries.md)
- [0006 — Logging](docs/adr/0006-logging-strategy.md)
- [0007 — Estratégia de testes](docs/adr/0007-testing-strategy.md)
- [0008 — Metodologia de avaliação de qualidade](docs/adr/0008-data-quality-evaluation-methodology.md)
- [0009 — Escopo do uso de LLM](docs/adr/0009-llm-assisted-maintenance-scope.md)
- [0010 — Dependências e ambiente](docs/adr/0010-dependency-and-environment-management.md)
- [0011 — Postura sobre robots.txt](docs/adr/0011-robots-txt-compliance-stance.md)

O contrato de dados/comportamento que guiou a implementação (spec-driven development) está em [`specs/0001-scraper-core-spec.md`](specs/0001-scraper-core-spec.md) (núcleo do scraper) e [`specs/0002-data-quality-spec.md`](specs/0002-data-quality-spec.md) (avaliação de qualidade).

## Instalação

Dois caminhos suportados — ver [ADR 0010](docs/adr/0010-dependency-and-environment-management.md).

### Opção A: venv + pip

Requer Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -e ".[test]"
playwright install chromium   # baixa o binario do Chromium headless (obrigatorio para a coleta)
```

### Opção B: Docker

Requer apenas Docker (com o plugin `docker compose`, incluído no Docker Desktop). A imagem usa a base oficial `mcr.microsoft.com/playwright/python`, que já vem com o Chromium instalado — não é necessário rodar `playwright install` separadamente.

```bash
docker compose build
```

Os serviços (`scraper`, `test`, `evaluate`), com os volumes já declarados, ficam em [`docker-compose.yml`](docker-compose.yml) — ver por que essa é a forma recomendada de rodar (em vez de `docker run -v ...` cru) no [ADR 0010](docs/adr/0010-dependency-and-environment-management.md).

## Execução

### Opção A: venv + pip

```bash
python -m g1_lgpd_scraper.cli --query lgpd --max-pages 3
```

### Opção B: Docker

```bash
docker compose run --rm scraper --query lgpd --max-pages 3
```

`docker-compose.yml` já monta `data/` e `logs/` do host dentro do container, então o dataset e os logs gerados persistem normalmente fora do container — sem flags extras.

Parâmetros disponíveis (ambas as opções): `--query`, `--max-pages`, `--output-dir`, `--request-delay-seconds`, `--request-timeout-seconds`, `--max-retries` (ver `cli.py`).

Saída: `data/processed/g1_lgpd_<query>_<timestamp>.csv|json` e `data/processed/latest.csv|json`. Logs em `logs/scraper.log`.


## Testes

```bash
# venv:
pytest

# Docker:
docker compose run --rm test
```

43 testes (unitários + integração), todos rodando contra fixtures de HTML real capturadas do site (`tests/fixtures/html/`), sem rede nem browser, determinísticos e rápidos. Ver [ADR 0007](docs/adr/0007-testing-strategy.md).

## Dataset coletado

`data/processed/latest.csv` e `latest.json` contêm a execução real mais recente (28 registros, coletados em 2026-08-26 via browser headless).

## Avaliação de qualidade de dados

```bash
# venv:
python evaluation/evaluate_quality.py --reference evaluation/reference_sample.csv --scraped data/processed/latest.csv

# Docker:
docker compose run --rm evaluate
```

- Metodologia da amostra de referência (10 registros, transcritos manualmente item por item): [`evaluation/reference_sample.md`](evaluation/reference_sample.md).
- Resultado da avaliação mais recente, com interpretação: [`evaluation/quality_report.md`](evaluation/quality_report.md) — completude, precisão, acurácia e cobertura da referência em 100%; zero duplicatas.

## Proposta de uso de LLM

Proposta técnica (não implementada) de uso de LLM para apoiar diagnóstico e manutenção do scraper — detecção de drift de seletor, sugestão de seletor candidato — com validação automática obrigatória e revisão humana antes de qualquer merge. Ver [`docs/llm-assisted-maintenance.md`](docs/llm-assisted-maintenance.md) e [ADR 0009](docs/adr/0009-llm-assisted-maintenance-scope.md).

## Limitações e melhorias futuras

- **Dependência de estrutura HTML congelada em fixtures**: se o G1 mudar a estrutura novamente, os testes continuam passando contra as fixtures antigas, mas a coleta real pode voltar a falhar, mitigação proposta em `docs/llm-assisted-maintenance.md` (monitoramento de drift).
- **Sem suporte a outros tipos de resultado** (vídeo, foto, galeria têm componentes de busca separados no G1 — `videosSearchResults`, não cobertos por esta rotina, que trata apenas o componente `allSearchResults`/notícias).
- **Sem persistência em banco de dados** — CSV/JSON são suficientes para o volume atual; SQLite seria uma extensão natural para volumes maiores ou consultas mais ricas.
- **Zero resultados por falha vs. zero resultados legítimos só são distinguíveis pelo log, não pelo dataset**: o pipeline detecta a diferença (ADR 0005 — G1 renderiza `.search-not-found__root` quando não há resultados de verdade) e loga em níveis diferentes (`INFO` vs `ERROR`), mas `RunSummary`/o CSV final não carregam esse motivo de forma estruturada nem o código de saída muda — quem consumir a execução programaticamente ainda precisa ler o log, não só o dataset.
- **Volume de coleta deliberadamente pequeno nesta entrega** — ver ADR 0011; é um limite de uso adotado por precaução em relação ao `robots.txt`, não uma limitação técnica da arquitetura.
- **Estratégia de aquisição via feeds RSS/sitemap (`g1.globo.com/rss/...`, ambos publicamente acessíveis e citados no próprio `robots.txt`) foi considerada e documentada como alternativa (ADR 0011), mas não adotada nesta entrega**: exigiria construir um pipeline adicional de ingestão e indexação (consumir os feeds continuamente, indexar localmente, filtrar por termo), desproporcional ao prazo do desafio — fica registrada como extensão natural caso o uso evolua para monitoramento contínuo de maior volume.
- **Extensão futura natural**: implementar de fato a proposta de LLM (`docs/llm-assisted-maintenance.md`) como um job agendado de monitoramento de drift, rodando independentemente da coleta de produção.
