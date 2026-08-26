# Proposta: uso de LLM para apoiar diagnóstico e manutenção do scraper

Ver decisão de escopo em [ADR 0009](adr/0009-llm-assisted-maintenance-scope.md). Esta é uma **proposta técnica, não implementada** neste repositório, que inclui pseudocódigo ilustrativo, não uma integração real com uma API de LLM.

## Princípio norteador

> O LLM nunca é a fonte de verdade dos dados coletados. Ele só opera sobre **metadados de estrutura** (HTML, seletores, diffs, logs de execução) para acelerar tarefas de manutenção do código do scraper. Todo valor que vai para `data/processed/*.csv|json` continua vindo exclusivamente do parser determinístico (`BeautifulSoup`) rodando contra o HTML real.

Essa separação de papéis é o mecanismo anti-alucinação mais importante: mesmo que o modelo "invente" algo, isso nunca chega ao dataset final, porque o LLM não tem esse caminho de escrita.

## Onde o LLM entraria — quatro casos de uso concretos

### 1. Detecção de drift de seletor (monitoramento)

**Etapa**: execução periódica (ex.: cron semanal), antes/independente da coleta de produção.
**Função do modelo**: comparar a "assinatura estrutural" do HTML atual do site com uma assinatura de referência salva, e resumir em linguagem natural o que mudou, não decidir nada sozinho, só acelerar a leitura humana de um diff que seria tedioso de revisar manualmente.

```python
# pseudocodigo — nao implementado
def check_structural_drift(current_html, baseline_signature, llm_client):
    current_signature = extract_structure_signature(current_html)  # deterministico:
    # lista de (tag, classes, profundidade) dos elementos que os SELECTORS_V1 esperam encontrar
    if current_signature == baseline_signature:
        return None  # nada a reportar; LLM nem é chamado

    diff = compute_diff(baseline_signature, current_signature)  # deterministico
    prompt = f"""
    Voce recebe um diff estrutural de HTML (nao o conteudo das noticias, so tags/classes).
    Resuma em portugues, em no maximo 5 frases, o que mudou na estrutura.
    Nao invente informacao que nao esteja no diff. Se o diff nao for claro, diga isso explicitamente.

    DIFF:
    {diff}
    """
    summary = llm_client.complete(prompt)  # chamada ilustrativa
    return {"diff": diff, "llm_summary": summary}  # ambos vao para o humano revisar
```

**Dados fornecidos ao modelo**: só o diff estrutural (tags/classes/hierarquia), nunca o texto das notícias, não há necessidade nem motivo para o modelo ver conteúdo real de matérias nesta etapa.

### 2. Sugestão de seletor candidato quando o parser não encontra nenhum card

**Etapa**: quando o parser (`parse/result_parser.py`) roda contra o HTML renderizado pelo Playwright e não encontra nenhum `li.widget--info`, sinal de que o G1 mudou a estrutura de novo. Hoje isso não aciona nada automaticamente; numa versão futura com monitoramento assistido, acionaria esta rotina de sugestão.
**Função do modelo**: examinar um trecho do HTML real e propor seletores CSS candidatos para os campos do schema (título, resumo, data, link), para acelerar a atualização de `SELECTORS_V1` quando a estrutura mudar de novo.

```python
# pseudocodigo — nao implementado
def suggest_selectors(html_snippet, expected_fields, llm_client):
    prompt = f"""
    Este e um trecho de HTML de um card de resultado de busca. Sugira um seletor CSS
    para cada um destes campos: {expected_fields}.
    Responda APENAS em JSON: {{"campo": "seletor_css_ou_null"}}.
    Se nao conseguir identificar um campo com confianca, retorne null para ele —
    NUNCA invente um seletor que voce nao tenha visto no HTML fornecido.

    HTML:
    {html_snippet}
    """
    raw_response = llm_client.complete(prompt)
    candidates = json.loads(raw_response)  # parsing estrito; resposta fora do formato e descartada

    verified = {}
    for field, selector in candidates.items():
        if not selector:
            continue
        if verify_selector_against_fixtures(field, selector):  # ver secao de validacao abaixo
            verified[field] = selector
    return verified  # so os que passaram a verificacao chegam ao humano como candidatos
```

**Dados fornecidos ao modelo**: um ou dois cards de exemplo (HTML real, não o site inteiro) — suficiente para o modelo "ver" a estrutura, sem expor volume desnecessário de dados.


## Validação das respostas do modelo antes de incorporar

Nenhuma sugestão do LLM entra no código de produção sem passar pelas duas barreiras abaixo, nessa ordem:

1. **Validação automática e determinística** — todo seletor sugerido é executado contra:
   - o HTML real que motivou a sugestão (tem que casar com pelo menos os N cards esperados);
   - toda a suíte de fixtures já existente (`tests/fixtures/html/`) — não pode quebrar nenhum teste que já passava.

   ```python
   # pseudocodigo — nao implementado
   def verify_selector_against_fixtures(field, selector, fixtures_dir="tests/fixtures/html"):
       for fixture_path in Path(fixtures_dir).glob("*.html"):
           soup = BeautifulSoup(fixture_path.read_text(encoding="utf-8"), "html.parser")
           matches = soup.select(selector)
           if len(matches) == 0:
               return False  # seletor sugerido nao encontra nada em pelo menos uma fixture conhecida
       return True
   ```

2. **Revisão humana obrigatória** — mesmo depois de passar na validação automática, qualquer seletor/teste sugerido só é mesclado ao repositório via um PR revisado por uma pessoa, igual a qualquer outra mudança de código (ver ADR 0009). O LLM nunca tem permissão de commit/push automático.

## Mecanismos para evitar que o modelo introduza informação não presente nos dados

1. **Separação de papéis por design**: o LLM nunca recebe a tarefa "extraia o título desta notícia" nem tem qualquer caminho de escrita para `data/processed/`. Ele só recebe tarefas sobre *estrutura* (seletores, diffs, esqueleto de teste) — a extração de valor real continua 100% no `BeautifulSoup` determinístico.
2. **Grounding explícito no prompt**: toda instrução inclui uma cláusula de "não invente" e uma saída de escape explícita ("retorne `null`/'não sei' se não tiver certeza"), com exemplos no próprio prompt de quando essa saída é a resposta correta.
3. **Verificação automática obrigatória**: qualquer artefato gerado pelo modelo que vá se tornar código é executado contra HTML real antes de ser considerado, se não roda ou não produz o resultado esperado, é descartado automaticamente, sem chance de entrar "por inércia".
4. **Formato de saída estrito (JSON com schema fixo)**: reduz a superfície para texto livre alucinado; respostas fora do formato esperado são rejeitadas por um parser estrito, não interpretadas de forma tolerante.
5. **Revisão humana como último filtro**: nenhuma sugestão é aplicada de forma autônoma em produção, sempre há um humano no loop antes do merge.

## Limitações desta proposta

- Não implementada: é uma proposta de arquitetura e processo, com pseudocódigo ilustrativo, não uma integração funcional com uma API de LLM real.
- Não substitui a necessidade de fixtures de HTML atualizadas periodicamente, o LLM acelera a análise, mas ainda depende de alguém (ou de um agendamento automatizado) capturar HTML novo do site real quando houver suspeita de mudança.
