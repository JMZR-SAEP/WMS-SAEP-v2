# Filas de Trabalho — Triagem, Ordenação e Teclado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar as filas de trabalho (`fila_autorizacao`, `fila_atendimento`) triáveis num relance — sinal de idade e de saldo no cartão, ordenação alternativa por saldo/setor sem substituir o FIFO de domínio, placeholder de busca legível a 375px, e travessia por teclado entre cartões.

**Architecture:** Backend: um selector novo (`saldo_insuficiente_por_requisicoes`) que faz UM batch de saldo por página inteira de fila (reusa `saldos_por_materiais`, já usado por #195), mais dois helpers de view que anotam `data_antiga`/`saldo_insuficiente` nos objetos já paginados. A ordenação alternativa (`?ordenar=saldo|setor`) vive na view, não no selector — `setor` é `order_by` SQL puro; `saldo` reordena em Python a lista completa (pré-paginação, pós-filtro) porque o cálculo de saldo já é Python-side no projeto inteiro. URL permanece fonte de verdade via `apps/core/querystring.py` (padrão já usado em `historico_requisicoes_view`). Frontend: templates ganham badge de saldo + tom de idade reusando tokens existentes (`text-warning-text`), dois links de ordenação com `components/button.html`, e um wrapper `x-data` novo (Alpine) para travessia por setas — sem tocar nos partials compartilhados (`table.html#cards_abertura`).

**Tech Stack:** Django 6 (ORM: `Subquery`/`OuterRef` já em uso, aqui evitado em favor de Python batch — ver Task 2), Alpine.js (padrão `alpine:init` + `Alpine.data`), Tailwind (tokens de cor do design system), pytest + pytest-django, camada Navegador (Playwright via `pytest.mark.navegador`, ADR-0019).

**Spec:** issue GitHub #194 (`JMZR-SAEP/WMS-SAEP-v2#194`) + shape do agente `Plan` no comment da issue (decisões 1-7, citadas inline em cada task abaixo).

## Global Constraints

- Identificadores de domínio em PT-BR; comentários de código em PT-BR (AGENTS.md).
- `verbose_name`/`verbose_name_plural` não se aplicam aqui (nenhum model novo).
- Migrations locais são efêmeras — nenhuma task deste plano altera `models.py`, então não há reset de banco necessário.
- Gate obrigatório (issue #194, citando a varredura #166): `make test-navegador` para qualquer mudança de markup de listagem — Tasks 1, 3, 4 e 5 tocam markup das filas e exigem rodar a lane Navegador antes de fechar.
- DESIGN.md §Layout: nenhuma `grid-cols-2` fixa em cartão de listagem; cabeçalho de cartão não-`flex-row` abaixo de `xl` (só acima de 1280px) — Task 3 precisa seguir esse padrão ao adicionar o badge de saldo em `fila_autorizacao.html` (que hoje não tem badge nenhum).
- Fila é ordem de DOMÍNIO (FIFO por `atualizado_em`) — nenhuma task pode fazer a ordenação alternativa (`?ordenar=`) substituir o default; ausência do parâmetro sempre volta ao FIFO puro, sem nenhuma query/anotação extra.
- Rodar `uv run ruff format .`, `uv run ruff check .` e `uv run mypy apps` antes de cada commit (padrão do projeto, não repetido em cada task abaixo).

---

## Mapa de arquivos

| Arquivo | O que muda |
|---|---|
| `apps/requisicoes/selectors.py` | + `saldo_insuficiente_por_requisicoes()` (Task 2) |
| `apps/requisicoes/views.py` | + `_marcar_idade_antiga`, `_marcar_saldo_insuficiente` (Task 3); `ordenar` em `fila_autorizacao_view`/`fila_atendimento_view` (Task 4); placeholder mais curto (Task 1) |
| `apps/requisicoes/templates/requisicoes/fila_autorizacao.html` | placeholder (T1); badge+tom (T3); link de ordenação (T4); wrapper de teclado (T5) |
| `apps/requisicoes/templates/requisicoes/fila_atendimento.html` | idem, no `partialdef corpo_cartao` |
| `apps/requisicoes/templates/requisicoes/lista_minhas.html` | placeholder (T1) |
| `apps/core/static/core/js/travessia-fila.js` | novo (Task 5) |
| `apps/core/templates/base.html` | registra o script novo (Task 5) |
| `apps/requisicoes/tests/test_views.py` | testes das Tasks 1-4 |
| `apps/requisicoes/tests/test_navegador_fila_teclado.py` | novo (Task 5) |

---

### Task 1: Encurtar o placeholder de busca nas 3 telas de fila

**Achado que muda o escopo original:** a string-fonte já é `"Número público, código ou nome do material"` (completa, com "l") nas 3 telas — verificado no navegador dev a 375px: o campo corta visualmente para "...nome do materia" porque o texto não cabe no input, não porque a string está truncada. O fix é encurtar o texto, não "consertar" a string.

**Files:**
- Modify: `apps/requisicoes/templates/requisicoes/fila_autorizacao.html:13`
- Modify: `apps/requisicoes/templates/requisicoes/fila_atendimento.html:13`
- Modify: `apps/requisicoes/templates/requisicoes/lista_minhas.html:26`
- Test: `apps/requisicoes/tests/test_views.py`

**Interfaces:**
- Consumes: nada (mudança de string estática).
- Produces: nada consumido por outra task.

- [ ] **Step 1: Escrever os 3 testes que travam o novo texto**

Adicionar em `apps/requisicoes/tests/test_views.py`, perto de `test_fila_autorizacao_renderiza_cartoes` (linha ~3070):

```python
@pytest.mark.django_db
def test_fila_autorizacao_placeholder_de_busca_cabe_a_375(
    client, chefe_obras, req_enviada_solicitante
):
    """Texto mais curto: o antigo cortava para "nome do materia" a 375px."""
    _login(client, chefe_obras)
    response = client.get(reverse('requisicoes:autorizacoes'))
    html = response.content.decode('utf-8')
    assert 'placeholder="Número, código ou material"' in html


@pytest.mark.django_db
def test_fila_atendimento_placeholder_de_busca_cabe_a_375(
    client, aux_almoxarifado, req_autorizada_view
):
    _login(client, aux_almoxarifado)
    response = client.get(reverse('requisicoes:atendimentos'))
    html = response.content.decode('utf-8')
    assert 'placeholder="Número, código ou material"' in html


@pytest.mark.django_db
def test_minhas_placeholder_de_busca_cabe_a_375(client, solicitante):
    _login(client, solicitante)
    response = client.get(reverse('requisicoes:minhas'))
    html = response.content.decode('utf-8')
    assert 'placeholder="Número, código ou material"' in html
```

- [ ] **Step 2: Rodar os 3 testes e confirmar que falham**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k placeholder_de_busca_cabe -v`
Expected: 3 FAIL (placeholder atual ainda é o texto longo).

- [ ] **Step 3: Encurtar o placeholder nas 3 telas**

`apps/requisicoes/templates/requisicoes/fila_autorizacao.html:13`, trocar:
```django
{% include "components/busca_simples.html" with action_url=url_lista id="busca-autorizacoes" name="busca" label="Requisição ou material" value=busca placeholder="Número público, código ou nome do material" %}
```
por:
```django
{% include "components/busca_simples.html" with action_url=url_lista id="busca-autorizacoes" name="busca" label="Requisição ou material" value=busca placeholder="Número, código ou material" %}
```

`apps/requisicoes/templates/requisicoes/fila_atendimento.html:13`, mesma troca (`id="busca-atendimentos"` preservado).

`apps/requisicoes/templates/requisicoes/lista_minhas.html:26`, mesma troca de `placeholder=` (preservar `id`/`name`/`label`/`value` da linha).

- [ ] **Step 4: Rodar os 3 testes e confirmar que passam**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k placeholder_de_busca_cabe -v`
Expected: 3 PASS.

- [ ] **Step 5: Confirmar visualmente a 375px**

No navegador (dev server já rodando), abrir `/requisicoes/autorizacoes/` a 375px de viewport e conferir que o placeholder aparece inteiro, sem corte.

- [ ] **Step 6: Commit**

```bash
git add apps/requisicoes/templates/requisicoes/fila_autorizacao.html apps/requisicoes/templates/requisicoes/fila_atendimento.html apps/requisicoes/templates/requisicoes/lista_minhas.html apps/requisicoes/tests/test_views.py
git commit -m "fix(#194): encurta placeholder de busca das filas para caber a 375px"
```

---

### Task 2: Selector de saldo agregado por página de fila

**Files:**
- Modify: `apps/requisicoes/selectors.py` (nova função, após `saldos_por_materiais`, ~linha 433)
- Test: `apps/requisicoes/tests/test_selectors.py` (confirmar que o arquivo existe; se não existir, criar seguindo o padrão de `test_views.py` — fixtures via `conftest.py` compartilhado)

**Interfaces:**
- Consumes: `saldos_por_materiais(material_ids: list[int]) -> dict[int, dict]` (já existe, `apps/requisicoes/selectors.py:390`).
- Produces: `saldo_insuficiente_por_requisicoes(requisicao_ids: Iterable[int]) -> dict[int, bool]` — chave `requisicao_id`, valor `True` se **algum** item da requisição pede mais que o saldo disponível do material. Requisição sem entrada no dict = sem itens (trate como `False` via `.get(pk, False)`). Consumida por Task 3 (sinal no cartão) e Task 4 (ordenação por saldo).

- [ ] **Step 1: Confirmar onde ficam os testes de selectors**

Run: `find apps/requisicoes/tests -iname "test_selectors*"`
Se existir `test_selectors.py`, usar esse arquivo. Se não existir, criar `apps/requisicoes/tests/test_selectors.py` com o cabeçalho:
```python
"""Testes de apps/requisicoes/selectors.py."""

import pytest

from apps.requisicoes.models import ItemRequisicao, Requisicao
from apps.requisicoes.selectors import saldo_insuficiente_por_requisicoes
```

- [ ] **Step 2: Escrever o teste que falha**

```python
@pytest.mark.django_db
def test_saldo_insuficiente_por_requisicoes_marca_so_quem_nao_cobre(
    solicitante, setor_obras, material_disponivel, material_sem_saldo
):
    req_ok = Requisicao.objects.create(
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
        estado='aguardando_autorizacao', numero_publico='REQ-2026-8001',
    )
    ItemRequisicao.objects.create(
        requisicao=req_ok, material=material_disponivel, quantidade_solicitada=1,
    )
    req_insuficiente = Requisicao.objects.create(
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
        estado='aguardando_autorizacao', numero_publico='REQ-2026-8002',
    )
    ItemRequisicao.objects.create(
        requisicao=req_insuficiente, material=material_sem_saldo, quantidade_solicitada=1,
    )

    resultado = saldo_insuficiente_por_requisicoes([req_ok.pk, req_insuficiente.pk])

    assert resultado == {req_ok.pk: False, req_insuficiente.pk: True}


@pytest.mark.django_db
def test_saldo_insuficiente_por_requisicoes_sem_itens_devolve_dict_vazio():
    assert saldo_insuficiente_por_requisicoes([]) == {}
```

Use `from apps.requisicoes.models import EstadoRequisicao` e `estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO` em vez da string literal — ajustar o import junto com o Step acima.

- [ ] **Step 3: Rodar e confirmar falha**

Run: `uv run pytest apps/requisicoes/tests/test_selectors.py -k saldo_insuficiente_por_requisicoes -v`
Expected: FAIL com `ImportError` ou `NameError` (`saldo_insuficiente_por_requisicoes` não existe).

- [ ] **Step 4: Implementar o selector**

Em `apps/requisicoes/selectors.py`, logo após `saldos_por_materiais` (depois da linha 432, antes de `historico_requisicoes_visiveis_para`):

```python
def saldo_insuficiente_por_requisicoes(
    requisicao_ids: Iterable[int],
) -> dict[int, bool]:
    """Pra cada requisição, algum item pede mais que o saldo disponível?

    Reusa `saldos_por_materiais` (a mesma fonte do sinal já usado no detalhe/
    modal de autorizar, #195) num único batch pra página inteira de fila, em
    vez de uma chamada por requisição — é o que torna este selector seguro
    pra listagem (Task 2/#194), diferente de `_anotar_saldo_para_autorizar`
    em views.py, que opera sobre os itens de UMA requisição já carregada.
    """
    itens = list(
        ItemRequisicao.objects.filter(requisicao_id__in=list(requisicao_ids)).values(
            'requisicao_id', 'material_id', 'quantidade_solicitada'
        )
    )
    if not itens:
        return {}
    saldos = saldos_por_materiais([item['material_id'] for item in itens])
    resultado: dict[int, bool] = {}
    for item in itens:
        info = saldos.get(item['material_id'])
        if info is None:
            continue
        insuficiente = info['saldo_disponivel'] < item['quantidade_solicitada']
        resultado[item['requisicao_id']] = (
            resultado.get(item['requisicao_id'], False) or insuficiente
        )
    return resultado
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `uv run pytest apps/requisicoes/tests/test_selectors.py -k saldo_insuficiente_por_requisicoes -v`
Expected: 2 PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/requisicoes/selectors.py apps/requisicoes/tests/test_selectors.py
git commit -m "feat(#194): selector de saldo insuficiente em batch por página de fila"
```

---

### Task 3: Sinal de triagem no cartão — idade e saldo

**Decisões do shape (issue #194, comment):** limiar único de 24h corridas (sem escalada); reusa o token de `quantidade.html` (`text-warning-text`); "quantidade" no cartão fica como está (fora de escopo).

**Files:**
- Modify: `apps/requisicoes/views.py` (helpers + chamada nas duas views de fila)
- Modify: `apps/requisicoes/templates/requisicoes/fila_autorizacao.html` (badge + tom)
- Modify: `apps/requisicoes/templates/requisicoes/fila_atendimento.html` (badge + tom, no `corpo_cartao`)
- Test: `apps/requisicoes/tests/test_views.py`

**Interfaces:**
- Consumes: `saldo_insuficiente_por_requisicoes` (Task 2, `apps/requisicoes/selectors.py`).
- Produces: cada `Requisicao` em `page_obj.object_list` ganha os atributos dinâmicos `req.data_antiga: bool` e `req.saldo_insuficiente: bool`, lidos pelos templates.

- [ ] **Step 1: Escrever os testes de view (idade)**

Em `apps/requisicoes/tests/test_views.py`, perto de `test_fila_autorizacao_coluna_enviada_em` (linha ~2915), adicionar:

```python
@pytest.mark.django_db
def test_fila_autorizacao_timestamp_recente_sem_tom_de_warning(
    client, chefe_obras, solicitante, setor_obras
):
    from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-8101',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    TimelineRequisicao.objects.create(
        requisicao=req, evento=EventoTimeline.ENVIO_AUTORIZACAO, ator=solicitante,
    )
    _login(client, chefe_obras)
    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')
    assert 'text-warning-text">Enviada em' not in html
    assert 'text-text-tertiary">Enviada em' in html


@pytest.mark.django_db
def test_fila_autorizacao_timestamp_com_mais_de_24h_ganha_tom_de_warning(
    client, chefe_obras, solicitante, setor_obras
):
    from datetime import timedelta

    from django.utils import timezone

    from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-8102',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    evento = TimelineRequisicao.objects.create(
        requisicao=req, evento=EventoTimeline.ENVIO_AUTORIZACAO, ator=solicitante,
    )
    TimelineRequisicao.objects.filter(pk=evento.pk).update(
        criado_em=timezone.now() - timedelta(hours=25)
    )
    _login(client, chefe_obras)
    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')
    assert 'text-warning-text">Enviada em' in html
```

Espelhar os dois testes para `fila_atendimento` (`req_autorizada_view` como base, evento `EventoTimeline.AUTORIZACAO_TOTAL`, checar `Autorizada em` em vez de `Enviada em`) — nomear `test_fila_atendimento_timestamp_recente_sem_tom_de_warning` e `test_fila_atendimento_timestamp_com_mais_de_24h_ganha_tom_de_warning`.

- [ ] **Step 2: Escrever os testes de view (saldo)**

```python
@pytest.mark.django_db
def test_fila_autorizacao_saldo_insuficiente_mostra_badge(
    client, chefe_obras, solicitante, setor_obras, material_sem_saldo
):
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-8103',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req, material=material_sem_saldo, quantidade_solicitada=1,
    )
    _login(client, chefe_obras)
    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')
    assert 'Saldo insuficiente' in html


@pytest.mark.django_db
def test_fila_autorizacao_saldo_suficiente_nao_mostra_badge(
    client, chefe_obras, req_enviada_solicitante, material_disponivel
):
    ItemRequisicao.objects.create(
        requisicao=req_enviada_solicitante,
        material=material_disponivel,
        quantidade_solicitada=1,
    )
    _login(client, chefe_obras)
    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')
    assert 'Saldo insuficiente' not in html
```

Espelhar para `fila_atendimento` com `req_autorizada_view`/`material_sem_saldo` (trocar o item do fixture existente, ou criar novo item numa segunda requisição — usar o mesmo padrão de fixture inline do Step 1).

- [ ] **Step 3: Rodar e confirmar falha**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "timestamp_recente or timestamp_com_mais_de_24h or saldo_insuficiente_mostra_badge or saldo_suficiente_nao_mostra_badge" -v`
Expected: FAIL (nenhum tom condicional, nenhum badge ainda existe).

- [ ] **Step 4: Implementar os helpers em views.py**

No topo do bloco "Fila de autorização — lista" (`apps/requisicoes/views.py`, antes de `PAGINA_MINHAS_REQUISICOES_TAMANHO` na linha 748), adicionar import e constante:

```python
from datetime import timedelta

from django.utils import timezone

from apps.requisicoes.selectors import saldo_insuficiente_por_requisicoes  # junto aos demais imports de selectors já existentes no topo do arquivo

LIMIAR_IDADE_FILA = timedelta(hours=24)


def _marcar_idade_antiga(requisicoes, campo_data: str) -> None:
    """`req.data_antiga = True` quando `campo_data` passou de 24h corridas.

    Limiar único (#194): o timestamp muda de tom neutro (`text-text-tertiary`)
    pra warning (`text-warning-text`, o mesmo token de `quantidade.html`) —
    sem escalada em múltiplos níveis, decisão do shape da issue.
    """
    agora = timezone.now()
    for req in requisicoes:
        valor = getattr(req, campo_data)
        req.data_antiga = bool(valor and agora - valor > LIMIAR_IDADE_FILA)


def _marcar_saldo_insuficiente(requisicoes) -> None:
    """`req.saldo_insuficiente` via batch único pra página inteira (Task 2)."""
    mapa = saldo_insuficiente_por_requisicoes([r.pk for r in requisicoes])
    for req in requisicoes:
        req.saldo_insuficiente = mapa.get(req.pk, False)
```

Nota: se `apps.requisicoes.selectors` já for importado com outro alias no topo do arquivo (confirmar com `rg "from apps.requisicoes.selectors import" apps/requisicoes/views.py`), adicionar `saldo_insuficiente_por_requisicoes` a esse import existente em vez de duplicar a linha.

- [ ] **Step 5: Chamar os helpers nas duas views**

Em `fila_autorizacao_view` (linha 822, logo após `page_obj = paginar(...)`):
```python
    page_obj = paginar(request, requisicoes, per_page=PAGINA_FILA_TAMANHO)
    _marcar_idade_antiga(page_obj.object_list, 'enviada_em')
    _marcar_saldo_insuficiente(page_obj.object_list)
```

Em `fila_atendimento_view` (linha 927, mesmo ponto):
```python
    page_obj = paginar(request, requisicoes, per_page=PAGINA_FILA_TAMANHO)
    _marcar_idade_antiga(page_obj.object_list, 'autorizada_em')
    _marcar_saldo_insuficiente(page_obj.object_list)
```

- [ ] **Step 6: Templates — fila_autorizacao.html**

Trocar o bloco (linhas 22-52) de:
```django
        <div>
          <h2 class="break-words text-sm font-semibold text-text-primary">
            ...
          </h2>
          {% if req.enviada_em %}
            <p class="mt-1 text-xs text-text-tertiary">Enviada em {{ req.enviada_em|date:"d/m/Y H:i" }}</p>
          {% endif %}
        </div>
```
por (header agora segue o mesmo padrão `flex-col xl:flex-row` de `fila_atendimento.html`, exigido por DESIGN.md §Layout ao introduzir um segundo elemento no cabeçalho):
```django
        <div class="flex flex-col gap-2 xl:flex-row xl:items-start xl:justify-between xl:gap-3">
          <div class="min-w-0">
            <h2 class="break-words text-sm font-semibold text-text-primary">
              ...
            </h2>
            {% if req.enviada_em %}
              <p class="mt-1 text-xs {% if req.data_antiga %}text-warning-text{% else %}text-text-tertiary{% endif %}">Enviada em {{ req.enviada_em|date:"d/m/Y H:i" }}</p>
            {% endif %}
          </div>
          {% if req.saldo_insuficiente %}
            <span class="shrink-0">
              {% include "components/badge.html" with variant="amber" label="Saldo insuficiente" prefixo_sr="Saldo: " %}
            </span>
          {% endif %}
        </div>
```
(o `<h2>...</h2>` interno permanece byte-a-byte igual ao original — só a estrutura em volta muda.)

- [ ] **Step 7: Templates — fila_atendimento.html**

No `partialdef corpo_cartao` (linha 94-100), trocar:
```django
  <span class="shrink-0">
    {% if req.estado == 'autorizada' %}
      {% include "components/badge.html" with variant="blue" label="Autorizada" prefixo_sr="Estado: " %}
    {% else %}
      {% include "components/badge.html" with variant="teal" label="Pronta para retirada" prefixo_sr="Estado: " %}
    {% endif %}
  </span>
```
por:
```django
  <span class="shrink-0 flex flex-col items-end gap-1.5">
    {% if req.estado == 'autorizada' %}
      {% include "components/badge.html" with variant="blue" label="Autorizada" prefixo_sr="Estado: " %}
    {% else %}
      {% include "components/badge.html" with variant="teal" label="Pronta para retirada" prefixo_sr="Estado: " %}
    {% endif %}
    {% if req.saldo_insuficiente %}
      {% include "components/badge.html" with variant="amber" label="Saldo insuficiente" prefixo_sr="Saldo: " %}
    {% endif %}
  </span>
```
E a linha 91:
```django
    {% if req.autorizada_em %}
      <p class="mt-1 text-xs text-text-tertiary">Autorizada em {{ req.autorizada_em|date:"d/m/Y H:i" }}</p>
    {% endif %}
```
por:
```django
    {% if req.autorizada_em %}
      <p class="mt-1 text-xs {% if req.data_antiga %}text-warning-text{% else %}text-text-tertiary{% endif %}">Autorizada em {{ req.autorizada_em|date:"d/m/Y H:i" }}</p>
    {% endif %}
```

- [ ] **Step 8: Rodar e confirmar que os testes das Steps 1-2 passam**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "timestamp_recente or timestamp_com_mais_de_24h or saldo_insuficiente_mostra_badge or saldo_suficiente_nao_mostra_badge" -v`
Expected: todos PASS.

- [ ] **Step 9: Rodar a suíte completa de views de fila (regressão)**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "fila_autorizacao or fila_atendimento" -v`
Expected: todos PASS (nenhum teste pré-existente quebrado pela mudança de estrutura do cabeçalho do cartão).

- [ ] **Step 10: Rodar a lane Navegador (gate obrigatório — mudança de markup de listagem)**

Run: `make test-navegador`
Expected: PASS. Se algum caso de `test_navegador_ordem_foco.py` ou `test_navegador_contraste.py` tocar os cartões de fila, conferir manualmente que o novo `<span>` de badges não quebra a ordem de tabulação a 375px (o `<span>` não é focável — não deveria).

- [ ] **Step 11: Commit**

```bash
git add apps/requisicoes/views.py apps/requisicoes/templates/requisicoes/fila_autorizacao.html apps/requisicoes/templates/requisicoes/fila_atendimento.html apps/requisicoes/tests/test_views.py
git commit -m "feat(#194): sinal de idade e saldo no cartão das filas de trabalho"
```

---

### Task 4: Ordenação alternativa por saldo (ambas) e setor (só atendimento)

**Decisões do shape:** mecânica é reload de página via querystring canônica (`apps/core/querystring.py`), sem swap HTMX parcial; "ordenar por setor" só existe em `fila_atendimento` (multi-setor) — `fila_autorizacao` é escopada a um único setor, o controle não aparece lá; a ordenação alternativa nunca substitui o FIFO — ausência de `?ordenar=` volta ao comportamento de hoje, sem nenhuma query extra.

**Files:**
- Modify: `apps/requisicoes/views.py`
- Modify: `apps/requisicoes/templates/requisicoes/fila_autorizacao.html`
- Modify: `apps/requisicoes/templates/requisicoes/fila_atendimento.html`
- Test: `apps/requisicoes/tests/test_views.py`

**Interfaces:**
- Consumes: `saldo_insuficiente_por_requisicoes` (Task 2); `apps.core.querystring.caminho_canonico`/`querystring_ja_canonica` (já existem, `apps/core/querystring.py`).
- Produces: nenhuma interface nova consumida por outra task.

- [ ] **Step 1: Escrever os testes de contrato HTTP**

Em `apps/requisicoes/tests/test_views.py`, perto de `test_fila_paginacao_preserva_ordem_do_selector` (linha ~4900):

```python
@pytest.mark.django_db
def test_fila_autorizacao_ordenar_saldo_lista_insuficientes_primeiro(
    client, chefe_obras, solicitante, setor_obras, material_disponivel, material_sem_saldo
):
    req_ok = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO, numero_publico='REQ-2026-8201',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req_ok, material=material_disponivel, quantidade_solicitada=1,
    )
    req_insuficiente = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO, numero_publico='REQ-2026-8202',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req_insuficiente, material=material_sem_saldo, quantidade_solicitada=1,
    )
    _login(client, chefe_obras)

    html = client.get(
        reverse('requisicoes:autorizacoes'), {'ordenar': 'saldo'}
    ).content.decode('utf-8')

    assert html.index('REQ-2026-8202') < html.index('REQ-2026-8201')


@pytest.mark.django_db
def test_fila_autorizacao_sem_ordenar_mantem_fifo(
    client, chefe_obras, solicitante, setor_obras, material_disponivel, material_sem_saldo
):
    """Ausência de `?ordenar=` não muda em nada o comportamento de hoje."""
    req_antiga = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO, numero_publico='REQ-2026-8203',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req_antiga, material=material_sem_saldo, quantidade_solicitada=1,
    )
    req_nova = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO, numero_publico='REQ-2026-8204',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req_nova, material=material_disponivel, quantidade_solicitada=1,
    )
    _login(client, chefe_obras)

    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')

    # FIFO por `atualizado_em`: quem foi criado primeiro aparece primeiro,
    # mesmo sendo a requisição com saldo insuficiente.
    assert html.index('REQ-2026-8203') < html.index('REQ-2026-8204')


@pytest.mark.django_db
def test_fila_atendimento_ordenar_setor_agrupa_por_nome_do_setor(
    client, aux_almoxarifado, solicitante, setor_obras, setor_ti, material_disponivel
):
    req_ti = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA, numero_publico='REQ-2026-8301',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_ti,
    )
    ItemRequisicao.objects.create(
        requisicao=req_ti, material=material_disponivel, quantidade_solicitada=1,
    )
    req_obras = Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA, numero_publico='REQ-2026-8302',
        criador=solicitante, beneficiario=solicitante, setor_beneficiario=setor_obras,
    )
    ItemRequisicao.objects.create(
        requisicao=req_obras, material=material_disponivel, quantidade_solicitada=1,
    )
    _login(client, aux_almoxarifado)

    html = client.get(
        reverse('requisicoes:atendimentos'), {'ordenar': 'setor'}
    ).content.decode('utf-8')

    # "Obras" < "TI" alfabeticamente.
    assert html.index('REQ-2026-8302') < html.index('REQ-2026-8301')


@pytest.mark.django_db
def test_fila_autorizacao_nao_mostra_controle_de_ordenar_por_setor(
    client, chefe_obras, req_enviada_solicitante
):
    """Decisão do shape: `fila_autorizacao` é de um único setor, sem o controle."""
    _login(client, chefe_obras)
    html = client.get(reverse('requisicoes:autorizacoes')).content.decode('utf-8')
    assert 'ordenar=setor' not in html
```

Ajustar `setor_ti` para o nome real da fixture em `conftest.py` (confirmar com `rg "def setor_ti" apps/requisicoes/tests/conftest.py`) antes de rodar.

- [ ] **Step 2: Rodar e confirmar falha**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "ordenar_saldo or sem_ordenar_mantem_fifo or ordenar_setor or controle_de_ordenar_por_setor" -v`
Expected: FAIL (`?ordenar=` ainda não existe; `assert ... not in html` passa por acidente, mas os outros 3 falham).

- [ ] **Step 3: Constante de ordem canônica e ordenação em `fila_autorizacao_view`**

Em `apps/requisicoes/views.py`, perto de `PAGINA_FILA_TAMANHO` (linha 749):
```python
ORDEM_QUERYSTRING_FILA = ('busca', 'ordenar')
```

Substituir o corpo de `fila_autorizacao_view` (linhas 808-835) por:
```python
@login_required
@require_GET
def fila_autorizacao_view(request):
    """Lista requisições aguardando autorização no escopo da chefia."""
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_ver_fila_autorizacao(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    # URL é fonte de verdade do recorte (issue #152): `?ordenar=` inválido ou
    # redundante redireciona pra forma canônica antes de montar a página.
    if not request.htmx and not querystring_ja_canonica(
        request, ordem_chaves=ORDEM_QUERYSTRING_FILA
    ):
        return redirect(caminho_canonico(request, ordem_chaves=ORDEM_QUERYSTRING_FILA))

    busca = request.GET.get('busca', '').strip()
    ordenar = request.GET.get('ordenar', '')
    requisicoes_qs = filtrar_por_busca_simples(fila_autorizacao(request.user.pk), busca)

    if ordenar == 'saldo':
        # Saldo é calculado em Python em todo o projeto (`saldos_por_materiais`)
        # — ordenar por ele em SQL exigiria portar esse cálculo pra
        # Subquery/annotate agregado, que não existe hoje. A fila cabe em
        # memória (escala municipal, não milhões de linhas): materializar o
        # recorte filtrado inteiro e reordenar em Python, preservando FIFO
        # como critério de desempate (sort estável), é a opção mais simples
        # que não muda a paginação do que já existe.
        requisicoes_lista = list(requisicoes_qs)
        mapa_saldo = saldo_insuficiente_por_requisicoes(
            [r.pk for r in requisicoes_lista]
        )
        requisicoes_lista.sort(key=lambda r: 0 if mapa_saldo.get(r.pk, False) else 1)
        page_obj = paginar(request, requisicoes_lista, per_page=PAGINA_FILA_TAMANHO)
    else:
        page_obj = paginar(request, requisicoes_qs, per_page=PAGINA_FILA_TAMANHO)

    _marcar_idade_antiga(page_obj.object_list, 'enviada_em')
    _marcar_saldo_insuficiente(page_obj.object_list)
    return render(
        request,
        'requisicoes/fila_autorizacao.html',
        {
            'page_obj': page_obj,
            'requisicoes': page_obj.object_list,
            'querystring_filtros': querystring_sem_page(request.GET),
            'busca': busca,
            'ordenar': ordenar,
        },
    )
```

- [ ] **Step 4: Mesma mecânica em `fila_atendimento_view`, com o ramo `setor`**

Substituir o corpo de `fila_atendimento_view` (linhas 913-940) por:
```python
@login_required
@require_GET
def fila_atendimento_view(request):
    """Lista requisições autorizadas/prontas para almoxarifado."""
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_ver_fila_atendimento(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    if not request.htmx and not querystring_ja_canonica(
        request, ordem_chaves=ORDEM_QUERYSTRING_FILA
    ):
        return redirect(caminho_canonico(request, ordem_chaves=ORDEM_QUERYSTRING_FILA))

    busca = request.GET.get('busca', '').strip()
    ordenar = request.GET.get('ordenar', '')
    requisicoes_qs = filtrar_por_busca_simples(fila_atendimento(request.user.pk), busca)

    if ordenar == 'saldo':
        requisicoes_lista = list(requisicoes_qs)
        mapa_saldo = saldo_insuficiente_por_requisicoes(
            [r.pk for r in requisicoes_lista]
        )
        requisicoes_lista.sort(key=lambda r: 0 if mapa_saldo.get(r.pk, False) else 1)
        page_obj = paginar(request, requisicoes_lista, per_page=PAGINA_FILA_TAMANHO)
    elif ordenar == 'setor':
        # SQL puro — ao contrário de `saldo`, não depende de cálculo Python.
        # Só existe em atendimento: autorização é escopada a um único setor
        # (`fila_autorizacao` filtra por `ator.setor_chefiado`), então ordenar
        # por setor lá seria no-op — decisão do shape da issue.
        requisicoes_qs = requisicoes_qs.order_by(
            'setor_beneficiario__nome', 'atualizado_em', 'criado_em', 'id'
        )
        page_obj = paginar(request, requisicoes_qs, per_page=PAGINA_FILA_TAMANHO)
    else:
        page_obj = paginar(request, requisicoes_qs, per_page=PAGINA_FILA_TAMANHO)

    _marcar_idade_antiga(page_obj.object_list, 'autorizada_em')
    _marcar_saldo_insuficiente(page_obj.object_list)
    return render(
        request,
        'requisicoes/fila_atendimento.html',
        {
            'page_obj': page_obj,
            'requisicoes': page_obj.object_list,
            'querystring_filtros': querystring_sem_page(request.GET),
            'busca': busca,
            'ordenar': ordenar,
        },
    )
```

- [ ] **Step 5: Import de `caminho_canonico`/`querystring_ja_canonica` e `redirect`**

Conferir com `rg -n "^from django.shortcuts import|from apps.core.querystring import" apps/requisicoes/views.py`. Se `redirect` já vier de `django.shortcuts`, só falta adicionar:
```python
from apps.core.querystring import caminho_canonico, querystring_ja_canonica
```
(mesmo padrão de import já usado por `historico_requisicoes_view`, linha 46 do arquivo — reaproveitar a linha existente se já importar as duas funções.)

- [ ] **Step 6: Templates — controle de ordenação em `fila_autorizacao.html`**

Depois de `{% include "components/ordenacao_data.html" ... %}` (linha 16), adicionar:
```django
  <div class="mb-3 flex justify-end">
    {% if ordenar == 'saldo' %}
      {% include "components/button.html" with variant="secondary" label="Ordem padrão (mais antiga primeiro)" href=url_lista aria_label="Voltar à ordem padrão da fila" %}
    {% else %}
      {% url 'requisicoes:autorizacoes' as url_lista_saldo %}
      {% include "components/button.html" with variant="secondary" label="Saldo insuficiente primeiro" href=url_lista_saldo|add:"?ordenar=saldo" aria_label="Ordenar pelas requisições com saldo insuficiente primeiro" %}
    {% endif %}
  </div>
```
`url_lista` já existe no template (linha 12, `{% url 'requisicoes:autorizacoes' as url_lista %}`) — reusar em vez de recriar.

- [ ] **Step 7: Templates — dois controles em `fila_atendimento.html`**

Mesmo ponto (linha 16), adicionar:
```django
  <div class="mb-3 flex flex-wrap justify-end gap-2">
    {% if ordenar == 'saldo' or ordenar == 'setor' %}
      {% include "components/button.html" with variant="secondary" label="Ordem padrão (mais antiga primeiro)" href=url_lista aria_label="Voltar à ordem padrão da fila" %}
    {% else %}
      {% include "components/button.html" with variant="secondary" label="Saldo insuficiente primeiro" href=url_lista|add:"?ordenar=saldo" aria_label="Ordenar pelas requisições com saldo insuficiente primeiro" %}
      {% include "components/button.html" with variant="secondary" label="Agrupar por setor" href=url_lista|add:"?ordenar=setor" aria_label="Ordenar as requisições agrupadas por setor" %}
    {% endif %}
  </div>
```
`url_lista` já existe (linha 12).

Nota de acessibilidade: usar `|add:"?ordenar=saldo"` funciona porque `url_lista` nestas duas telas nunca carrega querystring própria (é `{% url %}` puro). Se a busca estiver ativa (`?busca=...`), o clique no botão de ordenar **perde** o filtro de busca — aceitável para este plano (a issue não pede combinar busca+ordenar simultaneamente), mas documentar a limitação no PR.

- [ ] **Step 8: Rodar e confirmar que os testes da Step 1 passam**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "ordenar_saldo or sem_ordenar_mantem_fifo or ordenar_setor or controle_de_ordenar_por_setor" -v`
Expected: todos PASS.

- [ ] **Step 9: Rodar a suíte completa de fila (regressão — checar `test_fila_paginacao_preserva_ordem_do_selector`)**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "fila_autorizacao or fila_atendimento or fila_paginacao" -v`
Expected: todos PASS — em particular `test_fila_paginacao_preserva_ordem_do_selector` (linha 4900), que asserta que `?ordem=asc` (parâmetro antigo, não `?ordenar=`) não reordena a fila; confirmar que esse teste continua verde porque `ordem` e `ordenar` são chaves diferentes.

- [ ] **Step 10: Rodar a lane Navegador**

Run: `make test-navegador`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add apps/requisicoes/views.py apps/requisicoes/templates/requisicoes/fila_autorizacao.html apps/requisicoes/templates/requisicoes/fila_atendimento.html apps/requisicoes/tests/test_views.py
git commit -m "feat(#194): ordenação alternativa por saldo (ambas as filas) e setor (atendimento)"
```

---

### Task 5: Travessia por teclado (setas ↓/↑)

**Decisão do shape:** setas ↓/↑ (não j/k), Enter não precisa de JS extra (foco num `<a>` já ativa nativamente no Enter do navegador). Listener escopado ao container da lista — WCAG 2.1.4 satisfeito estruturalmente porque o listener só existe dentro do wrapper da grade de cartões, não em `document`.

**Files:**
- Create: `apps/core/static/core/js/travessia-fila.js`
- Modify: `apps/core/templates/base.html:25` (registra o script)
- Modify: `apps/requisicoes/templates/requisicoes/fila_autorizacao.html`
- Modify: `apps/requisicoes/templates/requisicoes/fila_atendimento.html`
- Test: `apps/requisicoes/tests/test_navegador_fila_teclado.py` (novo)

**Interfaces:**
- Consumes: nada.
- Produces: `Alpine.data('travessiaFila', ...)`, registrado globalmente em `alpine:init` — nome reservado, não reusar para outro propósito.

- [ ] **Step 1: Escrever o teste de navegador (falha esperada)**

Criar `apps/requisicoes/tests/test_navegador_fila_teclado.py`:

```python
"""Camada Navegador (ADR-0019) — travessia por teclado na fila (#194).

Critério de admissão: depende de foco real (`document.activeElement`) e de
evento de teclado real (`page.keyboard.press`) — não provável por atributo
estático no HTML renderizado.
"""

import pytest
from django.urls import reverse

from apps.core.tests.navegador import autenticar
from apps.requisicoes.models import EstadoRequisicao, ItemRequisicao, Requisicao

pytestmark = pytest.mark.navegador

MOBILE = {'width': 375, 'height': 812}


@pytest.fixture
def abrir_pagina(live_server, context, page):
    def _abrir(usuario, caminho):
        autenticar(live_server, context, usuario)
        page.goto(f'{live_server.url}{caminho}')
        return page

    return _abrir


@pytest.fixture
def duas_requisicoes_na_fila(db, solicitante, setor_obras, material_disponivel):
    reqs = []
    for numero in ('REQ-2026-8401', 'REQ-2026-8402'):
        req = Requisicao.objects.create(
            estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico=numero,
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        ItemRequisicao.objects.create(
            requisicao=req, material=material_disponivel, quantidade_solicitada=1,
        )
        reqs.append(req)
    return reqs


def test_seta_para_baixo_move_o_foco_para_o_proximo_cartao(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('[data-cartao-link]')

    links = page.locator('[data-cartao-link]')
    links.first.focus()
    primeiro_texto = page.evaluate('document.activeElement.textContent.trim()')

    page.keyboard.press('ArrowDown')
    segundo_texto = page.evaluate('document.activeElement.textContent.trim()')

    assert primeiro_texto != segundo_texto
    assert segundo_texto == links.nth(1).text_content().strip()


def test_seta_para_cima_no_primeiro_cartao_volta_para_o_ultimo(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('[data-cartao-link]')

    links = page.locator('[data-cartao-link]')
    links.first.focus()

    page.keyboard.press('ArrowUp')
    texto_atual = page.evaluate('document.activeElement.textContent.trim()')

    assert texto_atual == links.last.text_content().strip()


def test_seta_para_baixo_fora_do_container_nao_move_foco(
    abrir_pagina, chefe_obras, duas_requisicoes_na_fila
):
    """O listener é escopado ao container — o campo de busca não é afetado."""
    page = abrir_pagina(chefe_obras, reverse('requisicoes:autorizacoes'))
    page.wait_for_selector('#busca-autorizacoes')

    page.locator('#busca-autorizacoes').focus()
    page.keyboard.press('ArrowDown')
    id_do_ativo = page.evaluate('document.activeElement.id')

    assert id_do_ativo == 'busca-autorizacoes'
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `uv run pytest apps/requisicoes/tests/test_navegador_fila_teclado.py -v`
Expected: `test_seta_para_baixo_move_o_foco_para_o_proximo_cartao` e `test_seta_para_cima_no_primeiro_cartao_volta_para_o_ultimo` FAIL (nenhum listener existe ainda); `test_seta_para_baixo_fora_do_container_nao_move_foco` já passa por acidente (nada move foco nenhum).

- [ ] **Step 3: Criar o componente Alpine**

`apps/core/static/core/js/travessia-fila.js`:
```javascript
// Travessia por teclado nos cartões de fila (#194). Setas ↓/↑ movem o foco
// entre os links `[data-cartao-link]` dentro do wrapper que carrega
// `x-data="travessiaFila()"`. Enter não precisa de handler: o navegador já
// ativa um <a> focado nativamente — só a navegação por seta é comportamento
// novo. Escopado ao `$el` do componente (não a `document`), o que também
// cumpre WCAG 2.1.4: fora do container, as setas não fazem nada aqui.
document.addEventListener('alpine:init', () => {
  window.Alpine.data('travessiaFila', () => ({
    proximo() {
      this._mover(1)
    },
    anterior() {
      this._mover(-1)
    },
    _mover(direcao) {
      const links = Array.from(this.$el.querySelectorAll('[data-cartao-link]'))
      if (links.length === 0) return
      const atual = links.indexOf(document.activeElement)
      const proximoIndice =
        atual === -1
          ? direcao > 0
            ? 0
            : links.length - 1
          : (atual + direcao + links.length) % links.length
      links[proximoIndice].focus()
    },
  }))
})
```

- [ ] **Step 4: Registrar o script em base.html**

`apps/core/templates/base.html:25`, depois de `item_form_row.js`:
```html
  <script src="{% static 'core/js/item_form_row.js' %}" defer></script>
  <script src="{% static 'core/js/travessia-fila.js' %}" defer></script>
```

- [ ] **Step 5: Envolver a grade de cartões em `fila_autorizacao.html`**

Trocar (linhas 17-89):
```django
  {% include "components/table.html#cards_abertura" %}
    {% for req in requisicoes %}
      ...
    {% endfor %}
  </div>
```
por:
```django
  <div
    x-data="travessiaFila()"
    @keydown.arrow-down.prevent="proximo()"
    @keydown.arrow-up.prevent="anterior()"
  >
    {% include "components/table.html#cards_abertura" %}
      {% for req in requisicoes %}
        ...
      {% endfor %}
    </div>
  </div>
```
(o `{% for %}...{% endfor %}` interno permanece idêntico — só um `<div>` novo por fora do include, fechado depois do `</div>` que já fechava `cards_abertura`.)

- [ ] **Step 6: Mesma mudança em `fila_atendimento.html`**

Mesmo padrão (linhas 17-40), envolvendo o bloco `{% include "components/table.html#cards_abertura" %} ... {% endfor %} </div>` com o `<div x-data="travessiaFila()" ...>` / `</div>` externo.

- [ ] **Step 7: Rodar os testes de navegador e confirmar que passam**

Run: `uv run pytest apps/requisicoes/tests/test_navegador_fila_teclado.py -v`
Expected: 3 PASS.

- [ ] **Step 8: Rodar a lane Navegador inteira (regressão — Alpine novo pode colidir com outro `x-data`)**

Run: `make test-navegador`
Expected: PASS.

- [ ] **Step 9: Rodar a suíte de views de fila (regressão de markup)**

Run: `uv run pytest apps/requisicoes/tests/test_views.py -k "fila_autorizacao or fila_atendimento" -v`
Expected: PASS — em particular os testes que contam `<article class="relative rounded-xl border border-border">` (a wrapper `<div>` nova não deve alterar essa contagem).

- [ ] **Step 10: Checar `ruff`/`mypy` (JS não é coberto, mas os `.py`/`.html` tocados sim)**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy apps`
Expected: limpo.

- [ ] **Step 11: Commit**

```bash
git add apps/core/static/core/js/travessia-fila.js apps/core/templates/base.html apps/requisicoes/templates/requisicoes/fila_autorizacao.html apps/requisicoes/templates/requisicoes/fila_atendimento.html apps/requisicoes/tests/test_navegador_fila_teclado.py
git commit -m "feat(#194): travessia por teclado (setas) entre cartões das filas"
```

---

## Fora de escopo (confirmado pelo shape da issue)

- "Autorizar inline no cartão" — spin-off separado, decisão de UX própria.
- Multi-seleção / ação em lote / continuidade PRG pós-confirmação — spin-off separado.
- Placeholder do catálogo (`lista_materiais.html`) — usa string diferente, não entra.
- `css-build`: nenhuma classe Tailwind nova é introduzida por este plano (`text-warning-text`, `bg-warning-muted` etc. já existem em `quantidade.html`/`badge.html`) — não deve ser necessário rodar `make css-build`, mas confirmar com `grep` no `app.css` gerado antes de assumir isso no PR (ver `[[project_css_build_gate]]`).
