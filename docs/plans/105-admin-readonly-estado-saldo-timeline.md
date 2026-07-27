# Plano — Admin não escreve estado/quantidade/saldo/timeline direto (#105)

## Escopo

Fechar as quatro brechas em que o Django admin permite escrever, à mão, campos
governados pela máquina de estados, pelo ledger e pela trilha de auditoria —
contornando services, policies e `MovimentacaoEstoque`.

O admin permanece **válvula de emergência**: nada aqui remove telas, oculta
modelos ou restringe leitura. A mudança é estreita — tira do formulário os
campos cuja escrita direta quebra invariante, e nega escrita no log append-only.

**Vai mudar:**

- `apps/requisicoes/admin.py`
  - `RequisicaoAdmin.readonly_fields` ganha `estado`.
  - `ItemRequisicaoAdmin.readonly_fields` passa a existir, com
    `quantidade_solicitada`, `quantidade_autorizada` e `quantidade_entregue`;
    e `has_add_permission` passa a devolver `False` (justificativa abaixo).
  - `ItemRequisicaoInline.readonly_fields` passa a existir, com as mesmas três
    quantidades; `extra` cai para `0` e `has_add_permission` devolve `False`.
  - `TimelineRequisicaoAdmin` ganha `has_add_permission`,
    `has_change_permission` e `has_delete_permission` fixos em `False`.
- `apps/estoque/admin.py`
  - `SaldoEstoqueAdmin.readonly_fields` ganha `saldo_fisico` e
    `saldo_reservado`, ao lado de `saldo_disponivel`/`divergente` que já estão lá.
- `apps/requisicoes/tests/test_admin.py` — arquivo **novo**.
- `apps/estoque/tests/test_admin.py` — arquivo já existente (#102, #104); ganha
  um bloco para `SaldoEstoqueAdmin` e uma linha no docstring do módulo.

**Não vai mudar:**

- Leitura. `has_view_permission` não é sobrescrito em lugar nenhum: changelist e
  change view de todos os quatro admins seguem abrindo para quem o Django já
  autoriza. `TimelineRequisicaoAdmin` com `has_change_permission=False` e
  `has_view_permission` default renderiza a change view em modo somente-leitura,
  que é exatamente o comportamento desejado para um log de auditoria.
- `MovimentacaoEstoqueAdmin`. A ADR-0015 já garante imutabilidade no model
  (`save`/`delete` levantam), e o issue trata esse admin como já protegido.
  Registrar aqui uma observação para triagem futura, sem agir: a ADR-0015
  (§ Riscos) justifica a garantia app-level pela "ausência de UI/admin de
  edição", mas `MovimentacaoEstoqueAdmin` está registrado com add/change/delete
  — hoje o efeito é um erro 500 em vez de um 403, o que é feio mas não viola
  LED-05. Fora do escopo deste issue.
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

### Por que negar add de item (e só de item)

Deixar o add aberto com as quantidades readonly não é uma opção neutra: é um
erro 500. `ItemRequisicao.quantidade_solicitada` é `DecimalField` **NOT NULL,
sem `default`**, e ainda tem `CheckConstraint item_solicitada_positiva (> 0)`.
Com o campo em `readonly_fields`, `ModelAdmin.get_form` o joga em `exclude` e o
`ModelForm` deixa de tê-lo — o save cai em `IntegrityError`. Ou seja, "manter o
add" entregaria uma tela que quebra em vez de uma tela que nega.

Então `has_add_permission → False` em `ItemRequisicaoAdmin` e em
`ItemRequisicaoInline` (com `extra = 0`, senão o Django renderiza uma linha
vazia que não pode ser salva). Isso é o *mesmo* escopo, não escopo novo: criar
um item **é** escrever `quantidade_solicitada` direto, que é exatamente o que o
issue fecha. Itens nascem de `criar_requisicao`/`copiar_requisicao`, nunca à mão.

O inline **continua permitindo remover linhas**, e `ItemRequisicaoAdmin` mantém
change (dos campos não-quantitativos) e delete. Fechar isso seria decisão
separada e tiraria do superusuário a capacidade de desfazer uma linha corrompida.

Assimetria deliberada com os outros dois models: `Requisicao.estado` tem
`default=EstadoRequisicao.RASCUNHO` e `SaldoEstoque.saldo_fisico`/`saldo_reservado`
têm `default=0`, então nesses dois o add segue funcionando com o campo readonly —
e nasce no valor correto (rascunho / zerado), coerente com REQ-01. Só
`ItemRequisicao` não tem default, e é por isso que só ele perde o add.

## Arquivos a alterar

Nenhuma mudança abaixo foi aplicada ainda: na altura deste commit o repositório
contém apenas este plano, e os quatro admins seguem com as brechas descritas.

| Arquivo | Ação prevista |
|---|---|
| `apps/requisicoes/admin.py` | Acrescentar `readonly_fields` em `RequisicaoAdmin` (`estado`), `ItemRequisicaoAdmin` e `ItemRequisicaoInline` (as três quantidades); negar add em `ItemRequisicaoAdmin`/`ItemRequisicaoInline`; negar add/change/delete em `TimelineRequisicaoAdmin` |
| `apps/estoque/admin.py` | Acrescentar `saldo_fisico`/`saldo_reservado` ao `readonly_fields` de `SaldoEstoqueAdmin` |
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
    readonly_fields = QUANTIDADES_READONLY

    def has_add_permission(self, request, obj):
        return False


class RequisicaoAdmin(admin.ModelAdmin):
    ...
    readonly_fields = ('numero_publico', 'estado', 'criado_em', 'atualizado_em')


class ItemRequisicaoAdmin(admin.ModelAdmin):
    ...
    readonly_fields = QUANTIDADES_READONLY

    def has_add_permission(self, request):
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
- `delete_selected` some sozinho do changelist de `TimelineRequisicao`:
  `ModelAdmin._filter_actions_by_permissions` filtra a action pelo
  `allowed_permissions = ('delete',)`, que consulta `has_delete_permission`. Não
  é preciso sobrescrever `get_actions`; o teste fixa esse acoplamento.
- `RequisicaoAdmin` mantém delete: cancelar/descartar requisição via domínio é
  outro assunto, e o issue não pede. Só a escrita de `estado` é fechada.
- As assinaturas de `has_add_permission` **divergem** entre as duas classes-base:
  `ModelAdmin.has_add_permission(self, request)` e
  `InlineModelAdmin.has_add_permission(self, request, obj)` — `obj` é posicional
  e obrigatório no inline, porque `BaseModelAdmin.get_inline_instances` chama
  `inline.has_add_permission(request, obj)`. Errar isso levanta `TypeError` na
  renderização de **qualquer** change view de `Requisicao`.
- `extra = 0` acompanha o `has_add_permission` do inline por redundância barata:
  `get_inline_instances` já força `max_num = 0` quando add é negado, mas fixar
  `extra` deixa a intenção explícita no lugar em que o leitor procura.

## Estratégia de testes

Camada: admin (ADR-0010 — testes de camada, sem duplicar a matriz de policies).
Fixtures reaproveitadas dos `conftest.py` de cada app: `superuser`,
`solicitante`, `setor_obras`, `req_historico_obras`, `estoque_principal`,
`material_disponivel`. `RequestFactory` para os testes de unidade, `client` +
`force_login` para os de contrato HTTP.

`apps/requisicoes/tests/test_admin.py` é arquivo novo; `apps/estoque/tests/test_admin.py`
já existe desde #102 e só recebe um bloco novo.

| # | Caso | Alvo | Esperado |
|---|---|---|---|
| 1 | `estado` está em `readonly_fields` | `RequisicaoAdmin` | introspecção passa |
| 2 | `estado` **não** está em `get_form(request, obj).base_fields` | `RequisicaoAdmin` | prova o enforcement |
| 3 | POST na change view tentando trocar `estado` | `admin:requisicoes_requisicao_change` | `estado` no banco inalterado |
| 4 | as três quantidades em `readonly_fields` | `ItemRequisicaoAdmin` | introspecção passa |
| 5 | as três quantidades fora de `get_form(...).base_fields` | `ItemRequisicaoAdmin` | prova o enforcement |
| 6 | as três quantidades em `readonly_fields` | `ItemRequisicaoInline` | introspecção passa |
| 7 | as três quantidades fora do formset do inline | `ItemRequisicaoInline` | prova o enforcement |
| 8 | `has_add_permission` nega | `ItemRequisicaoAdmin` | `False` |
| 9 | `GET admin:requisicoes_itemrequisicao_add` | superusuário logado | 403, não 500 |
| 10 | `has_add_permission(request, obj)` nega | `ItemRequisicaoInline` | `False` |
| 11 | `GET admin:requisicoes_requisicao_change` renderiza | superusuário logado | 200 (assinatura do inline correta) |
| 12 | `has_add_permission` nega | `TimelineRequisicaoAdmin` | `False` |
| 13 | `has_change_permission` nega | `TimelineRequisicaoAdmin` | `False` |
| 14 | `has_delete_permission` nega | `TimelineRequisicaoAdmin` | `False` |
| 15 | `delete_selected` ausente das actions | `TimelineRequisicaoAdmin` | action filtrada |
| 16 | `GET admin:requisicoes_timelinerequisicao_add` | superusuário logado | 403 |
| 17 | `GET .../timelinerequisicao/` (changelist) | superusuário logado | 200 |
| 18 | `saldo_fisico`/`saldo_reservado` em `readonly_fields` | `SaldoEstoqueAdmin` | introspecção passa |
| 19 | ambos fora de `get_form(...).base_fields` | `SaldoEstoqueAdmin` | prova o enforcement |
| 20 | POST na change view tentando trocar `saldo_fisico` | `admin:estoque_saldoestoque_change` | saldo no banco inalterado |

Os casos 1, 4, 6, 8, 10, 12–14 são o critério de aceite literal ("testes de
introspecção `readonly_fields` / `has_*_permission`").

Os casos 9 e 11 cobrem a armadilha descrita nas notas de mecanismo: o 9 fixa que
o add de item vira **403 e não 500** (é o `IntegrityError` que `readonly_fields`
sozinho provocaria), e o 11 fixa a assinatura de três argumentos do
`has_add_permission` do inline — com dois, toda change view de `Requisicao` cai
em `TypeError`, exatamente a classe de regressão do #104.

Os casos 2, 5, 7 e 19 existem porque o critério literal é fraco sozinho: um
`get_readonly_fields` sobrescrito no futuro poderia devolver algo diferente do
atributo de classe, e o teste de introspecção continuaria verde enquanto o campo
voltava a ser editável. Verificar `base_fields` mede o formulário que o Django
realmente monta.

Os casos 3 e 20 são a prova de ponta a ponta contra POST forjado — o cenário do
issue não é o admin clicar num widget, é o campo existir. Um POST com
`estado='atendida'` (ou `saldo_fisico=999`) deve ser aceito com 302 e **não**
alterar o banco. O POST de requisição inclui os `management_form` do inline
`itens` (prefixo `itens`, do `related_name` em `ItemRequisicao.requisicao`).

O caso 17 espera **200**, não 403, e é deliberado: negar escrita não pode negar
consulta da trilha de auditoria. Sem ele, alguém "reforçando" o admin com
`has_view_permission = False` passaria em todos os outros casos.

Não coberto (defaults de framework, a ADR-0010 proíbe testar): que o Django
esconda o botão "Add", que renderize o campo readonly como `<p>` em vez de
`<input>`, e que o link "Delete" suma da change view.

Não coberto (outra camada, já coberto): que services e transitions sejam o único
caminho legítimo de mudança de estado — vive em `test_services.py` e
`test_transitions.py`; e que `MovimentacaoEstoque` seja imutável — vive nos
testes de LED-05.

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| REQ-05 | "Requisição precisa ter ao menos um item." Preservado: o inline mantém a remoção de linhas, então o admin continua podendo esvaziar uma requisição — o invariante segue guardado no service, onde já está. Negar add de item não o afeta. |
| REQ-06 | "Após envio, não há edição direta de itens." Hoje **contornável pelo admin** via `ItemRequisicaoAdmin` e via o inline, em qualquer estado. Os casos 4–11 fecham. |
| REQ-08 | "Timeline registra eventos principais e é visível a autorizados." A trilha só tem valor se for append-only; hoje o admin edita e apaga evento. Casos 12–16 fecham a escrita, o caso 17 preserva a visibilidade que o invariante exige. |
| LED-01 | "Toda mutação de `SaldoEstoque` pelos services gera `MovimentacaoEstoque` na mesma transação." Escrita direta de `saldo_fisico`/`saldo_reservado` pelo admin é mutação **sem** movimentação — a exceção que o invariante não previu. Casos 18–20 fecham. |
| LED-02 | "`Σ delta_fisico`/`Σ delta_reservado` reconciliam com os saldos." É o invariante que quebra silenciosamente quando o admin ajusta saldo à mão: a reconciliação passa a acusar divergência permanente, sem nenhuma linha de ledger que a explique. Motivo direto da subida de 🟡 pré-produção para pré-piloto. |
| LED-05 | "Ledger é append-only." Preservado sem código novo — `MovimentacaoEstoque` já se defende no model. Citado aqui só como o padrão que `TimelineRequisicao` passa a espelhar na camada admin. |
| EST-01 | "disponível = físico − reservado." Preservado: `saldo_disponivel` continua property calculada e readonly; a mudança tira do formulário os dois operandos, não a fórmula. |
| PER-05 | "Superusuário tem permissões totais, incluindo administração." Tensão aparente, resolvida: o superusuário continua com acesso total ao admin e a todas as operações de negócio **pelos caminhos de domínio**. O que ele perde é a escrita direta em quatro campos derivados — que nunca foi uma permissão, e sim um lapso. O caso 17 e o não-uso de `has_view_permission` mantêm PER-05 verificável. |
| PER-08 | "Views e services chamam a mesma policy contextual." Reforçado: o admin deixa de ser um caminho de escrita que não passa por policy nenhuma. |

Nenhuma linha da matriz de invariantes ou da matriz de permissões precisa ser
reescrita — a mudança faz o código convergir para o que já está documentado.

## Riscos

| Risco | Avaliação |
|---|---|
| Perder a válvula de emergência | O risco real do issue. Mitigado por desenho: nenhuma tela some, nenhuma leitura é negada, e `Requisicao`/`ItemRequisicao`/`SaldoEstoque` seguem editáveis nos demais campos. A saída de emergência para estado preso passa a ser o service de domínio, que é o ponto do issue. Se um estado ficar preso **sem** caminho de domínio, isso é bug de domínio a ser aberto como issue própria — não justificativa para reabrir o admin. |
| `TimelineRequisicao` sem nenhum caminho de escrita | Falso: o log é escrito pelos services de transição, não pelo admin. Varredura de criação de `TimelineRequisicao` confirma que o admin não é produtor. |
| Add de `SaldoEstoque` pelo admin fica inútil | Com os dois saldos readonly, um `SaldoEstoque` criado pelo admin nasce zerado — sem erro, porque ambos têm `default=0`. É aceitável e coerente: linha de saldo é criada pelo caminho de importação SCPI/serviços, não à mão. Fechar o add do `SaldoEstoqueAdmin` é decisão separada e não está no escopo. |
| `readonly_fields` transformar add em erro 500 | O risco concreto encontrado na revisão do plano, e a razão de `ItemRequisicaoAdmin`/`ItemRequisicaoInline` também perderem add. Varredura dos três models: só `ItemRequisicao.quantidade_solicitada` é NOT NULL sem `default` (e ainda com `CheckConstraint > 0`); `Requisicao.estado` e os dois saldos têm default. Casos 9 e 11 fixam o resultado. |
| Assinatura errada de `has_add_permission` no inline | Regressão de mesma classe que o #104: `TypeError` na montagem do menu/change view derruba páginas que nada têm a ver com item. Mitigado pela nota de mecanismo e pelo caso 11 (change view de `Requisicao` responde 200). |
| Testes acoplados a internals do Django | `get_form(...).base_fields` e `_filter_actions_by_permissions` são API pública documentada (`get_form`) e comportamento documentado (actions filtradas por permissão), não atributos privados. Os casos 3, 9, 11, 16, 17 e 20 são de contrato HTTP e sobreviveriam a uma mudança de mecanismo interno. |
| Concorrência / locks | Nada tocado. A mudança é declarativa na camada admin. |
| Máquina de estados / transições | Não tocada — é justamente o que a mudança passa a proteger. |
| Contrato OpenAPI | Projeto server-rendered sem camada REST. Não se aplica. |
| Migrations / dados existentes | Sem mudança de schema. Nada a resetar. |
