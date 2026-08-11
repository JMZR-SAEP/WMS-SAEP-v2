# Plano — Guarda USR-04 no remanejamento de lotação (#114)

## Escopo

A invariante do docstring de `Setor` — "se o setor tem chefe, o chefe pertence
ao próprio setor (`chefe.setor_id == setor.id`)" — só é verificada na
designação, dentro de `trocar_chefe_setor`
(`apps/accounts/services.py`). Nenhum caminho a verifica depois. Como
`UserAdmin.save_model` (`apps/accounts/admin.py`) só desvia quando `is_active`
está em `form.changed_data`, mudar `User.setor` de um chefe cai direto no
`super().save_model` e vira UPDATE no model.

O efeito não é cosmético: `papel_efetivo` (`apps/accounts/papeis.py`) deriva
chefia de `usuario.setor_chefiado`, o reverso de `Setor.chefe`, sem conferir
`usuario.setor_id`. Um chefe remanejado para outro setor continua com
`setor_chefiado_ativo_id` apontando para o setor antigo — ou seja, continua
vendo a fila e autorizando requisições de um setor ao qual não pertence mais.
É o achado R5 da auditoria.

Este plano fecha o vetor no ponto de escrita, criando `remanejar_usuario`,
simétrico a `desativar_usuario` (USR-07), e roteando o admin por ele.

**Limite do contrato, declarado de saída:** a guarda é **na escrita**, não na
leitura. `papel_efetivo` continua derivando chefia de `Setor.chefe` sem
conferir `User.setor` — ver "Não muda" e "Riscos" para o porquê.

**Divergências de contrato sinalizadas, não resolvidas aqui** (AGENTS.md manda
expor o conflito antes de implementar):

1. `CONTEXT.md` §12/§170 e USR-03 dizem que "usuário pertence a exatamente um
   setor"; `apps/accounts/models.py` declara `setor` com `null=True, blank=True`
   e comentário justificando a nulidade, e `seed_dev` semeia o ADMIN sem setor.
   O plano segue o model — ver decisão 8 — e registra a reconciliação como
   follow-up.
2. `remanejar_usuario` bloqueia por qualquer setor chefiado; `desativar_usuario`
   bloqueia só por setor `ativo=True`. A assimetria é deliberada neste recorte —
   ver decisão 5 — e alinhar os dois é follow-up, porque muda USR-07.

**Muda:**

- `apps/accounts/services.py` — novo
  `remanejar_usuario(*, ator_id, usuario_id, novo_setor_id, novo_chefe_id=None)`.
- `apps/accounts/admin.py` — `UserAdmin.save_model` roteia a troca de `setor`
  pelo service.
- `apps/accounts/tests/test_services.py` — classe `TestRemanejarUsuario`.
- `apps/accounts/tests/test_admin.py` — casos de `UserAdmin` (o arquivo hoje só
  cobre `SetorAdmin`).
- `docs/matriz-invariantes.md` — USR-04 registra o novo ponto de reforço.

**Não muda:**

- `apps/accounts/models.py` — nenhum campo, nenhuma constraint. **Sem migration.**
- `apps/accounts/papeis.py` — nenhuma checagem de leitura nova. Acrescentar
  `setor_chefiado.pk == usuario.setor_id` em `papel_efetivo` mascararia
  divergência de dados em vez de impedi-la, e mudaria o significado de
  `setor_chefiado_ativo_id` para todo consumidor de policy/selector — escopo
  bem maior que este issue. Com a guarda de escrita fechada, o único jeito de
  produzir a divergência passa a ser SQL direto ou ORM fora de service.
- `apps/accounts/policies.py` — `pode_gerir_cadastro` já é a policy certa: quem
  gere cadastro remaneja lotação. A pré-condição de chefia é regra de estado do
  agregado, não de permissão do ator; ADR-0011 põe isso em service.
- Lotação em setor **inativo** — nenhuma guarda nova. É uma questão de USR-06,
  não de USR-04, e hoje já é permitida pelo admin. Fora de escopo.
- `apps/requisicoes/**` — nenhuma transição, nenhuma requisição tocada.
- Dados já divergentes (chefe hoje lotado em outro setor) — sem data migration,
  sem varredura de saneamento.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/accounts/services.py` | `remanejar_usuario` após `desativar_usuario` |
| `apps/accounts/admin.py` | Ramo de `setor` em `UserAdmin.save_model`, depois do ramo de `is_active` |
| `apps/accounts/tests/test_services.py` | `TestRemanejarUsuario` — 10 casos |
| `apps/accounts/tests/test_admin.py` | 4 casos de `UserAdmin` (roteamento e tradução HTTP); a docstring do módulo hoje só cita o #107 e passa a cobrir os dois admins |
| `docs/matriz-invariantes.md` | Coluna de verificação de USR-04 |

## Implementação

### Service

```python
@transaction.atomic
def remanejar_usuario(
    *,
    ator_id: int,
    usuario_id: int,
    novo_setor_id: int | None,
    novo_chefe_id: int | None = None,
) -> None:
    """Muda a lotação, bloqueando se chefia setor ativo sem substituto (USR-04)."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
        usuario = User.objects.select_for_update().get(pk=usuario_id)
        if novo_setor_id is not None:
            Setor.objects.get(pk=novo_setor_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    if usuario.setor_id == novo_setor_id:
        return

    setor_chefiado = Setor.objects.select_for_update().filter(chefe=usuario).first()
    if setor_chefiado:
        if novo_chefe_id is None:
            raise ConflitoDominio(
                f"Usuário '{usuario.nome}' é chefe do setor "
                f"'{setor_chefiado.nome}'. Troque a chefia do setor antes de "
                'remanejar a lotação.',
                code='usuario_chefe_remanejado_sem_substituto',
            )
        if novo_chefe_id == usuario.pk:
            raise DadosInvalidos(
                f"Usuário '{usuario.nome}' não pode ser o próprio substituto "
                'na chefia.',
                code='substituto_igual_ao_remanejado',
            )
        trocar_chefe_setor(
            ator_id=ator_id,
            setor_id=setor_chefiado.pk,
            novo_chefe_id=novo_chefe_id,
        )

    usuario.setor_id = novo_setor_id
    usuario.save(update_fields=['setor'])
```

Oito decisões que o código embute:

1. **Guarda na escrita, não na leitura.** A divergência entre `Setor.chefe` e
   `User.setor` só nasce em um UPDATE. Fechar o UPDATE mantém uma única fonte de
   verdade; conferir na leitura criaria uma segunda definição de "é chefe" e
   deixaria a divergência existir em silêncio no banco. Já declarado no Escopo.
2. **`ConflitoDominio`, não `DadosInvalidos`.** O `novo_setor_id` submetido está
   correto; o que impede a operação é o estado do domínio no momento do
   remanejamento — definição literal de `ConflitoDominio` em
   `apps/core/exceptions.py`. Mesma escolha de `desativar_usuario` para USR-07.
3. **`novo_chefe_id` opcional, espelhando `desativar_usuario`.** O bloqueio
   sozinho já satisfaz o issue, mas o parâmetro dá o caminho atômico
   troca-e-remaneja dentro de uma transação, e reusa `trocar_chefe_setor` — que
   é quem valida chefe ativo, chefe do setor certo e chefia duplicada. Sem esse
   parâmetro, o fluxo completo só existiria como duas transações separadas, com
   janela entre elas. O admin **não** o usa (não há campo de substituto no
   formulário de `User`); ele existe para chamadas de service.
4. **Substituto não pode ser o próprio remanejado.** `trocar_chefe_setor`
   aceitaria `novo_chefe == usuario` — ele ainda pertence ao setor antigo neste
   ponto — e o `save` seguinte moveria o recém-designado chefe para fora,
   recriando exatamente a divergência que o service existe para impedir.
   `DadosInvalidos` porque o argumento submetido é que está errado.
5. **Bloqueia em qualquer setor chefiado, ativo ou não.** O invariante do
   docstring de `Setor` e o `CONTEXT.md` §171 ("cada Setor tem exatamente um
   Chefe de setor") não são qualificados por `ativo`. Não basta que
   `papel_efetivo` zere `setor_chefiado_ativo_id` em setor inativo: isso impede
   o vazamento de autoridade, mas não impede o estado inconsistente de ficar
   gravado. O filtro é `chefe=usuario`, sem `ativo=True`.
   **Assimetria declarada:** `desativar_usuario` filtra por `ativo=True` e
   continua assim — alinhar os dois é mudança de comportamento em USR-07, fora
   do escopo deste issue, e fica registrada como follow-up.
   **Saída para o caso preso:** um chefe de setor inativo sem nenhum outro
   usuário lotado nele não tem substituto possível e fica sem remanejamento pelo
   admin (`SetorAdmin` recusa `chefe=None` com `chefe_nulo`). É o mesmo tipo de
   travamento que USR-07 já aceita, e resolvê-lo exige decidir se chefia pode
   ser removida sem substituto — questão do backlog ACE-002, não deste issue.
6. **`select_for_update` no setor chefiado, antes de decidir.** Sem o lock, uma
   `trocar_chefe_setor` concorrente pode designar outro chefe entre a leitura e
   o commit, e a chamada de substituição daqui sobrescreveria essa designação —
   perda de atualização. Com o lock, quando existe chefia a decidir, as duas
   escritas serializam. **O que o lock não fecha:** se o usuário ainda **não** é
   chefe de nada, não há linha para travar, e uma `trocar_chefe_setor`
   concorrente pode torná-lo chefe logo após a checagem (leitura fantasma sob
   READ COMMITTED). Fechar isso exigiria lock de tabela ou serialização de todo
   o cadastro; fora de escopo, e o desfecho é o mesmo estado que este issue
   corrige no próximo remanejamento.
7. **Idempotente depois da policy.** `novo_setor_id` igual à lotação atual
   retorna sem erro — inclusive `None == None`. O early return vem **depois** de
   `exigir_pode_gerir_cadastro`, para não vazar estado de cadastro por diferença
   de resposta a quem não pode gerir. Mesma ordem de `desativar_usuario`.
8. **`novo_setor_id` aceita `None`, e isso expõe uma divergência de contrato.**
   `apps/accounts/models.py` declara `setor` com `null=True, blank=True` e
   comentário explícito ("nula para bootstrap, superusuário técnico e cadastro
   incompleto"), e `_seed_usuarios` em `seed_dev` semeia o ADMIN com
   `'setor': None`. Já o `CONTEXT.md` §12/§170 e o USR-03 da matriz dizem que
   "usuário pertence a exatamente um setor", sem ressalva.
   **A divergência é anterior a este issue e não é resolvida aqui.** O service
   aceita `None` porque o admin hoje permite limpar a lotação (`blank=True`), e
   recusar `None` transformaria uma operação legal em erro — mudança de
   comportamento não pedida pelo issue. Reconciliar `CONTEXT.md`/USR-03 com o
   model é decisão de contrato canônico (ADR ou ajuste do model), registrada
   como follow-up e sinalizada aqui conforme AGENTS.md.

### Roteamento no admin

```python
def save_model(self, request, obj, form, change):
    if change and 'is_active' in form.changed_data and not obj.is_active:
        ...  # ramo existente, inalterado

    if change and 'setor' in form.changed_data:
        from apps.accounts.services import remanejar_usuario
        from apps.core.exceptions import ConflitoDominio

        campos_extras = set(form.changed_data) - {'setor'}
        if campos_extras:
            raise ConflitoDominio(
                'Remaneje a lotação separadamente de outras alterações de cadastro.',
                code='remanejamento_com_campos_extras',
            )
        remanejar_usuario(
            ator_id=request.user.pk,
            usuario_id=obj.pk,
            novo_setor_id=obj.setor_id,
        )
        return  # service já persistiu; super sobrescreveria com os dados do form
    super().save_model(request, obj, form, change)
```

Três decisões:

1. **`return` depois do service — um único ponto de persistência de
   `User.setor`.** Este ramo espelha o de `is_active` em `UserAdmin` e o de
   `ativo` em `SetorAdmin`, não o de `chefe`. Deixar cair no
   `super().save_model` gravaria o objeto inteiro logo depois do service e
   manteria uma segunda mutação de `User.setor` fora da camada de service —
   idempotente na prática, mas em desacordo com `docs/CONVENTIONS.md` e
   ADR-0011, que põem a mutação num ponto só. O `return` fecha isso.
2. **Guard de `campos_extras`.** Consequência direta da decisão 1: com o
   `return`, qualquer outro campo editado no mesmo POST seria descartado em
   silêncio. Recusar explicitamente é o que os dois ramos de desativação já
   fazem, e o custo — remanejar em um POST separado — é o mesmo que o admin já
   paga para desativar usuário ou setor.
3. **Depois do ramo de `is_active`.** Aquele ramo já retorna cedo e já recusa
   `campos_extras`, então um POST que muda `is_active` e `setor` juntos falha
   com `desativacao_com_campos_extras` antes de chegar aqui — comportamento
   atual, preservado.

A tradução para mensagem já existe: `UserAdmin.changeform_view` usa
`_changeform_com_captura_dominio`, que converte `ConflitoDominio` em
`message_user(level=WARNING)` + redirect, `DadosInvalidos` em
`level=ERROR`, e `PermissaoNegada` em `PermissionDenied` (HTTP 403).

## Estratégia de testes

Camada de service, `apps/accounts/tests/test_services.py`, classe
`TestRemanejarUsuario`:

| # | Caso | Esperado |
|---|---|---|
| 1 | Chefe de setor ativo, sem `novo_chefe_id` | `ConflitoDominio`, `code == 'usuario_chefe_remanejado_sem_substituto'`; lotação intacta no banco |
| 2 | Usuário que não chefia nada | `setor_id` vira o novo setor |
| 3 | Chefe de setor ativo com `novo_chefe_id` válido | chefia passa ao substituto **e** lotação muda, na mesma transação |
| 4 | `novo_chefe_id == usuario_id` | `DadosInvalidos`, `code == 'substituto_igual_ao_remanejado'`; chefia e lotação intactas |
| 5 | Chefe de setor **inativo**, sem `novo_chefe_id` | `ConflitoDominio`, mesmo `code`; lotação intacta — cobre a decisão 5 |
| 6 | `novo_setor_id` inexistente | `DadosInvalidos`, `code == 'referencia_invalida'` |
| 7 | `novo_setor_id` igual à lotação atual | no-op sem exceção |
| 8 | Ator não superusuário | `PermissaoNegada`; lotação intacta |
| 9 | Remanejar para `None` usuário sem chefia | `setor_id` vira `None` — cobre a decisão 8 |
| 10 | `trocar_chefe_setor` e depois `remanejar_usuario`, em duas chamadas | passa; é o fluxo que a mensagem de erro do caso 1 instrui |

Casos 2, 1 e 8 são a anatomia obrigatória de ADR-0010 (caminho feliz, violação
de domínio sem escrita, permissão negada sem escrita). O caso 10 é o critério de
aceite "fluxo completo troca-chefia-depois-remaneja funciona" e vale por si: ele
é o contrato que a mensagem do caso 1 promete ao admin, e uma guarda mal escrita
(por exemplo, lendo `Setor.chefe` de um snapshot antigo) o quebraria enquanto o
caso 1 continuaria verde. Os casos 5, 7 e 9 protegem recortes que um refactor
ingênuo desfaria em silêncio — em especial o 5, que é o que impede alguém de
reintroduzir o filtro `ativo=True` na consulta de chefia.

Camada de admin, `apps/accounts/tests/test_admin.py` (o arquivo existe, hoje só
com `SetorAdmin`):

| # | Caso | Esperado |
|---|---|---|
| 11 | `save_model` com `setor` alterado, usuário sem chefia | lotação nova no banco — roteou pelo service |
| 12 | `save_model` com `setor` alterado de um chefe | `ConflitoDominio` propagado; lotação intacta |
| 13 | `save_model` com `setor` e `nome` alterados juntos | `ConflitoDominio`, `code == 'remanejamento_com_campos_extras'`; nada persistido — cobre as decisões 1 e 2 do admin |
| 14 | POST no changeform de um chefe trocando o setor | 302 e mensagem `warning` com o texto exato, não 500 — cobre `_changeform_com_captura_dominio` |

Os testes 11 a 13 chamam `UserAdmin.save_model` diretamente com `RequestFactory`
e o `_FormFake` que o arquivo já define. O 14 usa o `client` de verdade porque o
contrato sob teste é a tradução HTTP, não a decisão de domínio; asserta a
mensagem, porque o 302 sozinho não distingue este redirect do de um save
bem-sucedido.

Não coberto, e por quê: **teste de concorrência com threads**. A suíte roda
contra PostgreSQL, então `select_for_update` tem efeito real e o teste seria
tecnicamente possível com `django_db(transaction=True)` e duas threads — mas o
repositório não tem nenhum teste desse formato (os `transaction=True` de
`apps/notificacoes/tests/test_services.py` existem para `on_commit`, não para
concorrência), a suíte roda em paralelo com `-n logical`, e um teste que depende
de duas transações se entrelaçarem numa ordem específica é a receita clássica de
flake intermitente. O que o lock garante é propriedade do banco, não do código
deste service; o que é do código — a ordem lock → validação → substituição — o
caso 3 já fixa. Também não coberto: divergência pré-existente no banco (fora de
escopo, sem saneamento) e lotação em setor inativo (fora de escopo).

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| USR-04 | "Todo setor operacional ativo possui um chefe ativo." A verificação hoje existe só na designação; o service acrescenta o outro lado — o chefe não sai do setor sem que a chefia saia antes. A linha da matriz ganha o ponto de verificação; a definição não muda. O backlog ACE-002 (setor ativo sem chefe) segue aberto e não é tocado aqui. |
| USR-05 | Reforçada de graça: o caminho com substituto passa por `trocar_chefe_setor`, que já bloqueia `chefe_duplicado`. Nenhuma regra nova. |
| USR-06 | Não muda. Remanejar não ativa nem desativa setor, e a lotação em setor inativo continua permitida como hoje. |
| USR-07 | Não muda. `desativar_usuario` continua o caminho de desativação; os dois services não se chamam. Um chefe pode ser bloqueado por qualquer um dos dois, com mensagens distintas. **Assimetria conhecida:** `desativar_usuario` só bloqueia por setor `ativo=True`, enquanto `remanejar_usuario` bloqueia por qualquer setor chefiado (decisão 5). Alinhar os dois muda comportamento de USR-07 e fica como follow-up. |
| USR-03 | "Usuário pertence a um único setor." Divergente do model, que declara `setor` nulo (decisão 8). O plano sinaliza a divergência e não a resolve; nenhuma linha da matriz é alterada por causa dela. |
| REQ-* | Nenhuma requisição é criada, transicionada ou apagada. O efeito prático é indireto e desejado: o ex-chefe deixa de aparecer como autorizador do setor antigo, porque não fica mais como ex-chefe. |
| EST-* | Nenhum saldo é tocado. |

## Riscos

| Risco | Avaliação |
|---|---|
| Divergência já existente no banco continua vazando autorização | Real e aceito. A guarda é para frente; nenhuma varredura de saneamento entra neste issue. Saneamento é issue própria. |
| Nem todo caminho de escrita de `User.setor` fica guardado | Verificado: fora de fixtures de teste, há dois. O admin, que este plano fecha; e `_seed_usuarios` em `apps/core/management/commands/seed_dev.py`, que grava `setor` num `update_or_create` sem passar por service. O seed fica de fora de propósito — é comando de ambiente local descartável (ADR-0009), com elenco fixo, e grava as chefias **depois** das lotações (`_seed_chefias`), então produz estado consistente por construção. Submetê-lo ao service exigiria um ator superusuário antes de o elenco existir, invertendo a ordem do bootstrap. |
| Leitura fantasma na chefia | O `select_for_update` da decisão 6 fecha a perda de atualização quando a chefia **já existe**. O que resta: se o usuário não chefia nada, não há linha para travar, e uma `trocar_chefe_setor` concorrente pode designá-lo chefe logo após a checagem, sob READ COMMITTED. Aceito — fechar exigiria lock de tabela ou serializar todo o cadastro, e o estado resultante é exatamente o que o próximo remanejamento corrige. |
| `papel_efetivo` segue sem checagem de leitura | Declarado no Escopo. É defesa em profundidade que troca "impedir" por "mascarar", e mudaria o significado de `setor_chefiado_ativo_id` para todo consumidor. Se um dia entrar, entra como issue com revisão das policies que leem esse campo. |
| Chefe de setor inativo fica preso quando não há outro lotado no setor | Real e aceito, e é o preço de bloquear em qualquer setor chefiado (decisão 5). `SetorAdmin` recusa `chefe=None`, então sem outro usuário lotado no setor arquivado não existe substituto e o remanejamento fica travado. Mesmo tipo de travamento que USR-07 já aceita; destravar exige decidir se chefia pode ser removida sem substituto — backlog ACE-002. |
| POST isolado exigido para remanejar | O guard `remanejamento_com_campos_extras` obriga o admin a trocar a lotação separadamente de nome/e-mail/permissões. É custo de UX assumido em troca de um único ponto de persistência de `User.setor` (decisão 1 do admin), e é o mesmo custo que desativar usuário ou setor já cobra. |
| Admin não oferece campo de substituto | Deliberado. O admin recebe o bloqueio com a instrução de trocar a chefia primeiro em `SetorAdmin`; o `novo_chefe_id` do service atende chamadas programáticas. Adicionar campo ao `UserAdmin` é mudança de formulário fora do escopo do issue. |
| Migrations / schema | Nenhuma mudança de model. `make setup` não é necessário. |
| Contrato OpenAPI | Projeto é renderizado no servidor sem camada REST (AGENTS.md). Não se aplica. |
