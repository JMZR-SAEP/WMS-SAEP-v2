# ADR-0010 — Estratégia de testes

## Status

Aceita

## Contexto

O projeto tem models com constraints não triviais, políticas de autorização contextual derivadas de relações (ADR-0001), uma máquina de estados com 8 transições (ADR-0003), locking transacional (ADR-0005) e uma matriz de visibilidade por papel. Uma estratégia de testes vaga gera duplicação entre camadas, falsos negativos silenciosos e suítes frágeis difíceis de manter por humanos e agentes de IA.

Três riscos a evitar:
- **Undertesting**: views ou selectors sem testes → bugs de visibilidade silenciosos.
- **Overtesting**: policy matrix duplicada em service tests → falha em um lugar quebra N testes.
- **Testes na camada errada**: regra de autorização testada via HTTP → falha obscura.

## Decisão

Cada camada da arquitetura tem responsabilidade de teste própria e não duplica a das demais.

### Camadas e responsabilidades

```
Models    → invariantes estruturais e properties semânticas
Policies  → matriz de autorização por papel/contexto
Selectors → visibilidade e escopo de leitura por papel
Services  → orquestração, atomicidade, efeitos de transição
Views     → contrato HTTP: autenticação, autorização de acesso, renderização
Navegador → comportamento que só existe com layout, top layer e XHR reais
```

A camada Navegador foi acrescentada pela [ADR-0019](0019-camada-de-teste-de-navegador.md), que
define seu critério de admissão, seu escopo fechado e a fronteira dela com as duas lanes de front
que já existiam (varredura de marcação e asserção sobre HTML renderizado). Ela é excluída do comando
padrão de teste por marcador — ver ADR-0019 e `docs/ci-pipeline.md`.

### Testes de models

Cobrem:
- Uma violação por constraint não trivial (`UniqueConstraint` partial, `CheckConstraint`).
- Properties derivadas (`saldo_disponivel`, `divergente`).

Não cobrem:
- `CharField max_length`, `null`, `blank`, `verbose_name`, `ordering`, choices básicas — comportamento padrão do Django.
- `__str__` trivial.

### Testes de policies

- Chamam a função de policy diretamente (não via view nem service).
- Usam banco real (`@pytest.mark.django_db`) porque papéis efetivos são derivados de FK e queries (ADR-0001).
- Fixtures são mínimas e cirúrgicas — apenas os objetos necessários para a decisão da policy.
- Cobrem a matriz de permissão com: um caso positivo canônico e os negativos que protegem regras reais (papel errado, setor errado, estado errado se a policy valida estado).
- **Não** testam combinações cartesianas completas — apenas os negativos significativos.

### Testes de selectors

- Chamam a função de selector diretamente.
- Usam banco real.
- Criam datasets mínimos com objetos contrastantes: um que deve aparecer e um que não deve (por setor, papel, estado, rascunho de terceiro).
- Comparam conjuntos de IDs (`values_list("id", flat=True)`), não HTML.
- São a fonte principal da garantia de visibilidade. Views não duplicam essa matriz.

### Testes de services / transições

Anatomia mínima por transição canônica (3 testes):

```
1. Caminho feliz:
   - estado final correto
   - efeitos obrigatórios da transição (quantidade_autorizada, saldo_reservado, etc.)
   - timeline com evento correto, ator correto
   - ausência de efeitos indevidos, quando relevante

2. Estado de origem inválido:
   - exceção de estado inválido
   - estado permanece inalterado
   - nenhuma timeline nova
   - nenhum efeito colateral parcial

3. Permissão negada (um caso real de recusa, não a matriz completa):
   - exceção de permissão
   - estado permanece inalterado
   - nenhum efeito colateral parcial
```

Efeitos com ramificação própria (atendimento parcial, divergência de saldo) recebem testes extras além dos 3 mínimos. Timeline é validada no caminho feliz, não em teste isolado.

**Services não duplicam a matriz completa de políticas.** O teste de permissão negada usa um caso real mínimo para provar que o service respeita a política — não que sabe reproduzi-la.

### Testes de concorrência

A suíte **não** testa locking real por threads por padrão. O `select_for_update` + PostgreSQL é o mecanismo de serialização (ADR-0005) — confiado ao banco e ao Django, não reimplementado como teste de thread.

O que é testado sequencialmente:
- Após uma transição ser aplicada, a mesma transição recusada → estado permanece, sem timeline duplicada, sem efeito colateral duplicado.

Testes com `@pytest.mark.django_db(transaction=True)` e threads ficam para bugs de concorrência real confirmados, marcados como `@pytest.mark.slow @pytest.mark.concurrency`.

### Testes de views

Contrato por tipo:

**Views de leitura (GET):**
```
- sem login → 302 para login
- ator autorizado → 200 + template correto
- ator sem permissão → 403 ou redirect esperado
```

**Views de mutação (POST):**
```
- sem login → 302 para login
- ator sem permissão → 403/redirect + estado principal inalterado
- POST válido → redirect correto + evidência mínima de mutação (estado principal alterado)
```

Views **não** revalidam timeline, saldo, items ou efeitos internos já cobertos por service tests. Views **não** duplicam a matriz de selectors ou de policies.

Para objects sensíveis (detail view fora do escopo de visibilidade do ator): `404` para não revelar existência. Para ação proibida em objeto visível: `403`.

### Organização de arquivos

```
apps/<app>/tests/
  __init__.py
  conftest.py        # fixtures específicas do app
  test_models.py
  test_policies.py   # se o app tem policies
  test_selectors.py  # se o app tem selectors
  test_services.py   # se o app tem services
  test_views.py
```

`tests.py` (arquivo único) é convertido para pacote quando o app precisar de mais de um módulo de teste.

**Fixtures:**
- `conftest.py` raiz: entidades básicas transversais (`setor_almoxarifado`, `setor_obras`, `user_obras`, `chefe_obras`, etc.).
- `apps/<app>/tests/conftest.py`: cenários e objetos específicos do app (requisições em estados, saldos, materiais).
- `make_*` fixtures (função que retorna função): variações locais sem factory_boy.

**Não usar `factory_boy` nesta fase.** A dor atual é organização, não falta de framework. Reavaliar quando houver duplicação real de setup em 5+ modelos com campos obrigatórios extensos.

**Não usar `seed_dev` como fixture de teste.** Seed é ambiente local; teste cria o próprio cenário isolado.

## Consequências

Falhas são diagnósticas: uma falha em `test_policies.py` aponta para regra de autorização; em `test_selectors.py` aponta para escopo de visibilidade; em `test_services.py` aponta para orquestração. Não há busca de onde a regra foi quebrada.

A suíte de serviços cobre ~24 testes para as 8 transições canônicas, mais testes extras para ramificações. Sem duplicação de policy matrix nos services.

Fixtures de raiz compartilhadas: se uma fixture base mudar (ex: `setor_almoxarifado` ganhar campo obrigatório), múltiplos apps quebram ao mesmo tempo — sinal de que o change é estrutural, não de que a fixture está errada.

## Trade-off

Policy tests com banco real são mais lentos que unit tests sem banco, mas o papel efetivo derivado não pode ser validado de forma confiável sem persistência. Aceita-se o custo de tempo pelo ganho de fidelidade.

Não testar threads e não usar factory_boy são decisões revisáveis — não irreversíveis. O critério de revisão está documentado: bugs reais de concorrência ou duplicação concreta de setup em múltiplos modelos.
