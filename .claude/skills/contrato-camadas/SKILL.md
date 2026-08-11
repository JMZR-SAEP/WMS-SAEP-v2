---
name: contrato-camadas
description: Contrato de camadas dos apps de domínio — onde cada coisa mora, assinatura de service, par de policy, exceções, transições, e quais módulos de apps/core reutilizar. Use ao escrever ou revisar qualquer código em apps/ (services, policies, selectors, views, forms, models, transitions), ao decidir em que camada algo vai, ou ao traduzir erro de domínio para HTTP.
user-invocable: false
---

# Contrato de camadas — WMS-SAEP

Resumo operacional. **Não é fonte de verdade** — se divergir dos documentos
abaixo, o documento vence e este arquivo está desatualizado.

## Fontes e a armadilha das emendas

| Assunto | Documento |
|---|---|
| Regra operacional detalhada | `docs/CONVENTIONS.md` |
| Layout e fronteiras de camada | `docs/adr/0004-arquitetura-em-camadas.md` |
| Contrato service/policy/exceção | `docs/adr/0011-contrato-services-policies-excecoes.md` |
| Estratégia de testes | `docs/adr/0010-estrategia-de-testes.md` |
| Autorização por papel | `docs/matriz-permissoes.md` |
| Invariantes de domínio | `docs/matriz-invariantes.md` |

⚠️ **ADR-0004 e ADR-0011 têm emendas de 2026-06-26 no final que substituem
trechos do corpo.** Ler só o começo do ADR entrega regra revogada. Os três
pontos revogados com mais frequência:

1. Policies **não** recebem `User` — recebem `PapelEfetivo` (ADR-0011 mostra
   `ator: User` no corpo; está superado).
2. `transitions.py` é keyed por `Operacao`, não por estado de origem.
3. A view **não** abre `transaction.atomic` para encadear services — isso é um
   service composto.

## Onde cada coisa mora

| Preciso de… | Camada |
|---|---|
| Campo, constraint, choice, property trivial | `models.py` |
| Mutar estado de domínio | `services.py` / `services/` |
| Orquestrar vários services numa transação | `services/composites.py` |
| Decidir se um papel pode fazer algo | `policies.py` |
| Listar/filtrar com escopo de visibilidade | `selectors.py` |
| Validar input de formulário | `forms.py` |
| Receber request, devolver response | `views.py` |
| Regra estado→estado | `transitions.py` |

Hierarquia: `View → Service composto → Services atômicos → Domínio`.
A view **seleciona** o caso de uso; nunca sequencia operações nem abre
transação.

## Service

```python
def autorizar_requisicao(*, ator_id: int, requisicao_id: int) -> Requisicao:
    ...
```

- Keyword-only obrigatório; recebe **IDs**, não instâncias ORM.
- Carrega entidades internamente com os `select_related` necessários.
- `transaction.atomic` quando escreve; o **composto** é o dono da transação e
  os atômicos não a reabrem.
- Ordem: `verificar_transicao_valida` → `exigir_pode_*` → efeitos → timeline.
- Notificação **só** em `transaction.on_commit`; nunca pré-condição da
  transição.
- Lança exceções de `apps.core.exceptions`; nunca exceção HTTP do Django.
- Retorna a entidade principal alterada, sem garantia de relações carregadas.
- Em `services/`: um módulo por **capability** (`ciclo_vida`, `cancelamento`,
  `atendimento`, `copia`, `composites`). Proibido `helpers.py`, `utils.py`,
  `commands.py`, `queries.py`. API pública reexportada em `__init__.py`.

## Policy

```python
def pode_autorizar_requisicao(papel: PapelEfetivo, requisicao: Requisicao) -> bool: ...

def exigir_pode_autorizar_requisicao(papel: PapelEfetivo, requisicao: Requisicao) -> None:
    if not pode_autorizar_requisicao(papel, requisicao):
        raise PermissaoNegada('Você não pode autorizar esta requisição.')
```

- `exigir_pode_*` **sempre** delega para `pode_*`; nunca reimplementa a regra.
- Policy não faz IO e não resolve identidade. `papel_efetivo(usuario)` é
  chamado **uma vez** pelo chamador e reutilizado — é um snapshot.
- Service chama `exigir_pode_*`; view/template pode chamar `pode_*` para
  renderização.

## Exceções → HTTP

| Exceção | severity | status |
|---|---|---|
| `PermissaoNegada` | error | 403 |
| `DadosInvalidos` | error | 422 |
| `EstadoInvalido` | warning | 409 |
| `ConflitoDominio` | warning | 409 |

Use `traduz_erro_dominio(exc)` — não escreva a tabela à mão na view.
`str(exc)` é o texto exibido: PT-BR, orientado ao usuário, sem termo técnico.
`IntegrityError` não é caminho normal; é última barreira de corrida, capturada
e relançada como `ConflitoDominio`.

Fluxo padrão de mutação: POST → service → `messages.*` → redirect (PRG). Em
HTMX use `htmx_redirect`, nunca fragment para transição de escrita.

## Módulos de `apps/core` a reutilizar

| Módulo | API |
|---|---|
| `apps/core/exceptions.py` | `ErroDominio`, `PermissaoNegada`, `EstadoInvalido`, `DadosInvalidos`, `ConflitoDominio` |
| `apps/core/presentation.py` | `ErroPresentation`, `traduz_erro_dominio` |
| `apps/core/http.py` | `HtmxHttpRequest`, `htmx_redirect`, `parse_data_iso`, `querystring_sem_page` |
| `apps/core/listagem.py` | `ResultadoListagem`, `paginar_com_filtros` |
| `apps/accounts/papeis.py` | `PapelEfetivo`, `papel_efetivo` |

Transições: `TRANSICOES: dict[Operacao, TransicaoRequisicao]`,
`verificar_transicao_valida`, `cancelamento_info` em
`apps/requisicoes/transitions.py`. `Operacao` é `TextChoices` em
`apps/requisicoes/models.py`. A UI consome
`selectors.acoes_disponiveis(papel, requisicao) -> frozenset[Operacao]`, não
condicionais de estado espalhadas.

## Regras que costumam ser violadas

- Models não importam services, não disparam caso de uso em `save()`, não
  geram timeline por signal.
- Mutação de saldo **só** em `estoque.services`, com `transaction.atomic` +
  `select_for_update` sobre `SaldoEstoque` em ordem determinística. Exceção
  única: função `*_bootstrap_exception` no `seed_dev`, marcada com
  `# SEED BOOTSTRAP EXCEPTION`.
- Form entrega **value object tipado** (ex.: `LinhaAtendimento`), nunca dict
  anônimo, e não chama service.
- A tabela de transições nunca codifica autorização: ela responde "permitida
  neste estado?", a policy responde "este papel pode?".
- Migrations são efêmeras: mudou model → `make setup`. Não crie migration à mão.

## Idioma

Domínio em PT-BR (models, fields, choices, services, policies, selectors,
funções). Superfície de framework em inglês onde o Django impõe (`is_active`,
`is_staff`, `USERNAME_FIELD`, nome de app). `verbose_name` e
`verbose_name_plural` sempre em PT-BR.
