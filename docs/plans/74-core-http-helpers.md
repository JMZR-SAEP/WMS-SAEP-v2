# Plano — Issue #74: apps/core/http.py + adoção de request.htmx

## Escopo

**Muda:**
- Novo módulo `apps/core/http.py` com 3 helpers puros de infraestrutura HTTP:
  - `htmx_redirect(request, url)` — PRG: 204 + `HX-Redirect` para HTMX; `redirect()` normal caso contrário.
  - `parse_data_iso(valor)` — `'YYYY-MM-DD'` → `date | None`; entrada inválida/vazia → `None`.
  - `querystring_sem_page(get_params)` — querystring atual sem `page`, para paginação com filtros preservados.
- Substituição de `request.headers.get('HX-Request') == 'true'` por `request.htmx` (bool nativo do `HtmxMiddleware`, já ativo em `config/settings/base.py:54`) nos 6 pontos identificados na issue.
- Remoção das 3 duplicações de helpers em `apps/requisicoes/views.py`, `apps/estoque/views.py`, `apps/notificacoes/views.py`, substituídas por import de `apps.core.http`.
- Testes unitários novos para os 3 helpers puros em `apps/core/tests/test_http.py` (módulo novo, sem cobertura própria ainda).

**Não muda:**
- Contrato PRG + HX-Redirect (status codes, headers) — comportamento HTTP idêntico ao atual.
- Nenhuma lógica de domínio (services/policies/selectors intocados).
- Templates, views de histórico (issue própria, fora de escopo), unificação de `historico_*_view`.
- `_voltar_url`, `_detalhe_context`, `_render_modal_erro`, `_render_detalhe` — helpers específicos de `requisicoes/views.py` que não são duplicados nos outros dois apps, permanecem onde estão.

## Decisão técnica: NÃO delegar em `django_htmx.http.HttpResponseClientRedirect`

A issue pede para "avaliar" a delegação. Inspecionado o código-fonte de `django_htmx.http` (versão instalada via `pyproject.toml`):

```python
class HttpResponseClientRedirect(HttpResponseRedirectBase):
    status_code = 200
    ...
```

`HttpResponseClientRedirect` responde com **status 200**, não 204. O critério de aceite da issue exige explicitamente "requisição HTMX de POST de transição → 204 + `HX-Redirect`". Delegar mudaria o contrato de status code (200 vs 204), o que é vedado pelos guardrails ("não alterar códigos de status", "mudar contrato PRG+HX-Redirect" está fora de escopo pelo próprio épico).

**Decisão:** manter implementação custom com `HttpResponse(status=204)` + header manual, apenas centralizada em `apps/core/http.py`. Documentar a decisão no docstring do helper.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/core/http.py` (novo) | 3 helpers: `htmx_redirect`, `parse_data_iso`, `querystring_sem_page` |
| `apps/core/tests/test_http.py` (novo) | testes unitários dos 3 helpers |
| `apps/requisicoes/views.py` | remove `_htmx_redirect` (linhas 84-90) e `_parse_data_iso_historico`/`_querystring_sem_page_historico` (linhas ~1146-1165); importa de `apps.core.http`; troca 4 ocorrências de `request.headers.get('HX-Request') == 'true'` (linhas ~86→removida, 870, 946, 1226) por `request.htmx` |
| `apps/estoque/views.py` | remove `_parse_data_iso`/`_querystring_sem_page` (linhas 78-93); importa de `apps.core.http`; troca 1 ocorrência de HX-Request (linha 179) por `request.htmx` |
| `apps/notificacoes/views.py` | remove `_htmx_redirect` (linhas 17-23); importa de `apps.core.http`; troca 1 ocorrência de HX-Request (linha 19, dentro do próprio helper removido) |

Todas as chamadas existentes (`_htmx_redirect(request, ...)` em ~25 pontos de `requisicoes/views.py`, 2 em `notificacoes/views.py`) continuam funcionando sem mudança de call site — apenas o import muda, já que a assinatura é preservada.

## Test strategy

- Suíte existente (`test_views.py` dos 3 apps) já cobre PRG+HX-Redirect para as transições afetadas — confirmado por inspeção de `apps/requisicoes/tests/test_views.py` (106KB, cobre os fluxos de cancelamento/recusa/etc. com client HTMX). **Não é necessário teste novo de comportamento HTTP** conforme o próprio critério de aceite da issue ("se a suíte já cobre... nenhum teste novo é obrigatório — verificar antes").
- Testes novos apenas para o módulo novo `apps/core/http.py` (unidade pura, sem apps consumidores):
  - `htmx_redirect`: request HTMX → 204 + header `HX-Redirect` == url; request normal → 302 + `Location` == url.
  - `parse_data_iso`: string ISO válida → `date`; `None`/`''`/string inválida → `None`.
  - `querystring_sem_page`: `QueryDict` com `page` e outros params → querystring sem `page`; sem `page` → idempotente.
- Rodar suíte completa antes e depois da refatoração para confirmar zero regressão (mesmo pass count).

## Invariantes relevantes (docs/design-acesso-rapido/matriz-invariantes.md)

- Contrato PRG + HX-Redirect (mensagens ao usuário) — preservado, ver decisão acima.
- Camadas ADR-0011 — `apps/core/http.py` é infraestrutura HTTP pura, sem import de models/services de domínio.

## Riscos

- Baixo: refactor mecânico, sem mudança de lógica de negócio.
- Risco principal é regressão silenciosa em call sites de `_htmx_redirect` fora dos 3 arquivos mapeados — mitigado por grep prévio (`_htmx_redirect`, `HX-Request`, `_parse_data_iso`, `_querystring_sem_page` restrito a `apps/**/*.py`), que confirmou apenas os 3 arquivos citados na issue contêm essas definições/usos.
- `request.htmx` depende do `HtmxMiddleware` estar ativo em todas as requisições relevantes — já confirmado ativo globalmente em `config/settings/base.py:54`, sem exclusões por app.
