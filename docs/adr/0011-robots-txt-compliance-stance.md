# 0011 — Postura sobre robots.txt

Status: aceito

## Contexto

`https://g1.globo.com/robots.txt` contém explicitamente:

```
User-Agent: *
Disallow: /busca/*
```

Ou seja, o próprio G1 solicita, pelo protocolo padrão de exclusão de robôs, que crawlers automatizados não acessem a área de busca do site. Isso é um fato verificado e precisa ser tratado com transparência, não omitido.

## Decisão

- Este projeto é entregue e executado com escopo de volume de coleta pequeno e deliberadamente limitado (poucas páginas, ver `specs/0001-scraper-core-spec.md`) e rate limiting conservador entre requisições (`time.sleep` configurável, ADR 0005), para minimizar carga sobre a infraestrutura do G1.
- O README declara explicitamente essa restrição de `robots.txt` na seção de limitações, com transparência sobre a existência do `Disallow: /busca/*` — a decisão é declará-lo e operar dentro de um escopo pontual e de baixo volume, não ignorá-lo silenciosamente.
- O scraper não tenta contornar nenhuma medida técnica anti-bot (não falsifica headers além de um User-Agent padrão de navegador, não usa proxies rotativos, não tenta resolver captchas).

## Alternativas consideradas

- **Ignorar o robots.txt sem mencionar**: rejeitada, desonesto tecnicamente.
- **Migrar a fonte de dados para feeds RSS (`g1.globo.com/rss/g1/...`) ou para o sitemap XML** (ambos citados no próprio `robots.txt`, e ambos confirmados publicamente acessíveis, sem `Disallow`): considerada como estratégia de aquisição alternativa, nenhuma delas passa pelo endpoint `/busca/`, então nenhuma conflita com o `robots.txt`. Não foi adotada nesta entrega porque a busca por palavra-chave ("lgpd") deixaria de ser delegada ao G1 e passaria a ser responsabilidade do próprio projeto: seria necessário consumir os feeds/sitemap continuamente, indexar o conteúdo localmente (ex. Elasticsearch/Postgres full-text) e então filtrar por termo, um pipeline de ingestão e indexação adicional, desproporcional ao prazo e ao escopo deste desafio. Fica registrado como extensão natural caso o uso evolua de "exercício pontual" para "monitoramento contínuo" (ver seção de limitações e melhorias futuras do README).

## Consequências

- Positivas: transparência técnica e ética documentada; a solução entregue resolve o problema proposto no enunciado dentro do escopo e prazo do exercício.
- Negativas / trade-offs: o volume e a frequência de execução ficam deliberadamente limitados por este ADR (não é uma limitação técnica da arquitetura em si, é um limite de uso adotado por precaução); se o escopo evoluir para monitoramento contínuo de maior volume, a estratégia de aquisição via RSS/sitemap (acima) passa a ser a opção natural a avaliar primeiro, por já ser publicamente sancionada pelo `robots.txt`.
