# Metodologia da amostra de referência

## Objetivo

Construir uma pequena amostra de referência, selecionada manualmente a partir dos resultados efetivamente presentes na página (conforme pedido pelo enunciado), para comparar contra a saída real do scraper e medir objetivamente a qualidade da coleta.

## Como foi coletada

- Data: 2026-08-26.
- Fonte: `https://g1.globo.com/busca/?q=lgpd` (primeira página de resultados, 10 itens).
- **Processo**:
  1. Uma navegação carrega a página.
  2. Cada card foi lido diretamente e os valores de `title`, `summary` e `published_at_raw` foram **transcritos manualmente**, um a um, por leitura direta do trecho de HTML.
  3. A URL de cada item também foi decodificada manualmente: o link de cada card é um redirecionamento de tracking (`measures.globo.com/v1/click?...&u=<URL-encoded>`); o parâmetro `u` foi lido e percent-decodificado à mão.
- Total de registros na amostra: **10**
