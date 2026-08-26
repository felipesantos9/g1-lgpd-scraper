# 0010 — Gestão de dependências e ambiente

Status: aceito

## Contexto

O projeto precisa ser reproduzível por uma banca avaliadora em uma máquina diferente da de desenvolvimento, incluindo a dependência pesada e pouco comum de um navegador headless (Playwright/Chromium).

## Decisão

Dois caminhos de instalação são suportados e documentados no README, para cobrir tanto quem prefere um ambiente Python local quanto quem prefere isolamento total:

1. **venv + pip** (`pyproject.toml`): dependências declaradas com versões mínimas fixadas (`>=`) para bibliotecas estáveis (`requests`, `beautifulsoup4`, `tenacity`, `pytest`) e o pacote `playwright` como dependência explícita. Exige o passo extra `playwright install chromium` (baixa o binário do navegador; não vem incluído no pacote pip). Ambiente Python mínimo: 3.10+ (uso de sintaxe moderna de type hints e `datetime` com timezone).
2. **Docker** (`Dockerfile` + `docker-compose.yml`): usa a imagem oficial `mcr.microsoft.com/playwright/python:v1.62.0-noble` como base, ela já vem com o Chromium e todas as dependências de sistema do navegador pré-instaladas, então `docker compose build` sozinho já produz uma imagem pronta para rodar, sem o passo manual de `playwright install`. A tag da imagem é fixada na mesma versão do pacote `playwright` declarada em `pyproject.toml`, para garantir que o binário do navegador e a biblioteca Python estejam sempre em sintonia. Os volumes que persistem `data/` e `logs/` do host para dentro do container são declarados em `docker-compose.yml` (serviços `scraper`, `test`, `evaluate`).

## Alternativas consideradas

- **`requirements.txt` simples**: rejeitada em favor de `pyproject.toml`, que permite declarar o projeto como pacote instalável (`pip install -e .`), facilitando imports em testes e no CLI sem manipular `sys.path`.
- **Dockerfile customizado a partir de uma imagem Python genérica** (`python:3.11-slim` + `apt-get install` das dependências do Chromium manualmente): rejeitada em favor da imagem oficial do Playwright — replicar manualmente a lista de pacotes de sistema que o Chromium headless precisa é frágil e muda entre versões do Playwright; a imagem oficial já resolve isso e é mantida pelo próprio time do Playwright.


## Consequências

- Positivas: instalação reprodutível em poucos comandos documentados nos dois caminhos; dependências com versão mínima evitam quebras por breaking changes de patch; o caminho Docker elimina o download manual de ~150-300MB do Chromium e qualquer problema de dependência de sistema operacional, ao custo de baixar uma imagem base maior uma única vez.
- Negativas / trade-offs: manter dois caminhos de instalação significa manter os dois sincronizados (se a versão do `playwright` em `pyproject.toml` mudar, a tag da imagem base no `Dockerfile` precisa ser atualizada junto).
