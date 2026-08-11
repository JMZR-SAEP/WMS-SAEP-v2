---
name: nova-slice
description: Constrói uma fatia vertical completa de caso de uso — da regra de domínio até a tela — na ordem de camadas do ADR-0004, com TDD por camada. Use ao implementar uma nova operação de domínio ou tela.
disable-model-invocation: true
---

# Nova fatia vertical

Uma fatia atravessa todas as camadas de um caso de uso, não um arquivo por vez.
A ordem abaixo existe porque cada camada é pré-condição da seguinte: policy
antes de service, service antes de view, view antes de template.

Carregue `contrato-camadas` para as regras de cada camada. Aqui está só a
**ordem** e os pontos de parada.

## Fase 0 — Entender antes de escrever

Não abra editor antes de responder estas quatro perguntas:

1. **Qual operação de domínio?** Ela já existe em `TRANSICOES`
   (`apps/requisicoes/transitions.py`) ou é nova? Nova operação = nova entrada
   na tabela + novo membro em `Operacao`.
2. **Quem pode executá-la?** Ache a linha em `docs/matriz-permissoes.md` para
   os seis papéis. Se a ação não está na matriz, **pare e pergunte** — matriz
   e código não podem divergir por decisão sua.
3. **Que invariantes precisam valer?** `docs/matriz-invariantes.md`.
4. **É UI?** Então leia, nesta ordem: `.design/INFORMATION_ARCHITECTURE.md`,
   `.design/<area>/DESIGN_BRIEF.md` e `.design/TASKS.md`. Mantenha o escopo no
   brief referenciado. Se `.design/` conflitar com ADR, design system ou regra
   de domínio, **exponha o conflito antes de implementar**.

Escreva em uma frase o que a fatia faz e qual estado ela move. Se não couber
numa frase, são duas fatias.

## Fase 1 — Schema (só se necessário)

`models.py`: campo, constraint, choice, property simples. `verbose_name` e
`verbose_name_plural` em PT-BR.

Mexeu em `models`/schema → `/reset-schema`. Migration não se escreve à mão.

**Checkpoint:** `DJANGO_SETTINGS_MODULE=config.settings.dev uv run python manage.py makemigrations --check --dry-run` sai limpo.

## Fase 2 — Transição

Nova operação: adicione o membro em `Operacao` e a entrada em `TRANSICOES` com
`estados_origem` (conjunto), `estado_destino`, `evento_timeline`.

A tabela **não** codifica autorização — só "esta operação é permitida neste
estado?".

**Teste:** `test_transitions.py` — origem válida, origem inválida.

## Fase 3 — Policy (TDD)

Escreva `test_policies.py` **primeiro**, um caso por papel da linha da matriz,
incluindo os `Não`. Rode e veja falhar. Depois implemente o par
`pode_*` / `exigir_pode_*`.

Policy tests usam banco real (papéis derivam de FK/query) e chamam a policy
direto — não via view.

**Checkpoint:** a matriz de autorização está coberta aqui e **em nenhum outro
lugar**. Não replique em service tests nem em view tests.

## Fase 4 — Service (TDD)

Três testes por transição, sempre:

| Caso | Verifica |
|---|---|
| Caminho feliz | estado final + efeitos + evento de timeline |
| Estado inválido | levanta `EstadoInvalido` e **nenhuma escrita** ocorreu |
| Permissão negada | levanta `PermissaoNegada` e **nenhuma escrita** ocorreu |

Só então implemente o service. Se o caso de uso encadeia dois services, o
composto vai em `services/composites.py` e é o dono da `transaction.atomic`.

Mutação de saldo passa por `estoque.services` — nenhum outro app escreve saldo.

## Fase 5 — Selector

Leitura não trivial, fila ou escopo de visibilidade. `test_selectors.py`
compara **sets de IDs**, nunca HTML.

Listagem paginada com filtro: use `paginar_com_filtros` de
`apps/core/listagem.py`, não reinvente.

## Fase 6 — Form

Valida qualidade de input (tipo, obrigatoriedade, choices). Entrega **value
object tipado**, não dict anônimo, e não chama o service.

Invariante de domínio não mora aqui — mora no service.

## Fase 7 — View + URL

Fina: input → `papel_efetivo` uma vez → policy/service/selector → resposta.

- `ator_id=request.user.id`, nunca `request.user`.
- Exceção de domínio → `traduz_erro_dominio`.
- POST de mutação → `messages.*` + redirect (PRG). HTMX → `htmx_redirect`.
- Slug de URL em PT-BR.

`test_views.py` cobre contrato HTTP: exige login, exige permissão, smoke de
GET, e para POST de mutação **redirect + um estado principal**. Não replique
a matriz de policy nem a de selector aqui.

## Fase 8 — Template

Reutilize os componentes de `apps/core/templates/components/`: `button`,
`alert`, `badge`, `table`, `pagination`, `empty_state`, `form_field`, `modal`,
`autocomplete`, `filter_*`. Não escreva Tailwind cru onde existe componente —
`docs/design-system.md` e ADR-0008 mandam, e há teste de tokens semânticos
guardando isso.

Fragment HTMX é para leitura e interação auxiliar (GET). Nunca para transição
de escrita.

## Fase 9 — Fechar

Checklist de `docs/CONVENTIONS.md`:

- Caso de uso em service, view fina?
- Policy chamada por view **e** por service?
- Mutação dentro de `transaction.atomic`?
- Transição via `transitions.py`?
- Evento em `TimelineRequisicao`?
- Notificação só em `transaction.on_commit`?
- Teste de feliz, permissão negada e violação de invariante?

Depois rode `/gates`. Antes de abrir PR, considere os agents
`revisor-camadas` e — se a fatia tocou autorização — `auditor-permissoes`.

## Limites

- Uma fatia por vez. Não abra a próxima antes desta passar nos gates.
- Arquivos nascem com conteúdo: **não crie stubs vazios** para "preparar" a
  estrutura.
- Não promova `services.py` a pacote só porque a fatia é nova — só quando o
  volume justificar.
