# 0009 — Escopo do uso de LLM na manutenção do scraper

Status: aceito (proposta, não implementada)

## Contexto

O enunciado pede uma proposta técnica de uso de LLM para apoiar diagnóstico/manutenção/monitoramento da coleta. É preciso decidir o escopo dessa proposta com o mesmo rigor das demais decisões, principalmente porque LLMs podem alucinar, e este é um pipeline de dados onde inventar informação é inaceitável.

## Decisão

O uso de LLM é restrito a **apoio ao diagnóstico e à manutenção do código do scraper** (detecção de drift de seletor, sugestão de seletor candidato, geração de rascunho de teste, comparação de versões de página), nunca à **extração ou geração dos dados finais coletados**. Ou seja: o LLM pode sugerir *como* extrair um campo, mas nunca *qual é o valor* de um campo de um resultado real, esse valor sempre vem do parser determinístico (`BeautifulSoup`) rodando contra o HTML real.

Toda sugestão do LLM passa por validação automática (roda contra HTML real, resultado comparado a um golden set) e, antes de qualquer merge no código de produção, por revisão humana explícita, nunca é aplicada automaticamente em produção.

Detalhamento completo em `docs/llm-assisted-maintenance.md`.

## Alternativas consideradas

- **Integração completa e automática (LLM decide e aplica correções em produção sem revisão humana)**: rejeitada, o próprio enunciado pede uma proposta, não uma implementação completa, e aplicar sugestões de IA sem validação humana em um pipeline de dados é um risco desproporcional ao benefício nesta escala de projeto.

## Consequências

- Positivas: acelera a detecção de drift de seletor (potencialmente antes que a coleta de produção silenciosamente degrade) sem colocar em risco a integridade dos dados coletados.
- Negativas / trade-offs: é uma proposta, não uma capacidade em produção, não implementada neste repositório; requer disciplina de processo (revisão humana obrigatória) para não se tornar um vetor de erro silencioso caso a organização decida implementá-la depois.
