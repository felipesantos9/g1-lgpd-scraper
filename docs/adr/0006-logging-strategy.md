# 0006 — Estratégia de logging

Status: aceito

## Contexto

O código legado só tinha `print()` esparsos, sem nível de severidade, sem persistência, e sem campos estruturados (qual página, qual URL, qual etapa). Isso torna impossível diagnosticar depois o que aconteceu numa execução específica (requisito do enunciado: "logs que permitam acompanhar e diagnosticar a execução").

## Decisão

Usar o módulo `logging` da stdlib (sem dependência extra), configurado em `logging_config.py`:

- Handler de console em nível `INFO` (visão de progresso durante a execução).
- Handler de arquivo em nível `DEBUG`, para diagnóstico detalhado posterior.
- Formatter inclui timestamp, nível, `run_id`, e a mensagem, módulos que precisam de contexto extra (página, URL, stage) o incluem na própria mensagem via `logger.info("...", extra={...})` ou f-string, mantendo o formato simples e legível em texto puro (não JSON), já que o volume de execução é pequeno e o consumo principal é humano.

## Alternativas consideradas

- **Logging estruturado em JSON** (`python-json-logger` ou similar): rejeitado por adicionar uma dependência para um volume de execução pequeno, onde texto legível já é suficiente; pode ser revisitado se o projeto crescer para uma pipeline de produção monitorada.
- **Apenas `print()` com timestamps manuais**: rejeitado — foi exatamente a limitação do código legado; não permite níveis de severidade nem handlers múltiplos (console + arquivo).

## Consequências

- Positivas: histórico persistente em arquivo para depuração pós-execução; níveis de severidade permitem filtrar ruído; zero dependência nova.
- Negativas / trade-offs: sem agregação/observabilidade centralizada, aceitável dado o escopo do projeto.
