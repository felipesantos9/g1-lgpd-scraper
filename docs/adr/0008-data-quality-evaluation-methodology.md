# 0008 — Metodologia de avaliação de qualidade de dados

Status: aceito

## Contexto

O enunciado exige uma avaliação objetiva de qualidade, com amostra de referência manual e métricas cobrindo completude, atualidade, precisão, acurácia, unicidade, consistência e rastreabilidade.

## Decisão

- Amostra de referência (`evaluation/reference_sample.csv`, 10 registros) construída por **leitura e transcrição manual, item por item**: para cada card, o HTML daquele elemento específico é obtido isoladamente (sem loop/função de extração em lote) e os valores de título/resumo/data são transcritos por leitura direta, sem reusar `BeautifulSoup`/seletores do parser avaliado; a URL também é decodificada manualmente a partir do link de tracking. A única etapa compartilhada com o scraper é a navegação via Playwright (inevitável, pois a página só existe depois de JS executar — ADR 0001); a camada avaliada (extração/interpretação de campos) não compartilha código. Metodologia completa em `evaluation/reference_sample.md`, contrato em `specs/0002-data-quality-spec.md`.
- Casamento de registros por URL canônica (reaproveitando `dedup.canonical_url`), não por título.
- Métricas com fórmulas explícitas e reproduzíveis (spec 0002, seção 2), calculadas por um script (`evaluation/evaluate_quality.py`) com teste unitário próprio.
- Divergências entre as duas coletas (itens só na referência ou só no scraper) são reportadas como categoria própria, não silenciosamente ignoradas nem tratadas automaticamente como "erro": a natureza dinâmica da busca do G1 pode gerar diferenças legítimas entre duas coletas não simultâneas — mitigado disparando a execução real do scraper imediatamente após a leitura manual, na mesma sessão de trabalho.

## Alternativas consideradas

- **Amostra de referência extraída com o mesmo parser do scraper**: rejeitada — compararia o código contra si mesmo, inflando artificialmente a precisão medida (qualquer bug de seleção estaria presente nos dois lados).
- **Amostra "independente" construída por um script de extração em lote via DOM (`innerText` sobre todos os itens de uma vez)**: considerada e usada numa rodada inicial, mas rejeitada depois — ainda é um script automatizado que compartilha a mesma camada de navegação/renderização Playwright do fallback do scraper, e não atende literalmente ao "selecionada manualmente" do enunciado. Substituída pela leitura item a item.
- **Avaliação qualitativa sem métricas numéricas**: rejeitada — o enunciado pede explicitamente métricas objetivas com resultados apresentados.

## Consequências

- Positivas: avaliação fiel ao "amostra selecionada manualmente" do enunciado; validação empírica prévia da decodificação de URL (6/6 redirecionamentos confirmados numa rodada anterior) segue válida; resultados reproduzíveis e testados.
- Negativas / trade-offs: amostra pequena (10 registros, uma página) e coletada em um único momento — não é uma avaliação estatisticamente robusta de longo prazo, é uma evidência pontual de que a correção funciona; monitoramento contínuo é proposto como extensão futura (ver `docs/llm-assisted-maintenance.md`).
