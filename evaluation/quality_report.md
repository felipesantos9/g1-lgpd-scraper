# Relatório de qualidade de dados

Execução avaliada: `data/processed/g1_lgpd_lgpd_20260826_232052.csv` / `latest.csv` (28 registros, `run_id=069172c060ba`, coletado em 2026-08-26) comparado contra `evaluation/reference_sample.csv` (10 registros, transcritos manualmente item por item, ver `reference_sample.md`).

Gerado por: `python evaluation/evaluate_quality.py --reference evaluation/reference_sample.csv --scraped data/processed/latest.csv`

## Contagens de casamento

| Métrica | Valor |
|---|---|
| Total na referência | 10 |
| Total coletado pelo scraper | 28 |
| Casados (mesma URL canônica) | 10 |
| Só na referência | 0 |
| Só no scraper | 18 |

## Resultados por dimensão

| Dimensão | Métrica | Resultado |
|---|---|---|
| Completude | % registros com `title`+`url` preenchidos | **100,0%** |
| Completude | % registros com `summary`+`published_at_raw` preenchidos | **100,0%** |
| Precisão | % `title` idêntico nos registros casados | **100,0%** |
| Precisão | % `url` canônica idêntica nos registros casados | **100,0%** |
| Acurácia | % `summary` com similaridade ≥ 0,8 nos registros casados | **100,0%** |
| Unicidade | Taxa de duplicatas na saída final (pós-dedup) | **0,0%** |
| Atualidade | % dos 10 itens da referência (transcritos manualmente) presentes no scraper | **100,0%** |
| Consistência | % `published_at_iso` em ISO 8601 válido (quando havia data para parsear) | **100,0%** |
| Consistência | % `page_number` inteiro ≥ 1 | **100,0%** |
| Rastreabilidade | % registros com `run_id`+`collected_at`+`page_number` simultaneamente presentes | **100,0%** |

## Interpretação

- **A amostra de referência foi construída por leitura manual, item por item** (10 cards, HTML de cada um obtido isoladamente e transcrito por leitura direta).
- **Precisão e acurácia em 100%** nos 10 registros casados: título, URL (decodificada do link de tracking) e resumo extraídos pelo scraper coincidem exatamente com o que foi lido manualmente do HTML real, campo a campo.
- **18 registros "só no scraper"** são esperados e não indicam problema: a referência manual cobriu só a primeira página (10 itens), enquanto o scraper coletou 3 páginas (28 itens, via cliques em "Veja mais"). Esses 18 itens adicionais não têm contraparte na referência para serem comparados campo a campo, mas passam pelas mesmas checagens de completude/consistência/rastreabilidade que os demais (refletido nos 100% dessas dimensões, calculados sobre os 28 registros).
- **Completude, consistência e rastreabilidade em 100%** (calculadas sobre os 28 registros coletados, não só os 10 casados) são esperadas por construção do pipeline (`pipeline.py`): todo registro que sobrevive ao parsing recebe `run_id`, `collected_at`, `page_number`, e `published_at_iso` só é preenchido quando um dos dois formatos de data (`timeparse.py`) é reconhecido.
- **Unicidade em 0% de duplicatas** confirma que a lógica de dedup (`dedup.py`, ADR 0004) funciona mesmo coletando via múltiplos cliques em "Veja mais".

## Conclusão

Comparando uma amostra manual contra a execução real do scraper disparada na sequência, todos os 10 itens foram encontrados, com precisão e acurácia de 100% campo a campo. Isso demonstra que a correção (coleta via browser headless, ADR 0001, mais a decodificação da URL de tracking) restabeleceu a coleta corretamente.
