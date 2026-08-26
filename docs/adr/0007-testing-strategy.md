# 0007 — Estratégia de testes

Status: aceito

## Contexto

O código legado não tinha nenhum teste: a quebra da coleta só foi percebida em produção. O enunciado exige testes automatizados que verifiquem o funcionamento esperado dos componentes relevantes.

## Decisão

- **Testes unitários** (`tests/unit/`) rodam contra **fixtures de HTML real**, capturadas uma única vez em `tests/fixtures/html/`: `rendered_10_items.html` (após Playwright renderizar, antes de clicar em "Veja mais") e `rendered_20_items.html` (após um clique). Nenhum teste unitário faz requisição de rede ou executa um browser — são determinísticos e rápidos, adequados para CI. `fetch/browser_client.py` é a exceção parcial: sua lógica de retry/backoff é testada com um objeto de página falso (`test_browser_client.py`), não com Playwright real.
- Cobrem: `parse/result_parser.py` (extração de campos, decodificação da URL de tracking, isolamento de card malformado), `fetch/browser_client.py` (retry/backoff de navegação), `dedup.py` (canonicalização de URL, dedup dentro da run, dedup entre runs via `latest.json` simulado), `timeparse.py` (interpretação de datas relativas), `storage/*` (round-trip de escrita/leitura), `models.py` (serialização).
- **Teste de integração** (`tests/integration/test_pipeline_with_fixtures.py`) roda o pipeline completo (parse → dedup → store) contra as fixtures salvas, sem rede nem browser — verifica que os módulos se encaixam corretamente end-to-end.
- Testes que dependem de rede/Playwright ao vivo contra o site real **não fazem parte da suíte padrão**, são scripts exploratórios (os mesmos usados para produzir as fixtures), não testes de CI, porque um site de terceiros pode mudar ou ficar indisponível a qualquer momento, o que tornaria a suíte não-determinística.

## Alternativas consideradas

- **Mockar `requests`/`Playwright` com respostas sintéticas simplificadas**: rejeitado como fonte primária, fixtures de HTML real capturam nuances verdadeiras da estrutura que um mock simplificado esconderia, mascarando exatamente o tipo de regressão que este projeto existe para prevenir.
- **Testes de integração ao vivo no CI**: rejeitado — não-determinístico e dependente de terceiro; documentado como possível execução manual/local.

## Consequências

- Positivas: suíte rápida, determinística, sem dependência de rede; detecta regressão de seletor imediatamente (ADR 0002) porque usa HTML real.
- Negativas / trade-offs: as fixtures ficam "congeladas" no tempo: se o G1 mudar a estrutura de novo, os testes continuam passando (contra a fixture antiga) mas a coleta real pode voltar a falhar; mitigado pela proposta de monitoramento assistido por LLM (`docs/llm-assisted-maintenance.md`).
