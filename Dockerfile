# Imagem oficial do Playwright para Python: ja vem com Chromium e todas as
# dependencias de sistema necessarias para o navegador headless (ADR 0010),
# eliminando o passo manual `playwright install chromium` exigido na
# instalacao via venv.
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[test]"

COPY specs ./specs
COPY docs ./docs
COPY tests ./tests
COPY evaluation ./evaluation

ENTRYPOINT ["python", "-m", "g1_lgpd_scraper.cli"]
CMD ["--query", "lgpd", "--max-pages", "3"]
