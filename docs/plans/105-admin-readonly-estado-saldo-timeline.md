# Plano — Admin não escreve estado/quantidade/saldo/timeline direto (#105)

## Escopo

Fechar as quatro brechas em que o Django admin permite escrever, à mão, campos
governados pela máquina de estados, pelo ledger e pela trilha de auditoria —
contornando services, policies e `MovimentacaoEstoque`.

O admin permanece **válvula de emergência**: nada aqui remove telas, oculta
modelos ou restringe leitura. Em todos os cinco admins tocados,
`has_view_permission` fica intacto — changelist e change view continuam abrindo
para quem o Django já autoriza, e o superusuário segue enxergando tudo que
precisa para diagnosticar.

A regra que emerge, e que o plano aplica de forma consistente: **model cujo
estado é derivado da máquina de estados ou do ledger é somente-leitura no
admin**. Requisição (o agregado-raiz) continua editável nos campos que não são
derivados.

**Vai mudar:**

- `apps/requisicoes/admin.py`
  - `RequisicaoAdmin.readonly_fields` ganha `estado`. Add/change/delete do
    agregado-raiz **permanecem** — é a válvula de emergência.
  - `ItemRequisicaoAdmin` — `readonly_fields` com as três quantidades e
    `has_add_permission`/`has_change_permission`/`has_delete_permission` fixos
    em `False`.
  - `ItemRequisicaoInline` — mesmos `readonly_fields`, `extra = 0`,
    `can_delete = False` e as três permissões fixas em `False`.
  - `TimelineRequisicaoAdmin` — as três permissões fixas em `False`.
- `apps/estoque/admin.py`
  - `SaldoEstoqueAdmin` — `readonly_fields` ganha `saldo_fisico` e
    `saldo_reservado`, ao lado de `saldo_disponivel`/`divergente`; e as três
    permissões passam a `False`.
- `apps/requisicoes/tests/test_admin.py` — arquivo **novo**.
- `apps/estoque/tests/test_admin.py` — arquivo já existente (#102, #104); ganha
  um bloco para `SaldoEstoqueAdmin` e uma linha no docstring do módulo.

**Não vai mudar:**

- Leitura, em nenhum dos cinco admins. `has_view_permission` não é sobrescrito.
  Um `ModelAdmin` com `has_change_permission=False` e `has_view_permission`
  default renderiza a change view em modo somente-leitura — exatamente o que se
  quer para item, saldo e timeline.
- `RequisicaoAdmin` add/change/delete. `criador`, `beneficiario`,
  `setor_beneficiario` e `observacao_geral` seguem editáveis: nenhum é derivado
  de ledger ou de transição, e é neles que a válvula de emergência opera. Só
  `estado` sai do formulário.
- `MovimentacaoEstoqueAdmin`. A ADR-0015 já garante imutabilidade no model
  (`save`/`delete` levantam), e o issue trata esse admin como já protegido.
  Registrado aqui como observação para triagem futura, sem agir: a ADR-0015
  (§ Riscos) justifica a garantia app-level pela "ausência de UI/admin de
  edição", mas `MovimentacaoEstoqueAdmin` está registrado com add/change/delete
  — hoje o efeito é um erro 500 em vez de um 403, feio mas sem violar LED-05.
  Fora do escopo deste issue.
- `Requisicao.numero_publico`, `criado_em`, `atualizado_em` — já readonly.
- Services, policies, selectors, transitions, forms, views, templates. Nenhum
  caminho de domínio é tocado: a mudança é inteiramente na camada admin.
- Schema, models, migrations, seed. Sem mudança estrutural → sem `make setup`.
- Refinamentos cosméticos de admin (fieldsets, list_display, filtros). O issue
  os deixa explicitamente em pré-produção.

### Por que o inline entra no escopo

O issue aponta `ItemRequisicaoAdmin` (`apps/requisicoes/admin.py:39`), mas o
critério de aceite é "nenhum dos campos acima é editável pelo admin", e
`ItemRequisicaoInline` (linha 10) expõe **os mesmos três campos** dentro da
change view de `Requisicao`, que é o caminho que o superusuário sob estresse
realmente percorre — ele abre a requisição presa, não a tela avulsa de item.
Deixar o inline de fora fecharia a porta e manteria a janela aberta.

### Por que `ItemRequisicao` e `SaldoEstoque` ficam somente-leitura por inteiro

`readonly_fields` nos campos citados pelo issue não basta, por três razões
concretas — e as meias-medidas deixariam exatamente o buraco que o issue quer
fechar.

**Add não fica "neutro", fica quebrado.** `ItemRequisicao.quantidade_solicitada`
é `DecimalField` **NOT NULL, sem `default`**, com `CheckConstraint
item_solicitada_positiva (> 0)`. Em `readonly_fields`, `ModelAdmin.get_form` o
joga em `exclude`, o `ModelForm` deixa de tê-lo e o save cai em `IntegrityError`.
Manter o add entregaria uma tela que estoura 500 em vez de uma tela que nega.
Em `SaldoEstoque` o add não estoura (ambos os saldos têm `default=0`), mas cria
uma linha de saldo **sem nenhuma `MovimentacaoEstoque` correspondente** — é
precisamente a mutação sem ledger que LED-01/LED-02 proíbem.

**Os campos restantes são tão derivados quanto os citados.** Em `ItemRequisicao`
sobrariam editáveis `requisicao`, `material` e `justificativa_entrega`; em
`SaldoEstoque`, `estoque` e `material`. Trocar o `material` de um item já
autorizado deixa a reserva pendurada no material antigo; trocar o `material` de
uma linha de saldo reatribui o saldo inteiro. Ambos quebram LED-02 de forma mais
silenciosa que escrever a quantidade à mão.

**Delete é a mesma escrita, pelo outro lado.** Apagar um item pelo inline pode
esvaziar uma requisição — violação direta de REQ-05 no banco, sem passar por
service nem por timeline. Apagar uma linha de `SaldoEstoque` deixa o ledger
apontando para um saldo que não existe. E, com o add já negado, manter o delete
daria ao superusuário a capacidade de destruir sem a de reconstruir — pior que
fechar os dois.

Item e saldo passam então a ter o mesmo tratamento de `TimelineRequisicao`:
add/change/delete negados, leitura preservada. Itens nascem de
`criar_requisicao`/`copiar_requisicao` e mudam por `autorizar`/`atender`; linhas
de saldo nascem da importação SCPI e mudam pelos services do ledger. Nenhum dos
dois tem caminho legítimo pelo admin.

`readonly_fields` **continua sendo declarado** nos dois, apesar de redundante
com `has_change_permission=False`: é o critério de aceite literal do issue, é o
que os testes de introspecção pedem, e sobrevive caso alguém reabra
`has_change_permission` no futuro sem revisar os campos.

## Arquivos a alterar

Nenhuma mudança abaixo foi aplicada ainda: na altura deste commit o repositório
contém apenas este plano, e os quatro admins seguem com as brechas descritas.

| Arquivo | Ação prevista |
|---|---|
| `apps/requisicoes/admin.py` | `readonly_fields` com `estado` em `RequisicaoAdmin`; `ItemRequisicaoAdmin` e `ItemRequisicaoInline` somente-leitura (3 quantidades em `readonly_fields` + add/change/delete negados); `TimelineRequisicaoAdmin` com add/change/delete negados |
| `apps/estoque/admin.py` | `SaldoEstoqueAdmin` somente-leitura: `saldo_fisico`/`saldo_reservado` em `readonly_fields` + add/change/delete negados |
| `apps/requisicoes/tests/test_admin.py` | Arquivo novo — cobertura dos três admins de requisições |
| `apps/estoque/tests/test_admin.py` | Acrescentar bloco de `SaldoEstoqueAdmin` e atualizar o docstring do módulo, hoje restrito a #102/#104 |

## Implementação

```python
# apps/requisicoes/admin.py
QUANTIDADES_READONLY = (
    'quantidade_solicitada',
    'quantidade_autorizada',
    'quantidade_entregue',
)


class ItemRequisicaoInline(admin.TabularInline):
    model = ItemRequisicao
    extra = 0
    can_delete = False
    readonly_fields = QUANTIDADES_READONLY

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RequisicaoAdmin(admin.ModelAdmin):
    ...
    readonly_fields = ('numero_publico', 'estado', 'criado_em', 'atualizado_em')


class ItemRequisicaoAdmin(admin.ModelAdmin):
    ...
    readonly_fields = QUANTIDADES_READONLY

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TimelineRequisicaoAdmin(admin.ModelAdmin):
    ...
    readonly_fields = ('criado_em',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

```python
# apps/estoque/admin.py
class SaldoEstoqueAdmin(admin.ModelAdmin):
    ...
    readonly_fields = (
        'saldo_fisico',
        'saldo_reservado',
        'saldo_disponivel',
        'divergente',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

Notas de mecanismo, que sustentam a estratégia de testes:

- `readonly_fields` não é cosmético. `ModelAdmin.get_form` passa os campos
  readonly em `exclude`, então o `ModelForm` gerado **não tem o campo**: um POST
  forjado com `estado=atendida` é descartado no bind, não só escondido no HTML.
  É por isso que os testes verificam `get_form(...).base_fields` além do atributo.
- `estado` está no `fieldsets` de `RequisicaoAdmin` e permanece lá: o Django
  aceita campo readonly dentro de fieldset e o renderiza como texto. Removê-lo do
  fieldset esconderia do superusuário o estado da requisição que ele foi
  diagnosticar — o contrário do propósito da válvula de emergência.
- `delete_selected` some sozinho dos changelists de item, saldo e timeline:
  `ModelAdmin._filter_actions_by_permissions` filtra a action pelo
  `allowed_permissions = ('delete',)`, que consulta `has_delete_permission`. Não
  é preciso sobrescrever `get_actions`; o teste fixa esse acoplamento.
- O inline sobrevive ao `has_change_permission=False` porque
  `BaseModelAdmin.get_inline_instances` só descarta a inline quando **nenhuma**
  das quatro permissões vale; com `has_view_permission` default, ela continua
  aparecendo na change view de `Requisicao`, em modo leitura. É o resultado
  desejado: o superusuário vê os itens da requisição presa, sem poder editá-los.
- As assinaturas de `has_add_permission` **divergem** entre as duas classes-base:
  `ModelAdmin.has_add_permission(self, request)` e
  `InlineModelAdmin.has_add_permission(self, request, obj)` — `obj` é posicional
  e obrigatório no inline, porque `BaseModelAdmin.get_inline_instances` chama
  `inline.has_add_permission(request, obj)`. Errar isso levanta `TypeError` na
  renderização de **qualquer** change view de `Requisicao`.
- `extra = 0` e `can_delete = False` acompanham as permissões por redundância
  barata: o Django já força `max_num = 0` quando add é negado e já esconde a
  coluna de exclusão quando delete é negado, mas os dois atributos deixam a
  intenção explícita no lugar em que o leitor procura.

## Estratégia de testes

Camada: admin (ADR-0010 — testes de camada, sem duplicar a matriz de policies).
Fixtures reaproveitadas dos `conftest.py` de cada app: `superuser`,
`solicitante`, `setor_obras`, `req_historico_obras`, `estoque_principal`,
`material_disponivel`. `RequestFactory` para os testes de unidade, `client` +
`force_login` para os de contrato HTTP.

Duas fixtures novas, locais aos arquivos de teste, no mesmo padrão de
`staff_de_material` (#104): **`staff_de_requisicao`** e **`staff_de_saldo`** —
usuários com `is_staff=True`, **não** superusuários, com as permissões Django
`add`/`change`/`delete`/`view` concedidas — `staff_de_requisicao` para os três
models de `requisicoes` que aparecem nos casos (`requisicao`, `itemrequisicao`,
`timelinerequisicao`) e `staff_de_saldo` para `saldoestoque`. São o sujeito
que separa os dois gates: o Django, sozinho, os autorizaria, então qualquer
negação só pode vir do código deste plano — e qualquer 200 de leitura prova que
o gate não vazou para a consulta.

`apps/requisicoes/tests/test_admin.py` é arquivo novo; `apps/estoque/tests/test_admin.py`
já existe desde #102 e só recebe um bloco novo.

### `RequisicaoAdmin` — só `estado` sai do formulário

| # | Caso | Sujeito | Esperado |
|---|---|---|---|
| 1 | `estado` está em `readonly_fields` | — | introspecção passa |
| 2 | `estado` **não** está em `get_form(request, obj).base_fields` | `superuser` | prova o enforcement |
| 3 | idem, para quem o Django autorizaria por permissão própria | `staff_de_requisicao` | prova que o gate não é "superuser-only" |
| 4 | POST na change view tentando trocar `estado` | `superuser` | 302 e `estado` inalterado no banco |
| 5 | POST na mesma change view alterando `observacao_geral` | `superuser` | 302 e observação **alterada** |
| 6 | `GET admin:requisicoes_requisicao_change` renderiza | `superuser` | 200 (assinatura do inline correta) |

O caso 5 é o caminho feliz da válvula de emergência: sem ele, um
`has_change_permission=False` colado por engano em `RequisicaoAdmin` passaria em
todos os outros casos e ninguém notaria que o admin virou vitrine.

### `ItemRequisicaoAdmin` e `ItemRequisicaoInline` — somente-leitura

| # | Caso | Sujeito | Esperado |
|---|---|---|---|
| 7 | as três quantidades em `readonly_fields` (admin e inline) | — | introspecção passa |
| 8 | as três quantidades fora de `get_form(...).base_fields` | `superuser` | prova o enforcement |
| 9 | `has_add_permission` / `has_change_permission` / `has_delete_permission` negam | `superuser` | `False` nos três |
| 10 | `has_add_permission(request, obj)` do inline nega | `superuser` | `False` (assinatura de 3 args) |
| 11 | `GET admin:requisicoes_itemrequisicao_add` | `superuser` | 403, não 500 |
| 12 | `POST admin:requisicoes_itemrequisicao_change` | `staff_de_requisicao` | 403 apesar da permissão Django |
| 13 | `GET admin:requisicoes_itemrequisicao_changelist` | `staff_de_requisicao` | 200 — leitura preservada |
| 14 | `delete_selected` ausente das actions | `superuser` | action filtrada |

### `TimelineRequisicaoAdmin` — somente-leitura

| # | Caso | Sujeito | Esperado |
|---|---|---|---|
| 15 | `has_add_permission` / `has_change_permission` / `has_delete_permission` negam | `superuser` | `False` nos três |
| 16 | `delete_selected` ausente das actions | `superuser` | action filtrada |
| 17 | `GET admin:requisicoes_timelinerequisicao_add` | `staff_de_requisicao` | 403 apesar da permissão Django |
| 18 | `GET admin:requisicoes_timelinerequisicao_changelist` | `staff_de_requisicao` | 200 — leitura preservada |

### `SaldoEstoqueAdmin` — somente-leitura

| # | Caso | Sujeito | Esperado |
|---|---|---|---|
| 19 | `saldo_fisico`/`saldo_reservado` em `readonly_fields` | — | introspecção passa |
| 20 | ambos fora de `get_form(...).base_fields` | `superuser` | prova o enforcement |
| 21 | as três permissões negam | `superuser` | `False` nas três |
| 22 | `GET admin:estoque_saldoestoque_add` | `staff_de_saldo` | 403 apesar da permissão Django |
| 23 | `POST admin:estoque_saldoestoque_change` tentando `saldo_fisico=999` | `staff_de_saldo` | 403 e saldo inalterado no banco |
| 24 | `GET admin:estoque_saldoestoque_changelist` | `staff_de_saldo` | 200 — leitura preservada |

### Por que esta distribuição

- **Critério de aceite literal do issue** ("testes de introspecção
  `readonly_fields` / `has_*_permission` cobrindo cada admin"): casos 1, 7, 9,
  10, 15, 19, 21.
- **Caminho feliz** — o admin continua servindo para o que deve: casos 5, 6, 13,
  18, 24. Sem eles, "blindar" o admin negando leitura passaria despercebido.
- **Permissão negada, com o Django dizendo sim**: casos 12, 17, 22, 23. É o que
  prova que a negação vem deste plano e não das permissões padrão — e o caso 3
  faz o mesmo pelo lado do formulário. Os quatro usam `staff_de_*`, nunca
  `superuser`, justamente para que um `if request.user.is_superuser` colado no
  código não os salve.
- **Violação de domínio bloqueada, ponta a ponta**: casos 4 e 23 — POST forjado
  com o campo governado no corpo. O cenário do issue não é o admin clicar num
  widget, é o campo existir. O POST de requisição inclui os `management_form` do
  inline `itens` (prefixo `itens`, do `related_name` em `ItemRequisicao.requisicao`).
- **Armadilhas de mecanismo**: caso 11 fixa que o add de item vira **403 e não
  500** (é o `IntegrityError` que `readonly_fields` sozinho provocaria), e o caso
  10 fixa a assinatura de três argumentos do `has_add_permission` do inline —
  com dois, toda change view de `Requisicao` cai em `TypeError`, exatamente a
  classe de regressão do #104.
- **Enforcement vs. atributo** (casos 2, 3, 8, 20): o critério literal é fraco
  sozinho — um `get_readonly_fields` sobrescrito no futuro poderia devolver algo
  diferente do atributo de classe e o teste de introspecção continuaria verde
  enquanto o campo voltava a ser editável. `base_fields` mede o formulário que o
  Django realmente monta.

Não coberto, deliberadamente:

- Que usuário **sem** `is_staff` seja barrado do admin, e que staff sem nenhuma
  permissão Django receba 403. É comportamento default de `AdminSite.admin_view`
  e de `ModelAdmin.has_view_permission`, que nenhum admin deste plano
  sobrescreve; a ADR-0010 proíbe testar defaults de framework. Os casos 12, 17,
  22 e 23 cobrem o que **é** deste plano: negação apesar da permissão concedida.
- Que o Django esconda o botão "Add", renderize o campo readonly como `<p>` em
  vez de `<input>`, e some com o link "Delete" da change view — mesmo motivo.
- Que services e transitions sejam o único caminho legítimo de mudança de estado
  (vive em `test_services.py`/`test_transitions.py`) e que `MovimentacaoEstoque`
  seja imutável (vive nos testes de LED-05). Outra camada, já coberto.

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| REQ-05 | "Requisição precisa ter ao menos um item." Hoje **violável pelo admin**: o inline apaga a última linha e o banco fica com requisição vazia, sem passar por service. Negar delete no inline e em `ItemRequisicaoAdmin` (casos 9, 12, 14) fecha o único caminho fora do domínio. |
| REQ-06 | "Após envio, não há edição direta de itens." Hoje contornável em qualquer estado, pelo admin avulso e pelo inline. Casos 7–14 fecham add, change e delete. |
| REQ-08 | "Timeline registra eventos principais e é visível a autorizados." A trilha só tem valor se for append-only; hoje o admin edita e apaga evento. Casos 15–17 fecham a escrita; o caso 18 preserva a visibilidade que o próprio invariante exige. |
| LED-01 | "Toda mutação de `SaldoEstoque` pelos services gera `MovimentacaoEstoque` na mesma transação." Escrita direta de saldo — e criação/exclusão de linha de saldo — pelo admin é mutação **sem** movimentação: a exceção que o invariante não previu. Casos 19–23 fecham. |
| LED-02 | "`Σ delta_fisico`/`Σ delta_reservado` reconciliam com os saldos." É o invariante que quebra silenciosamente quando o admin ajusta saldo à mão, cria linha zerada fora do ledger, ou reatribui o `material` de uma linha existente: a reconciliação passa a acusar divergência permanente, sem nenhuma linha de ledger que a explique. Motivo direto da subida de 🟡 pré-produção para pré-piloto. |
| LED-05 | "Ledger é append-only." Preservado sem código novo — `MovimentacaoEstoque` já se defende no model. Citado como o padrão que `TimelineRequisicao`, `ItemRequisicao` e `SaldoEstoque` passam a espelhar na camada admin. |
| EST-01 | "disponível = físico − reservado." Preservado: `saldo_disponivel` continua property calculada; a mudança tira do formulário os dois operandos, não a fórmula. |
| PER-05 | "Superusuário tem permissões totais, incluindo administração." Tensão aparente, resolvida: o superusuário mantém acesso a todo o admin, leitura completa dos cinco models e escrita nos campos não derivados de `Requisicao`. O que ele perde é a escrita direta em campos derivados — que nunca foi permissão, e sim lapso. Os casos 5, 6, 13, 18 e 24, mais o não-uso de `has_view_permission`, mantêm PER-05 verificável. |
| PER-08 | "Views e services chamam a mesma policy contextual." Reforçado: o admin deixa de ser um caminho de escrita que não passa por policy nenhuma. |

Nenhuma linha da matriz de invariantes ou da matriz de permissões precisa ser
reescrita — a mudança faz o código convergir para o que já está documentado.

## Riscos

| Risco | Avaliação |
|---|---|
| Perder a válvula de emergência | O risco real do issue, e o que mais cresce ao fechar item e saldo por inteiro. Mitigado por desenho: leitura intacta nos cinco admins, e `Requisicao` — o agregado por onde o socorro começa — segue com add/change/delete e com `criador`/`beneficiario`/`setor_beneficiario`/`observacao_geral` editáveis. Casos 5, 6, 13, 18 e 24 fixam isso em teste. Se um estado ficar preso **sem** caminho de domínio, é bug de domínio a abrir como issue própria — não justificativa para reabrir o admin. |
| Fechar item/saldo é escopo além do issue | Reconhecido e deliberado. O issue restringe o escopo a "escrita direta de estado/quantidade/saldo/timeline", e as operações fechadas **são** essa escrita por outra porta: criar item é escrever `quantidade_solicitada`; trocar o `material` de uma linha de saldo é reatribuir o saldo; apagar item é zerar as três quantidades de uma vez. O critério de aceite ("nenhum dos campos acima é editável pelo admin") não fecha com meia-medida. Refinamentos que **não** são essa escrita seguem em pré-produção, como o issue pede. |
| `readonly_fields` transformar add em erro 500 | O risco concreto encontrado na revisão do plano, e uma das razões de negar add. Varredura dos três models: só `ItemRequisicao.quantidade_solicitada` é NOT NULL sem `default` (e ainda com `CheckConstraint > 0`); `Requisicao.estado` e os dois saldos têm default. Caso 11 fixa o resultado. |
| Assinatura errada de `has_add_permission` no inline | Regressão de mesma classe que o #104: `TypeError` na montagem do menu/change view derruba páginas que nada têm a ver com item. Mitigado pela nota de mecanismo e pelos casos 6 e 10. |
| Inline sumir da change view de `Requisicao` | Não ocorre: `get_inline_instances` só descarta a inline quando add, change, delete **e** view são todos negados. Com `has_view_permission` default, ela permanece em modo leitura. Caso 6 fixa o 200. |
| `TimelineRequisicao`/`SaldoEstoque` sem caminho de escrita | Falso. Timeline é escrita pelos services de transição (varredura confirma: `ciclo_vida`, `atendimento`, `cancelamento`, `copia`; o admin não é produtor). Linhas de saldo nascem em `confirmar_importacao_scpi` e mudam pelos services do ledger. |
| Testes acoplados a internals do Django | `get_form(...).base_fields` e o filtro de actions por permissão são API e comportamento documentados, não atributos privados. Os casos 4–6, 11–13, 17, 18 e 22–24 são de contrato HTTP e sobreviveriam a uma mudança de mecanismo interno. |
| Concorrência / locks | Nada tocado. A mudança é declarativa na camada admin. |
| Máquina de estados / transições | Não tocada — é justamente o que a mudança passa a proteger. |
| Contrato OpenAPI | Projeto server-rendered sem camada REST. Não se aplica. |
| Migrations / dados existentes | Sem mudança de schema. Nada a resetar. |
