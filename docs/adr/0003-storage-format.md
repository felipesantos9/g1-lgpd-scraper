# 0003 — Formato de armazenamento

Status: aceito

## Contexto

O código legado gravava apenas CSV. O enunciado exige salvar em CSV, JSON ou outro formato estruturado, e pede uma base de dados coletada como parte da entrega.

## Decisão

- Gravar **os dois formatos** a cada execução: CSV (legível por humanos/Excel/planilhas, adequado para a amostra de revisão manual) e JSON (machine-friendly, consumido por `evaluation/evaluate_quality.py` e por dedup entre execuções).
- Nome de arquivo com timestamp (`g1_lgpd_<query>_<YYYYMMDD_HHMMSS>.csv|json`) para preservar histórico de execuções, mais uma cópia `latest.csv`/`latest.json` sempre sobrescrita, que é o contrato estável usado pelas ferramentas (evaluation, dedup entre execuções).
- CSV aberto com `newline=""` e `encoding="utf-8"`. JSON gravado com `ensure_ascii=False` (preserva acentuação legível) e indentação para diff-friendliness em revisão manual/git.

## Alternativas consideradas

- **Apenas CSV**: rejeitada — dificulta consumo programático (tipos, aninhamento) pelas ferramentas de avaliação de qualidade.
- **Banco de dados (SQLite)**: considerado, mas rejeitado por complexidade desproporcional ao escopo (execução pontual, não um serviço de longa duração); pode ser uma extensão futura mencionada nas limitações do README.

## Consequências

- Positivas: saída dupla cobre tanto revisão humana quanto consumo programático; `latest.*` dá um contrato estável para o restante do pipeline sem precisar descobrir o nome do arquivo mais recente.
- Negativas / trade-offs: duplica o custo de I/O (pequeno, dado o volume) e exige manter os dois writers em sincronia quando o schema mudar.
