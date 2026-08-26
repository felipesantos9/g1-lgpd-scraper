# Spec 0002 — Avaliação de qualidade de dados

Define o contrato de `evaluation/evaluate_quality.py`: como a amostra de referência (`evaluation/reference_sample.csv`, metodologia em `reference_sample.md`) é comparada contra a saída do scraper (`data/processed/latest.csv`), e como cada dimensão de qualidade é medida.

## 1. Casamento de registros

Registros dos dois lados são casados por **URL canônica** (mesma função `canonical_url` de `dedup.py`, reaplicada aos dois conjuntos). Três categorias resultantes:

- **Casados**: presentes em ambos — base para completude/precisão/acurácia/consistência por campo.
- **Só na referência**: o scraper não coletou um item que estava na página real no momento da referência (possível perda real, ou natural churn da busca entre as duas coletas — ver limitação em `reference_sample.md`).
- **Só no scraper**: o scraper coletou algo que não está na referência (esperado, dado que a busca é dinâmica e as coletas não são simultâneas).

## 2. Dimensões e métricas

| Dimensão | Métrica | Fórmula |
|---|---|---|
| **Completude** | % de registros do scraper com todos os campos obrigatórios (`title`, `url`) preenchidos, e % com campos opcionais (`summary`, `published_at_raw`) preenchidos | `preenchidos / total` |
| **Precisão** (exatidão sintática) | Para registros casados: taxa de igualdade exata de `title` e `url` | `iguais / casados` |
| **Acurácia** (fidelidade semântica) | Para registros casados: similaridade textual de `summary` (`difflib.SequenceMatcher`, threshold ≥ 0.8 conta como acurado — G1 pode truncar/normalizar espaços diferente entre as duas extrações) | `similares / casados` |
| **Unicidade** | Taxa de duplicatas na saída do scraper, antes e depois do dedup (usa o próprio `dedup_within_run`) | `1 - (unicos / total_bruto)` |
| **Atualidade** | Diferença entre `collected_at` e `published_at_iso` (quando disponível); e % de registros da referência (mais recentes) que aparecem no scraper | distribuição de deltas + taxa de cobertura dos itens mais recentes |
| **Consistência** | % de registros com `published_at_iso` em formato ISO 8601 válido (quando `published_at_raw` não é nulo); `page_number` sempre inteiro ≥ 1 | validação de schema por campo |
| **Rastreabilidade** | % de registros com `run_id`, `collected_at` e `page_number` simultaneamente presentes (sempre deveria ser 100%, por construção do pipeline) | `completos / total` |

## 3. Saída

`evaluation/quality_report.md`: tabela com o valor de cada métrica da execução mais recente, seguida de uma seção de interpretação escrita manualmente após rodar o script (não gerada automaticamente — a interpretação exige julgamento humano sobre o que os números significam).

## 4. Teste

`evaluate_quality.py` tem teste unitário próprio (`tests/unit/test_evaluate_quality.py`) com uma fixture sintética minúscula (poucos registros conhecidos, valores de métrica calculáveis à mão), para provar que o próprio script de avaliação funciona corretamente — não seria aceitável confiar em métricas de qualidade calculadas por um script não testado.
