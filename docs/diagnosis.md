# Diagnóstico

Data da investigação: 2026-08-25.

## Resumo

O código legado assume que `https://g1.globo.com/busca/?q=lgpd` devolve, no HTML da resposta HTTP, os cards de resultado prontos para serem lidos com `requests` + `BeautifulSoup` (`div.resultado`, `div.titulo`, `p.resumo`, `span.data`). Isso deixou de ser verdade: **o G1 migrou a página de busca para uma arquitetura de micro-frontends renderizados no cliente**. O HTML que o servidor devolve não contém nenhum resultado, eles são inseridos no DOM depois, via JavaScript, no navegador. Um scraper baseado em `requests.get()` nunca vai ver esses resultados.

## Evidência 1 — o container de resultados vem vazio

Requisição feita com `curl` e User-Agent de navegador (sem executar JS), reproduzindo exatamente o que `requests.get()` faz:

```
curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://g1.globo.com/busca/?q=lgpd"
```

Resultado: HTTP 200, ~58KB de HTML. Dentro do `<body>`, o trecho relevante é:

```html
<div class="search-result">
  <div class="container">
    <div class="results__content all-search-results"></div>
  </div>
</div>
```

`div.results__content.all-search-results`, o container onde os resultados deveriam estar, **está vazio**. Os seletores não mudaram de nome, a estrutura que eles descreviam simplesmente não é enviada pelo servidor.

## Evidência 2 — a página é montada por micro-frontends

O `<head>` do documento carrega múltiplos bundles JS/CSS, hospedados em `s.glbimg.com/bs/delivery/delivery-components/...`, com nomes como:

- `backstage-cms-search-page` (a página em si)
- `backstage-cms-all-search-results` (o componente responsável pelos resultados de notícia/foto/etc.)
- `backstage-cms-video-search-results` (resultados de vídeo)
- `backstage-cms-search-header`, `backstage-cms-search-menu`, `backstage-cms-search-footer`, `backstage-cms-barra-globo`

Isso é confirmado por `window.__PAGE__="backstage-cms-search-page"` e por um objeto `window.__COMPONENTS__` gigante que lista, para cada componente, os chunks JS via **Webpack Module Federation** (`remoteEntry.js`, `1.js`..`4.js`, etc.) — um padrão típico de micro-frontends independentes, montados no navegador, não no servidor.

O `window.__CONTEXT__` também carrega um bloco `api_content.resource.config` com `searchProfile: "sp_g1_globo_com"` e `queryId`s (`g1.pub_editorial_query`, `g1.info_query_recency`, `g1.info_query_relevancy`), sugerindo um backend de busca/relevância interno da Globo, que é consultado depois que a página carrega — não durante o SSR.


## Evidência 3 — paginação (via Playwright, com JS executado)

`?page=N` não tem efeito: `page=1` e `page=2` devolvem os mesmos 10 resultados, na mesma ordem. A paginação real é o botão `.pagination__load-more` ("Veja mais"), que faz *append* de +10 itens na mesma `ul.results__list`, sem navegação e sem mudar a URL.

Cada card (`li.widget--info`) traz: um link cuja URL real vem escondida atrás de um redirecionamento de tracking (`measures.globo.com/v1/click?...&u=<URL-encoded>`); título e resumo; e uma data que aparece em dois formatos, dependendo da idade da matéria — relativo para recentes ("há 45 minutos") e absoluto (`dd/mm/aaaa HH:MM`) para mais antigas.

**Decisão derivada**: "página N" = N-1 cliques no botão de carregar mais, dentro de uma sessão do Playwright — o único caminho de coleta (ADR 0001; não há tentativa via `requests`, já que a Evidência 1 comprova que o SSR nunca devolve resultados para esta página).


## Evidência 4 — busca sem resultados renderiza uma estrutura própria

Testado com uma query sem nenhum resultado real (`?q=zzznonexistentquery123456xyz`): em vez do container de resultados vir vazio, o G1 renderiza `<div class="search-not-found__root">` com o texto "Nenhum resultado encontrado.". Isso é diferente de qualquer cenário de falha (browser travado, timeout, seletor quebrado) — é a página confirmando, de forma verificável, que a busca não tem nada. Usado em `BrowserSession._navigate` (ADR 0005) para distinguir "zero resultados de verdade" (log `INFO`) de "algo deu errado" (log `ERROR`).

## Causa raiz consolidada

1. **Renderização client-side**: os resultados de busca não existem no HTML servido, são injetados por JS depois do carregamento. Isso, por si só, já explica os poucos ou nenhum resultado, mesmo com seletores corretos.
2. **Seletores desatualizados**: mesmo que a renderização client-side não existisse, os seletores do código legado (`div.resultado`, `div.titulo`, `p.resumo`, `span.data`) não correspondem a nenhuma classe usada pela página atual (`results__content`, `all-search-results`, etc.), a estrutura de classes também mudou.
3. **Bug funcional no acumulador**: em `executar()`, `resultados = dados_pagina` sobrescreve a cada iteração em vez de acumular (`resultados.extend(dados_pagina)`), então mesmo que a coleta de uma página funcionasse, só a última página coletada sobreviveria no CSV final.
4. **Ausência de tratamento de erro**: `card.find(...).get_text()` explode com `AttributeError` se o seletor não casar, qualquer card malformado interrompe a execução inteira em vez de ser pulado e logado.
5. **Sem verificação de status HTTP**: `requests.get(url)` não verifica `resposta.status_code` nem trata exceções de rede.
6. **Sem deduplicação**: nada impede registros repetidos entre execuções ou dentro da mesma execução.
