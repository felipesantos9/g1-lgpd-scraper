# 0001 — Estratégia de renderização: headless direto

Status: aceito (revisado — ver Alternativas consideradas)

## Contexto

A investigação em [`docs/diagnosis.md`](../diagnosis.md), Evidência 1, confirmou — com evidência empírica reproduzível (`curl` com User-Agent de navegador real, sem executar JS), não como hipótese — que `https://g1.globo.com/busca/?q=lgpd` **sempre** devolve, na resposta HTTP crua, um container de resultados vazio. Os resultados são inseridos no DOM depois, via um componente React (`backstage-cms-all-search-results`) que roda no navegador. Um cliente HTTP puro (`requests`) nunca verá esses dados, independentemente dos seletores usados — não é um caso "às vezes falha", é um fato comprovado para esta URL.

O enunciado do desafio exige explicitamente o uso de Python + BeautifulSoup para a coleta. Isso precisa ser conciliado com a realidade de que o HTML relevante só existe depois da execução de JavaScript.

## Decisão

**Headless direto é o único caminho de coleta**: o pipeline (`pagination.py`) aciona diretamente o Playwright (`fetch/browser_client.py`) para carregar a página com um navegador Chromium headless, esperar o componente React popular o DOM, simular os cliques em "Veja mais" necessários (docs/diagnosis.md, Evidência 3), e capturar o HTML renderizado. Esse HTML é entregue ao **parser BeautifulSoup** (`parse/result_parser.py`), que continua sendo o único código de extração/interpretação de dados do projeto — cumprindo o requisito do enunciado de usar BeautifulSoup, mesmo a fonte do HTML sendo sempre o navegador.

Falhas transitórias na navegação (timeout, carregamento incompleto) têm retry com backoff exponencial (`tenacity`, reaproveitando `config.max_retries`), preservando a garantia da ADR 0005 de que falhas de rede não abortam a execução.

## Alternativas consideradas

- **Reverse-engineering da API JSON interna da Globo** (chamada direta via `requests`, sem HTML): rejeitada. A API não é descoberta nos bundles JS inspecionados; mesmo que fosse encontrada, seria um contrato privado não documentado, sujeito a autenticação, WAF ou mudança sem aviso — o mesmo tipo de fragilidade que causou o incidente original.
- **Selenium** em vez de Playwright: descartado por ter mais peças móveis (gestão manual de driver/webdriver-manager) e API menos ergonômica (sem auto-wait nativo).
- **Fast-path HTTP com fallback headless condicional**: a versão inicial tentava `requests.get()` primeiro e só acionava o Playwright se o container viesse vazio. Isso fazia sentido como *hipótese* de design, antes de confirmar com `curl` que o SSR falha **sempre**, não só às vezes. Depois de virar fato comprovado (Evidência 1), manter os dois caminhos passou a ser complexidade especulativa (YAGNI): toda execução real pagava ~0,4-0,9s de latência garantidamente desperdiçada tentando um caminho que nunca tem sucesso, além de manter um módulo (`fetch/http_client.py`), uma função de decisão (`has_results()`), uma fixture (`empty_ssr_page.html`) e testes dedicados só para cobrir um ramo que nunca é o ramo real. Removido em favor do caminho único.

## Consequências

- Positivas: resolve a causa raiz real (não só sintomas de seletor); parser único e testável independente da origem do HTML; elimina a latência fixa e a complexidade de código de um caminho que nunca tem sucesso na prática.
- Negativas / trade-offs: toda execução depende do Chromium headless (mais pesada que uma requisição HTTP simples); se o G1 um dia voltar a servir SSR para esta página, o fast-path teria que ser reintroduzido (decisão reversível, não um beco sem saída); testes automatizados não podem depender de Playwright ao vivo em CI, precisam de fixtures de HTML já renderizado (ver ADR 0007).
