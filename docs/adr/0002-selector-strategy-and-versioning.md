# 0002 — Seletores centralizados e versionados

Status: aceito

## Contexto

O incidente que originou este projeto foi causado, em parte, por seletores CSS hardcoded e espalhados pelo código (`div.resultado`, `div.titulo`, `p.resumo`, `span.data`), sem nenhum mecanismo que avisasse quando eles deixassem de casar com a página real. Isso faz com que a quebra só seja percebida quando alguém nota que os dados coletados estão vazios ou incompletos, silenciosamente, potencialmente por dias.

## Decisão

Centralizar todos os seletores em um único módulo (`parse/result_parser.py`), em uma estrutura nomeada e versionada (`SELECTORS_V1`), em vez de strings literais espalhadas pelo código. Cada campo do registro (título, url, resumo, data, container do card) tem uma entrada nomeada nesse mapa.

Um teste dedicado (`tests/unit/test_result_parser.py`) roda contra uma fixture de HTML real capturado do site e falha alto e explicitamente se qualquer seletor parar de casar, a mensagem de falha aponta exatamente qual campo/seletor quebrou, em vez de um `AttributeError` genérico em produção.

## Alternativas consideradas

- **Seletores inline como no código legado**: rejeitada, dificulta localizar e atualizar todos os pontos de acoplamento à estrutura HTML quando o site muda.

## Consequências

- Positivas: um único ponto de manutenção quando o G1 mudar a estrutura de novo; falha de seletor é detectada por teste, não em produção silenciosa; abre caminho natural para versionar seletores (`SELECTORS_V2`) se precisar suportar duas estruturas de página simultaneamente durante uma migração.
- Negativas / trade-offs: ainda é uma solução reativa, um teste local só denuncia a quebra quando alguém rodar a suíte; não há monitoramento contínuo em produção (mitigado pela proposta de uso de LLM em `docs/llm-assisted-maintenance.md`, que propõe justamente automatizar essa detecção).
