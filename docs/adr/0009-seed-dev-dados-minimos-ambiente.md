# ADR-0009 — Estratégia de seed de dados mínimos para ambiente de desenvolvimento

## Status

Aceita

## Contexto

O ambiente local de desenvolvimento é descartável e efêmero (ver `AGENTS.md`). Para que um dev ou agente de IA possa operar o sistema sem passos manuais adicionais após `make setup`, é necessário um conjunto mínimo de dados canônicos: setores, usuários, materiais, estoque e saldo inicial.

Três abordagens foram consideradas:

- **Fixtures JSON** — geradas por `dumpdata`, versionadas. Ficam obsoletas rapidamente quando o schema evolui; acopladas ao estado do banco no momento da geração; difíceis de auditar e manter por agentes de IA.
- **Factories (`factory_boy`)** — adequadas para testes automatizados com dados arbitrários. Não servem para dados canônicos estáveis com identidades fixas.
- **Management command declarativo** (`seed_dev`) — dados fixos em constantes Python, convergente, idempotente e auditável.

## Decisão

Criar `apps/core/management/commands/seed_dev.py` como command declarativo e convergente para dados mínimos de ambiente local.

### Contrato do comando

```
seed_dev é declarativo e convergente.
Entidades canônicas declaradas neste arquivo são fonte de verdade.
Ao reexecutar o comando, campos gerenciados pelo seed são atualizados para refletir o estado declarado.
Conflitos com constraints semânticas são detectados antes da escrita e causam falha explícita.
Dados fora do escopo do seed não são apagados nem alterados.
```

### Proteção de ambiente

O comando só executa se ambas as condições forem satisfeitas:

```python
settings.DEBUG == True
os.environ.get("SEED_DEV_HABILITADO") == "true"
```

Qualquer violação levanta `CommandError` com instrução de uso. `DEBUG=True` sozinho não é suficiente — staging ou demo com DEBUG ativo não deve executar o seed acidentalmente. O Makefile encapsula o comando canônico: `make seed-dev`.

### Estratégia de escrita

Entidades canônicas usam `update_or_create` com chave natural estável:

- `Setor` → `codigo`
- `User` → `matricula`
- `UnidadeMedida` → `codigo` — as de `UNIDADES_CONHECIDAS` (ADR-0020)
- `Material` → `codigo`
- `Estoque` → `codigo`
- `SaldoEstoque` → `(estoque, material)` — **exceção de bootstrap** (ver abaixo)
- `SequenciaRequisicao` → `ano` — usa `get_or_create`, nunca reseta `ultimo_numero`

Antes de aplicar setores, o seed verifica conflito semântico da constraint `unico_setor_almoxarifado`: se existe setor com `classificacao=ALMOXARIFADO` e código diferente do declarado, o seed falha com `CommandError` antes de qualquer escrita.

### Exceção de bootstrap para `SaldoEstoque`

`estoque.services` é o único caminho autorizado para mutação operacional de saldo. O seed escreve `SaldoEstoque` diretamente via ORM como **exceção de bootstrap documentada**: o saldo inicial é pré-condição de ambiente, não evento de domínio. Não cria movimentação, não cria auditoria. A exceção está isolada em `_seed_saldos_iniciais_bootstrap_exception()` e documentada em `CONVENTIONS.md#seed-bootstrap-exceptions`. O `saldo_reservado` é sempre convergido para `0` no seed.

### Ordem de execução (fases declarativas)

```
1. Setores (sem chefe)
2. Usuários (vinculados a setores)
3. Chefias (Setor.chefe = usuário)
4. Vínculos auxiliares (VinculoAuxiliar)
5. Unidades de medida (antes dos materiais: `Material.unidade` é FK)
6. Materiais
7. Estoque
8. Saldos iniciais (bootstrap exception)
9. SequenciaRequisicao do ano corrente (get_or_create)
```

`Setor.chefe` nunca é atribuído durante `_seed_setores()`. Chefia é fase 3.

### Elenco canônico mínimo

```
Setores:
  ALMOX   — Almoxarifado   (classificacao=ALMOXARIFADO)
  OBRAS   — Obras          (classificacao=COMUM)

Usuários (matricula → setor):
  SUPER001  — Administrador (setor=null, is_staff=True, is_superuser=True)
  ALMOX001  — Chefe Almoxarifado     (setor=ALMOX, chefe de ALMOX)
  ALMOX002  — Auxiliar Almoxarifado  (setor=OBRAS, VinculoAuxiliar→ALMOX)
  OBRAS001  — Chefe de Obras         (setor=OBRAS, chefe de OBRAS)
  OBRAS002  — Auxiliar de Obras      (setor=OBRAS, VinculoAuxiliar→OBRAS)
  OBRAS003  — Usuário Obras          (setor=OBRAS, solicitante comum)

Vínculos auxiliares:
  ALMOX002 → ALMOX
  OBRAS002 → OBRAS

Materiais:
  MAT-001 — Papel A4              (un,   saldo_fisico=50)
  MAT-002 — Caneta esferográfica  (un,   saldo_fisico=10)
  MAT-003 — Fita crepe            (rolo, saldo_fisico=0)

Estoque:
  EST-PRINCIPAL — Estoque Principal
```

### Senha canônica

```python
SEED_DEV_SENHA_PADRAO = "senha@dev"
senha = os.environ.get("SEED_DEV_PASSWORD", SEED_DEV_SENHA_PADRAO)
```

O seed reaaplica a senha a cada execução (convergência). Usuários canônicos precisam de senha funcional para login via UI. `set_unusable_password` não é usado. A senha padrão é pública e destina-se exclusivamente ao ambiente de desenvolvimento.

### Fora do escopo do seed

```
Requisicao, ItemRequisicao, TimelineRequisicao — dados transacionais
Movimentações de estoque artificiais
Incremento de SequenciaRequisicao.ultimo_numero
numero_publico artificial
```

### Separação com factories

`seed_dev` e factories (`factory_boy`) são completamente independentes:

- Factories geram dados arbitrários e válidos para testes automatizados.
- `seed_dev` declara dados canônicos e estáveis para ambiente local.
- `seed_dev` não importa `factory_boy`.
- Factories não importam constantes do `seed_dev`.
- Duplicação pequena entre os dois é aceitável quando preserva clareza de intenção.

## Consequências

O ambiente local converge para um estado previsível e auditável após `make seed-dev`. Agentes de IA podem operar o sistema assumindo que o elenco e catálogo canônicos estão presentes. A rerexecução é segura: entidades existentes são atualizadas, não duplicadas.

O superuser técnico (`SUPER001`) não é persona de domínio — não deve ser usado como ator em fluxos operacionais. Existe apenas para acesso ao admin e inspeção técnica.

`SequenciaRequisicao` pode já ser criada pelo service na primeira requisição (ADR-0003). O seed a pré-cria para visibilidade e para garantir que o ano corrente está preparado mesmo antes da primeira operação.

## Trade-off

`update_or_create` como fonte de verdade implica que alterações manuais em dados canônicos são revertidas ao rodar o seed. Isso é desejável para reprodutibilidade, mas exige que mudanças intencionais nos dados canônicos sejam feitas no próprio `seed_dev.py`, não no banco. Aceita-se esse custo em troca de estado de ambiente determinístico e navegável por humanos e agentes de IA.
