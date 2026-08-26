# 0004 — Estratégia de deduplicação

Status: aceito

## Contexto

O código legado não tinha nenhuma lógica de dedup. Além disso, a URL disponível nos cards não é a URL final da matéria, mas um link de tracking (`measures.globo.com/v1/click?...&u=<url-encoded>`) — usar esse link literal como chave produziria falsos-negativos de dedup (cada card carrega um hash de tracking único mesmo apontando para a mesma matéria).

## Decisão

- `dedup_key = sha256(canonical_url)`, onde `canonical_url` é a URL real da matéria (já decodificada do parâmetro `u`, ver `parse/result_parser.py`), sem parâmetros de query string adicionais e sem fragmento.
- Dedup **dentro da mesma execução**: ao montar a lista final de `SearchResult`, qualquer `dedup_key` repetida é mantida apenas na primeira ocorrência; ocorrências repetidas são descartadas da lista final, mas contadas e logadas (nunca silenciosas).
- Dedup **entre execuções**: antes de gravar a saída, o pipeline carrega as `dedup_key` presentes em `data/processed/latest.json` (execução anterior). Registros da execução atual que já existiam são marcados com `is_duplicate_of_previous_run=True` — **não são removidos**, para preservar rastreabilidade (ADR 0008) de que aquele registro foi visto novamente numa execução específica; ferramentas de análise podem filtrar por essa flag se quiserem só o incremento.

## Alternativas consideradas

- **Usar a `canonical_url` diretamente como `dedup_key`, sem hash**: considerada — seria igualmente determinística, já que `canonical_url` também remove tracking/query string. Rejeitada em favor do hash SHA-256 porque produz uma chave de tamanho fixo e sem caracteres especiais (acentos, barras, `?`, `&`), mais segura para usar como coluna de índice/comparação em CSV/JSON do que uma URL crua de tamanho variável.
- **Descartar duplicatas entre execuções silenciosamente**: rejeitada em favor de marcar com flag — descartar destruiria a rastreabilidade de "esse artigo apareceu de novo na busca em tal execução", que pode ser um dado relevante (ex.: para medir por quanto tempo um artigo permanece nos resultados de "lgpd").

## Consequências

- Positivas: chave de dedup estável e semanticamente correta (aponta para a matéria real, não para o link de tracking); rastreabilidade preservada entre execuções.
- Negativas / trade-offs: `data/processed/latest.json` da execução anterior precisa existir e ser legível para a dedup entre execuções funcionar.
