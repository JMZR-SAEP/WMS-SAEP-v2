# Plano — Desativação de setor passa por service (#107)

## Escopo

`Setor.ativo = False` é hoje a única mutação de cadastro relevante para
autorização que escapa da camada de service. `SetorAdmin.save_model`
(`apps/accounts/admin.py:38`) só desvia quando `chefe` está em
`form.changed_data`; a desativação cai no `super().save_model` e vira UPDATE
direto no model — sem `exigir_pode_gerir_cadastro`, sem `select_for_update` e
sem nenhuma decisão sobre as requisições do setor que estão em
`aguardando_autorizacao`.

Este plano cria `desativar_setor`, simétrico a `desativar_usuario` (USR-07), e
fixa o destino das requisições em voo: **bloquear a desativação**, não
cascatear.

**Limite do contrato, declarado de saída:** este plano **não** fecha a corrida
entre a desativação de setor e `enviar_para_autorizacao`. O guard do #103 lê o
`Setor` com `.filter(...).exists()`, sem lock, por decisão explícita (decisão 1
do plano do #103: não travar linhas de cadastro no caminho do envio). Um
`select_for_update` só no lado da escrita serializa escrita-vs-escrita; a janela
leitura-vs-escrita continua aberta e continua declarada no docstring de
`enviar_para_autorizacao`. O que muda aqui é quem pode desativar um setor, sob
que pré-condição e com qual serialização contra outras escritas de cadastro.

**Muda:**

- `apps/accounts/services.py` — novo `desativar_setor(*, ator_id, setor_id)`.
- `apps/accounts/admin.py` — `SetorAdmin.save_model` roteia a desativação pelo
  service, antes do ramo de troca de chefia.
- `apps/accounts/tests/test_services.py` — classe `TestDesativarSetor`.
- `apps/accounts/tests/test_admin.py` — arquivo novo; roteamento e tradução da
  exceção no admin.
- `docs/matriz-invariantes.md` — USR-06 registra o ponto de reforço na
  desativação.

**Não muda:**

- `apps/accounts/models.py` — nenhum campo, nenhuma constraint. **Sem migration.**
- `apps/accounts/policies.py` — `pode_gerir_cadastro` já é a policy correta:
  quem pode gerir cadastro pode desativar setor. A pré-condição de requisições
  em voo é regra de estado do agregado, não de permissão do ator; ADR-0011 põe
  isso em service.
- `apps/requisicoes/**` — nenhuma transição nova, nenhuma mutação de requisição
  disparada por cadastro. `transitions.py` intocado.
- `apps/requisicoes/services/ciclo_vida.py` — o guard de envio fica como está,
  inclusive a janela de corrida que ele declara.
- Setores já inativos com requisições em voo — sem data migration, sem varredura.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/accounts/services.py` | `desativar_setor` após `desativar_usuario` |
| `apps/accounts/admin.py` | Ramo de desativação em `SetorAdmin.save_model`, antes do ramo de `chefe` |
| `apps/accounts/tests/test_services.py` | `TestDesativarSetor` — 7 casos |
| `apps/accounts/tests/test_admin.py` | Arquivo novo — 4 casos de roteamento/tradução |
| `docs/matriz-invariantes.md` | Coluna de verificação de USR-06 |

## Implementação

### Service

```python
@transaction.atomic
def desativar_setor(*, ator_id: int, setor_id: int) -> None:
    """Desativa setor, bloqueando se há requisições aguardando autorização (USR-06)."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro
    from apps.requisicoes.models import EstadoRequisicao, Requisicao

    try:
        ator = User.objects.get(pk=ator_id)
        setor = Setor.objects.select_for_update().get(pk=setor_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    if not setor.ativo:
        return

    em_voo = Requisicao.objects.filter(
        setor_beneficiario=setor,
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
    ).count()
    if em_voo:
        termo = 'requisição' if em_voo == 1 else 'requisições'
        raise ConflitoDominio(
            f"O setor '{setor.nome}' tem {em_voo} {termo} aguardando autorização. "
            'Conclua ou cancele antes de desativar o setor.',
            code='setor_com_requisicoes_em_voo',
        )

    setor.ativo = False
    setor.save(update_fields=['ativo'])
```

Seis decisões que o código embute:

1. **Bloquear, não cascatear.** As saídas de `aguardando_autorizacao` sem
   autorização são TR-006 (retornar para rascunho) e TR-012 (cancelar), e
   `docs/estado-transicoes-requisicao.md` designa **criador ou beneficiário**
   como ator das duas. Um admin executá-las em massa a partir de uma mudança de
   cadastro contradiz o ator documentado e transforma um service de cadastro em
   mutador de requisições. Bloquear mantém a decisão com quem o documento já
   designou, sem transição nova e sem reescrever o contrato de TR-006/TR-012.
2. **`ConflitoDominio`, não `DadosInvalidos`.** O `setor_id` submetido está
   correto; o que impede a operação é o estado do domínio no momento da
   desativação — definição literal de `ConflitoDominio` em
   `apps/core/exceptions.py`. Mesma escolha de `desativar_usuario` para o
   bloqueio de USR-07.
3. **Só `aguardando_autorizacao` bloqueia.** É o único estado cuja continuação
   depende de um autorizador do setor. `rascunho` não está na fila de ninguém;
   `autorizada` e `pronta_para_retirada` seguem pelo almoxarifado, que não
   consulta o setor do beneficiário; estados terminais não seguem. Bloquear por
   qualquer requisição histórica tornaria a desativação impossível na prática —
   `setor_beneficiario` é `PROTECT` e nunca é apagado.
4. **`count()`, não `exists()`.** Uma query nos dois caminhos, e a mensagem diz
   ao admin o tamanho do trabalho pendente em vez de só que ele existe. A
   pluralização é manual porque o projeto não usa i18n.
5. **Idempotente depois da policy.** Setor já inativo retorna sem erro, mesma
   forma de `desativar_usuario` com usuário já inativo — repetir a operação não
   é conflito. O early return vem **depois** de `exigir_pode_gerir_cadastro`:
   quem não pode gerir cadastro recebe `PermissaoNegada` mesmo quando a operação
   seria no-op, para não vazar estado de cadastro por diferença de resposta.
6. **Import local de `apps.requisicoes.models`.** `apps.requisicoes.models`
   importa `accounts.Setor`; importar no topo de `apps/accounts/services.py`
   criaria dependência circular entre os módulos. O import dentro da função é o
   padrão já usado no arquivo para `policies`.

### Roteamento no admin

```python
def save_model(self, request, obj, form, change):
    if change and 'ativo' in form.changed_data and not obj.ativo:
        from apps.accounts.services import desativar_setor
        from apps.core.exceptions import ConflitoDominio

        campos_extras = set(form.changed_data) - {'ativo'}
        if campos_extras:
            raise ConflitoDominio(
                'Desative o setor separadamente de outras alterações de cadastro.',
                code='desativacao_setor_com_campos_extras',
            )
        desativar_setor(ator_id=request.user.pk, setor_id=obj.pk)
        return  # service já persistiu; super sobrescreveria com os dados do form

    if change and 'chefe' in form.changed_data:
        ...  # ramo existente, inalterado
```

Duas decisões:

1. **O ramo de desativação vem primeiro.** Se `ativo` e `chefe` mudarem no mesmo
   POST e o ramo de chefia rodasse antes, `trocar_chefe_setor` executaria e o
   `super().save_model` seguinte gravaria `ativo=False` direto, sem passar pelo
   service — exatamente o vetor que este issue fecha.
2. **Recusar desativação misturada com outras alterações.** Cópia deliberada do
   guard `desativacao_com_campos_extras` de `UserAdmin`: o `return` que impede o
   `super().save_model` também descarta silenciosamente qualquer outro campo
   editado no mesmo POST. Recusar explicitamente é melhor que perder a edição
   sem aviso.

A tradução para mensagem no admin já existe: `SetorAdmin.changeform_view` usa
`_changeform_com_captura_dominio`, que converte `ErroDominio` em
`message_user(level=ERROR)` + redirect, e `PermissaoNegada` em
`PermissionDenied` (HTTP 403).

## Estratégia de testes

Camada de service, `apps/accounts/tests/test_services.py`, classe
`TestDesativarSetor`:

| # | Caso | Esperado |
|---|---|---|
| 1 | Setor com requisição em `aguardando_autorizacao` | `ConflitoDominio`, `code == 'setor_com_requisicoes_em_voo'`; `setor.ativo` segue `True` |
| 2 | Setor sem requisições | `ativo` vira `False` |
| 3 | Setor só com rascunho | desativa — cobre a decisão 3 |
| 4 | Setor só com requisição `autorizada` | desativa — cobre a decisão 3 |
| 5 | Requisição em voo de **outro** setor | desativa — o filtro é por `setor_beneficiario` |
| 6 | Setor já inativo | idempotente, sem exceção |
| 7 | Ator não superusuário | `PermissaoNegada`; `setor.ativo` segue `True` |

Casos 1, 2 e 7 são a anatomia obrigatória de ADR-0010 (caminho feliz, violação
de domínio sem escrita, permissão negada sem escrita). Os casos 3 a 5 protegem o
recorte do filtro, que um refactor ingênuo (`Requisicao.objects.filter(
setor_beneficiario=setor)` sem `estado`) desfaria silenciosamente e tornaria
qualquer setor com histórico indesativável.

Camada de admin, `apps/accounts/tests/test_admin.py` (arquivo novo):

| # | Caso | Esperado |
|---|---|---|
| 8 | `save_model` com `ativo` desmarcado, sem requisições em voo | setor inativo no banco — roteou pelo service |
| 9 | `save_model` com `ativo` desmarcado e requisição em voo | `ConflitoDominio` propagado; setor segue ativo |
| 10 | `save_model` com `ativo` e `nome` alterados no mesmo POST | `ConflitoDominio`, `code == 'desativacao_setor_com_campos_extras'`; nada persistido |
| 11 | POST no changeform do admin com requisição em voo | 302 e mensagem de erro, não 500 — cobre `_changeform_com_captura_dominio` |

Os testes 8 a 10 chamam `SetorAdmin.save_model` diretamente com um `RequestFactory`,
padrão já usado em `apps/estoque/tests/test_admin.py`. O 11 usa o `client` de
verdade porque o contrato sob teste é a tradução HTTP, não a decisão de domínio.

Não coberto, e por quê: a corrida com `enviar_para_autorizacao` (fora de escopo,
declarado acima; reproduzi-la exigiria duas transações concorrentes para
verificar um comportamento que o plano não previne); reativação de setor
(`ativo` voltando a `True` não tem invariante em risco e segue pelo
`super().save_model`); usuários lotados no setor desativado (fora de escopo).

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| USR-06 | "Setor inativo permanece em histórico e não recebe nova requisição." O service acrescenta o outro lado: um setor **não fica** inativo enquanto tiver requisição aguardando autorização. A linha da matriz ganha o ponto de verificação; a definição não muda. |
| USR-07 | Não muda. `desativar_usuario` continua sendo o caminho de desativação de chefe, e `desativar_setor` não o chama nem é chamado por ele — desativar um setor não desativa seus usuários. |
| USR-04 | Não muda. Continua sendo possível existir setor ativo sem chefe (bootstrap); o backlog ACE-002 segue aberto. |
| REQ-* | Nenhuma requisição é criada, transicionada ou apagada por este service. |
| EST-* | Nenhum saldo é tocado. |

## Riscos

| Risco | Avaliação |
|---|---|
| Setor com chefe já inativo e requisições em voo fica indesativável pelo admin | Real e aceito. Se o chefe não pode mais autorizar/recusar, só criador ou beneficiário esvaziam a fila, por TR-006/TR-012. O admin depende de outras pessoas para concluir a desativação. É o mesmo desenho de USR-07 (bloquear até o cadastro ficar consistente) e a alternativa — cascata pelo admin — contradiz o ator documentado das duas transições. A mensagem diz quantas requisições faltam. |
| Corrida com o envio continua aberta | Declarado no Escopo e no docstring do guard de envio. Este plano não promete o contrário; quem depender disso vai ler a promessa certa. |
| Dependência `accounts → requisicoes` | Nova, e assimétrica: `requisicoes` já depende de `accounts`. Resolvida com import local dentro da função (decisão 6). Se outros services de cadastro passarem a consultar requisições, o caminho é um selector em `requisicoes` consumido por `accounts`, não import no topo. |
| Perda silenciosa de edições no admin | Endereçada pelo guard `desativacao_setor_com_campos_extras`, cópia do que `UserAdmin` já faz. |
| Migrations / schema | Nenhuma mudança de model. `make setup` não é necessário. |
| Contrato OpenAPI | Projeto é server-rendered sem camada REST (AGENTS.md). Não se aplica. |
