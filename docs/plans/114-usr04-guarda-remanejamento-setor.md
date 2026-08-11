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
   O plano segue o model — ver decisão 9 — e registra a reconciliação como
   continuação.
2. `remanejar_usuario` bloqueia por qualquer setor chefiado; `desativar_usuario`
   bloqueia só por setor `ativo=True`. A assimetria é deliberada neste recorte —
   ver decisão 5 — e alinhar os dois é continuação, porque muda USR-07.

**Expansão de escopo declarada — ordem de locks.** Este plano passou a alterar
dois services que o issue #114 não menciona: `desativar_usuario` e
`trocar_chefe_setor`. O motivo é que a ordem de aquisição de locks só existe
como propriedade **global**: hoje `desativar_usuario` trava `User` antes de
`Setor`, e `trocar_chefe_setor` trava `Setor` antes de `User` — ordens opostas
no mesmo par de tabelas, o que já hoje admite deadlock entre os dois. Introduzir
um terceiro service que trava as duas tabelas sem unificar a ordem tornaria o
problema maior, e corrigir só o service novo daria aparência de garantia sem
eliminar o ciclo.

A expansão é **de mecânica de locks, não de regra de domínio**: nenhuma
pré-condição, mensagem, código de exceção ou comportamento observável de
`desativar_usuario` e `trocar_chefe_setor` muda, e os testes existentes dos dois
seguem válidos sem edição. Se o mantenedor preferir isolar essa parte em issue
própria, é só remover a seção "Ordem canônica de locks" e as duas linhas
correspondentes abaixo — o resto do plano fica de pé, com o deadlock
permanecendo como risco declarado.

**Muda:**

- `apps/accounts/services.py` — novo
  `remanejar_usuario(*, ator_id, usuario_id, novo_setor_id, novo_chefe_id=None)`;
  novos helpers `_travar_setores` e `_travar_usuarios`; `desativar_usuario`
  passa a travar `Setor` antes de `User` e a usar os helpers;
  `trocar_chefe_setor` passa a usar os helpers (já estava na ordem certa).
- `apps/accounts/admin.py` — `UserAdmin.save_model` roteia a troca de `setor`
  pelo service; `_changeform_com_captura_dominio` passa a traduzir
  `OperationalError` retentável (SQLSTATE `40P01`/`40001`) em mensagem, em vez
  de deixar virar HTTP 500; os demais SQLSTATEs continuam propagando.
- `apps/accounts/tests/test_services.py` — classe `TestRemanejarUsuario`.
- `apps/accounts/tests/test_admin.py` — casos de `UserAdmin` (o arquivo hoje só
  cobre `SetorAdmin`) e os dois casos de contenção seletiva de
  `OperationalError`.
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
| `apps/accounts/services.py` | Helpers `_travar_setores` e `_travar_usuarios`; `remanejar_usuario` após `desativar_usuario`; ordem de locks unificada em `desativar_usuario` e `trocar_chefe_setor` |
| `apps/accounts/admin.py` | Ramo de `setor` em `UserAdmin.save_model`, depois do ramo de `is_active`; captura seletiva de `OperationalError` em `_changeform_com_captura_dominio` |
| `apps/accounts/tests/test_services.py` | `TestRemanejarUsuario` — 14 casos |
| `apps/accounts/tests/test_admin.py` | 6 casos de `UserAdmin` (roteamento, tradução HTTP e contenção seletiva de `OperationalError`); a docstring do módulo hoje só cita o #107 e passa a cobrir os dois admins |
| `docs/matriz-invariantes.md` | Coluna de verificação de USR-04 |

## Implementação

### Ordem canônica de locks (helpers compartilhados)

**A ordem é: todas as linhas de `Setor`, por pk crescente; depois todas as de
`User`, por pk crescente.** Duas transações que travem as mesmas linhas em
ordens opostas formam um ciclo, e o desfecho é `OperationalError` do PostgreSQL
— não um erro de domínio. Ordenar remove o ciclo.

```python
def _travar_setores(**criterios: Q) -> dict[int, Setor]:
    """Trava setores por pk crescente numa única consulta, indexados por pk."""
    filtro = Q()
    for parcial in criterios.values():
        filtro |= parcial
    travados = Setor.objects.select_for_update().filter(filtro).order_by('pk')
    return {s.pk: s for s in travados}


def _travar_usuarios(*usuario_ids: int | None) -> dict[int, User]:
    """Trava usuários por pk crescente e devolve os encontrados, indexados por pk.

    Ids ausentes vêm no retorno como chaves faltando; a tradução para
    `DadosInvalidos` fica com o chamador, que sabe quais ids eram obrigatórios.
    """
    ids = sorted({i for i in usuario_ids if i is not None})
    travados = User.objects.select_for_update().filter(pk__in=ids).order_by('pk')
    return {u.pk: u for u in travados}
```

Os setores são travados em **uma consulta só**, com os critérios combinados por
`OR`. Isso não é detalhe de estilo: o setor chefiado é encontrado por
`chefe_id`, e o de destino por `pk`, então não dá para saber os dois pks antes
de consultar. Duas consultas travariam em ordem não determinística; uma consulta
com `ORDER BY pk` trava as duas linhas na ordem canônica, e a busca por
`chefe_id` continua sendo feita **sob lock**, sem TOCTOU.

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
    """Muda a lotação, bloqueando se chefia setor sem substituto (USR-04).

    Bloqueia a saída de qualquer chefe de setor, ativo ou inativo — o
    invariante `chefe.setor_id == setor.id` não é qualificado por `ativo`.
    `desativar_usuario` mantém o recorte `ativo=True`; a assimetria é
    deliberada e está declarada no plano do #114.
    """
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    # Ordem canônica: Setor antes de User, cada grupo por pk crescente.
    setores = _travar_setores(
        chefiado=Q(chefe_id=usuario_id),
        destino=Q(pk=novo_setor_id) if novo_setor_id is not None else Q(pk__in=[]),
    )
    if novo_setor_id is not None and novo_setor_id not in setores:
        raise DadosInvalidos('Referência inválida.', code='referencia_invalida')
    setor_chefiado = next(
        (s for s in setores.values() if s.chefe_id == usuario_id), None
    )

    usuarios = _travar_usuarios(usuario_id, novo_chefe_id)
    obrigatorios = {usuario_id} | ({novo_chefe_id} - {None})
    if not obrigatorios <= usuarios.keys():
        raise DadosInvalidos('Referência inválida.', code='referencia_invalida')
    usuario = usuarios[usuario_id]

    if usuario.setor_id == novo_setor_id:
        return

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

Nove decisões que o código embute:

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
   do escopo deste issue, e fica registrada como continuação.
   **Saída para o caso preso:** um chefe de setor inativo sem nenhum outro
   usuário lotado nele não tem substituto possível e fica sem remanejamento pelo
   admin (`SetorAdmin` recusa `chefe=None` com `chefe_nulo`). É o mesmo tipo de
   travamento que USR-07 já aceita, e resolvê-lo exige decidir se chefia pode
   ser removida sem substituto — questão do backlog ACE-002, não deste issue.
6. **`select_for_update` no setor chefiado, antes de decidir — e `Setor` antes
   de `User`.** Sem o lock, uma `trocar_chefe_setor` concorrente pode designar
   outro chefe entre a leitura e o commit, e a chamada de substituição daqui
   sobrescreveria essa designação — perda de atualização. Com o lock, quando
   existe chefia a decidir, as duas escritas serializam.

   A **ordem** dos locks é escolha deliberada. `trocar_chefe_setor` trava
   `Setor` e só depois `User` (o novo chefe). Se este service travasse o
   `usuario` primeiro — como faz `desativar_usuario` hoje — teríamos duas ordens
   opostas no mesmo par de tabelas, que é a receita de deadlock: uma transação
   segurando `User` e esperando `Setor`, outra segurando `Setor` e esperando
   `User`. Daí a ordem canônica: `Setor` primeiro, `User` depois.

   O ciclo `User`×`User` — dois chefes indicados como substituto um do outro —
   é fechado pelo `_travar_usuarios`, que trava por pk crescente e é usado pelos
   três services. Como o helper trava os dois usuários de uma vez, a chamada a
   `trocar_chefe_setor` de dentro do fluxo já encontra os locks adquiridos e não
   introduz ordem nova. O ciclo `Setor`×`Setor` — chefiado e destino — é fechado
   pela consulta única de `_travar_setores`, com `ORDER BY pk`.

   **O que ainda não está resolvido:** a leitura fantasma. Se o usuário ainda
   **não** é chefe de nada, não há linha de `Setor` para travar, e uma
   `trocar_chefe_setor` concorrente pode torná-lo chefe logo após a checagem
   (READ COMMITTED). Fechar exigiria lock de tabela; o desfecho é o mesmo estado
   que este issue corrige no próximo remanejamento. Não é deadlock — é janela de
   escrita perdida, e não produz HTTP 500.
7. **Toda referência é validada sob lock, e a validação preliminar sai.** A
   versão anterior deste plano validava existência sem lock e só conferia
   `usuario_id` depois. Isso deixava dois furos: um `novo_chefe_id` inexistente
   passava batido quando o usuário não chefiava nada (o ramo que chamaria
   `trocar_chefe_setor` nunca rodava), e o setor de destino podia ser apagado
   entre a validação e o `UPDATE`, virando `IntegrityError` em vez de erro de
   domínio. Agora não há validação preliminar de `usuario_id`, `novo_chefe_id`
   ou `novo_setor_id`: os três são conferidos **depois** dos locks, contra as
   chaves que os helpers devolveram. Referência que não existe — ou que deixou
   de existir na janela — recebe `DadosInvalidos(code='referencia_invalida')`,
   o mesmo código nos dois casos: para quem chamou, a referência era inválida, e
   o instante em que deixou de existir não muda a resposta. Só `ator_id`
   continua fora, porque não é travado nem mutado, só lido para derivar o papel.
8. **Idempotente depois da policy.** `novo_setor_id` igual à lotação atual
   retorna sem erro — inclusive `None == None`. O early return vem **depois** de
   `exigir_pode_gerir_cadastro`, para não vazar estado de cadastro por diferença
   de resposta a quem não pode gerir. Mesma ordem de `desativar_usuario`.
9. **`novo_setor_id` aceita `None`, e isso expõe uma divergência de contrato.**
   `apps/accounts/models.py` declara `setor` com `null=True, blank=True` e
   comentário explícito ("nula para bootstrap, superusuário técnico e cadastro
   incompleto"), e `_seed_usuarios` em `seed_dev` semeia o ADMIN com
   `'setor': None`. Já o `CONTEXT.md` 12/170 e o USR-03 da matriz dizem que
   "usuário pertence a exatamente um setor", sem ressalva.
   **A divergência é anterior a este issue e não é resolvida aqui.** O service
   aceita `None` porque o admin hoje permite limpar a lotação (`blank=True`), e
   recusar `None` transformaria uma operação legal em erro — mudança de
   comportamento não pedida pelo issue. Reconciliar `CONTEXT.md`/USR-03 com o
   model é decisão de contrato canônico (ADR ou ajuste do model), registrada
   como continuação e sinalizada aqui conforme AGENTS.md.

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

### Contenção de deadlock no admin

`_changeform_com_captura_dominio` ganha um ramo para `OperationalError`:

```python
# 40P01 deadlock_detected, 40001 serialization_failure: a transação foi abortada
# por concorrência e a mesma operação, repetida, tende a passar.
SQLSTATES_RETENTAVEIS = frozenset({'40P01', '40001'})

except OperationalError as exc:
    if getattr(exc.__cause__, 'sqlstate', None) not in SQLSTATES_RETENTAVEIS:
        raise  # conexão caída, disco cheio etc.: não é retentável, não mascarar
    logger.warning('remanejamento abortado por concorrência', exc_info=exc)
    admin_instance.message_user(
        request,
        'A operação não pôde ser concluída por concorrência com outra '
        'alteração de cadastro. Tente novamente.',
        level=messages.ERROR,
    )
    return HttpResponseRedirect(request.get_full_path())
```

Três observações. O ramo é **contenção, não prevenção** — a prevenção é a ordem
canônica de locks; isto existe para o caso em que um ciclo escape mesmo assim.
A captura é **restrita por SQLSTATE**: `OperationalError` cobre desde deadlock
até queda de conexão, e dizer "tente novamente" para um banco fora do ar seria
transformar indisponibilidade em erro de formulário — por isso o que não for
`40P01`/`40001` é propagado, e vira o 500 que de fato é. E o ramo vale para os
três admins do módulo, não só para `UserAdmin`, porque a função é compartilhada:
`SetorAdmin` e `VinculoAuxiliarAdmin` passam a ter a mesma contenção sem
mudança de comportamento em nenhum caminho que hoje funciona.

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
| 9 | Remanejar para `None` usuário sem chefia | `setor_id` vira `None` — cobre a decisão 9 |
| 10 | `trocar_chefe_setor` e depois `remanejar_usuario`, em duas chamadas | passa; é o fluxo que a mensagem de erro do caso 1 instrui |
| 11 | `usuario_id` inexistente | `DadosInvalidos`, `code == 'referencia_invalida'` |
| 12 | Usuário apagado **durante** a consulta de setores, antes do lock de `User` | `DadosInvalidos`, `code == 'referencia_invalida'`, não `KeyError`/HTTP 500 — cobre a decisão 7 |
| 13 | `novo_chefe_id` inexistente, usuário que **não** chefia nada | `DadosInvalidos`, `code == 'referencia_invalida'`; lotação intacta. Sem a conferência de todas as chaves obrigatórias, o ramo de chefia nunca roda e o id inválido passa batido |
| 14 | Setor de destino apagado **durante** a consulta de setores | `DadosInvalidos`, `code == 'referencia_invalida'`, não `IntegrityError` |

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
| 15 | `save_model` com `setor` alterado, usuário sem chefia | lotação nova no banco — roteou pelo service |
| 16 | `save_model` com `setor` alterado de um chefe | `ConflitoDominio` propagado; lotação intacta |
| 17 | `save_model` com `setor` e `nome` alterados juntos | `ConflitoDominio`, `code == 'remanejamento_com_campos_extras'`; nada persistido — cobre as decisões 1 e 2 do admin |
| 18 | POST no changeform de um chefe trocando o setor | 302 e mensagem `warning` com o texto exato, não 500 — cobre `_changeform_com_captura_dominio` |
| 19a | `save_model` levantando `OperationalError` com SQLSTATE `40P01` (service com `monkeypatch`) | 302 e mensagem de erro, não 500 — cobre a contenção nova |
| 19b | Idem, com SQLSTATE não retentável | exceção **propaga**; a captura não mascara indisponibilidade de banco |

Os testes 15 a 17 chamam `UserAdmin.save_model` diretamente com `RequestFactory`
e o `_FormFake` que o arquivo já define. Os 18 e 19 usam o `client` de verdade
porque o contrato sob teste é a tradução HTTP, não a decisão de domínio; ambos
assertam a mensagem, porque o 302 sozinho não distingue esses redirects do de um
save bem-sucedido.

Os casos 12, 14 e 19 substituem o teste concorrente com threads, e são melhores
para o que precisa ser fixado. Os 12 e 14 usam `monkeypatch` para apagar o
usuário e o setor de destino durante a consulta de setores, reproduzindo as duas
corridas de forma determinística; o 19 faz o service levantar `OperationalError`
para exercitar a contenção no admin. Os três rodam em qualquer ordem e não
dependem de duas transações se entrelaçarem.

O 19 tem duas variantes, porque a captura é seletiva: `OperationalError` com
SQLSTATE `40P01` vira mensagem e 302; com um SQLSTATE não retentável (conexão
caída, por exemplo) a exceção **propaga**. Testar só a primeira deixaria passar
uma captura larga demais, que transformaria indisponibilidade de banco em erro
de formulário.

Não coberto, e por quê: **deadlock real com duas transações em paralelo**. A
suíte roda contra PostgreSQL, então seria tecnicamente possível com
`django_db(transaction=True)` e threads, mas o repositório não tem nenhum teste
desse formato (os `transaction=True` de `apps/notificacoes/tests/test_services.py`
existem para `on_commit`, não para concorrência), a suíte roda em paralelo com
`-n logical`, e um teste que depende de duas transações se entrelaçarem numa
ordem específica é a receita clássica de flake intermitente. O que ficou coberto
é o que é do código: a **ordem** de aquisição (helpers únicos, usados pelos três
services, que ordenam por pk) e o **desfecho** caso um ciclo ainda ocorra (caso
19, sem HTTP 500). O escalonamento em si é propriedade do banco. Também não
coberto: divergência pré-existente no banco (fora de escopo, sem saneamento) e
lotação em setor inativo (fora de escopo).

## Invariantes

| ID | Relação com esta mudança |
|---|---|
| USR-04 | "Todo setor operacional ativo possui um chefe ativo." A verificação hoje existe só na designação; o service acrescenta o outro lado — o chefe não sai do setor sem que a chefia saia antes. A linha da matriz ganha o ponto de verificação; a definição não muda. O backlog ACE-002 (setor ativo sem chefe) segue aberto e não é tocado aqui. |
| USR-05 | Reforçada de graça: o caminho com substituto passa por `trocar_chefe_setor`, que já bloqueia `chefe_duplicado`. Nenhuma regra nova. |
| USR-06 | Não muda. Remanejar não ativa nem desativa setor, e a lotação em setor inativo continua permitida como hoje. |
| USR-07 | Não muda. `desativar_usuario` continua o caminho de desativação; os dois services não se chamam. Um chefe pode ser bloqueado por qualquer um dos dois, com mensagens distintas. **Assimetria conhecida:** `desativar_usuario` só bloqueia por setor `ativo=True`, enquanto `remanejar_usuario` bloqueia por qualquer setor chefiado (decisão 5). Alinhar os dois muda comportamento de USR-07 e fica como continuação. |
| USR-03 | "Usuário pertence a um único setor." Divergente do model, que declara `setor` nulo (decisão 8). O plano sinaliza a divergência e não a resolve; nenhuma linha da matriz é alterada por causa dela. |
| REQ-* | Nenhuma requisição é criada, transicionada ou apagada. O efeito prático é indireto e desejado: o ex-chefe deixa de aparecer como autorizador do setor antigo, porque não fica mais como ex-chefe. |
| EST-* | Nenhum saldo é tocado. |

## Riscos

| Risco | Avaliação |
|---|---|
| Divergência já existente no banco continua vazando autorização | Real e aceito. A guarda é para frente; nenhuma varredura de saneamento entra neste issue. Saneamento é issue própria. |
| Nem todo caminho de escrita de `User.setor` fica guardado | Verificado: fora de fixtures de teste, há dois. O admin, que este plano fecha; e `_seed_usuarios` em `apps/core/management/commands/seed_dev.py`, que grava `setor` num `update_or_create` sem passar por service. O seed **não** é declarado autorizado por este plano — ele é uma exceção pré-existente ao contrato de `docs/CONVENTIONS.md`, que este issue nem cria nem legitima. Fica de fora por três motivos de fato: é comando de ambiente local descartável (ADR-0009), tem elenco fixo, e grava as chefias **depois** das lotações (`_seed_chefias`), produzindo estado consistente por construção. Submetê-lo ao service esbarra na ordem do bootstrap — exigiria um ator superusuário antes de o elenco existir. Formalizar a exceção em ADR-0009 e `docs/CONVENTIONS.md`, ou dar ao seed um caminho de service próprio, é decisão de contrato registrada como continuação. |
| Leitura fantasma na chefia | O `select_for_update` da decisão 6 fecha a perda de atualização quando a chefia **já existe**. O que resta: se o usuário não chefia nada, não há linha para travar, e uma `trocar_chefe_setor` concorrente pode designá-lo chefe logo após a checagem, sob READ COMMITTED. Aceito — fechar exigiria lock de tabela ou serializar todo o cadastro, e o estado resultante é exatamente o que o próximo remanejamento corrige. |
| Deadlock por ordem de locks | Endereçado nas duas pontas, com expansão de escopo declarada no Escopo. **Prevenção:** ordem canônica única — `Setor`, depois `User` por pk crescente — aplicada aos três services via `_travar_usuarios`, o que elimina o ciclo `User`×`Setor` e o ciclo `User`×`User`. Isso corrige de passagem a ordem invertida que `desativar_usuario` já tinha antes deste issue. **Contenção:** `_changeform_com_captura_dominio` passa a traduzir `OperationalError`, então mesmo um ciclo remanescente vira mensagem, não HTTP 500. O que continua sem cobertura é o escalonamento concorrente em si, por ser propriedade do banco e teste inerentemente flaky — ver Estratégia de testes. |
| Expansão de escopo para `desativar_usuario` e `trocar_chefe_setor` | Assumida e declarada. Restrita a mecânica de locks: nenhuma pré-condição, mensagem ou código de exceção muda, e os testes existentes dos dois services continuam válidos sem edição. O risco residual é o de qualquer mudança em service com uso estabelecido — mitigado por a suíte inteira ter de passar antes do merge, e reversível removendo o helper e as duas chamadas. |
| `papel_efetivo` segue sem checagem de leitura | Declarado no Escopo. É defesa em profundidade que troca "impedir" por "mascarar", e mudaria o significado de `setor_chefiado_ativo_id` para todo consumidor. Se um dia entrar, entra como issue com revisão das policies que leem esse campo. |
| Chefe de setor inativo fica preso quando não há outro lotado no setor | Real e aceito, e é o preço de bloquear em qualquer setor chefiado (decisão 5). `SetorAdmin` recusa `chefe=None`, então sem outro usuário lotado no setor arquivado não existe substituto e o remanejamento fica travado. Mesmo tipo de travamento que USR-07 já aceita; destravar exige decidir se chefia pode ser removida sem substituto — backlog ACE-002. |
| POST isolado exigido para remanejar | O guard `remanejamento_com_campos_extras` obriga o admin a trocar a lotação separadamente de nome/e-mail/permissões. É custo de UX assumido em troca de um único ponto de persistência de `User.setor` (decisão 1 do admin), e é o mesmo custo que desativar usuário ou setor já cobra. |
| Admin não oferece campo de substituto | Deliberado. O admin recebe o bloqueio com a instrução de trocar a chefia primeiro em `SetorAdmin`; o `novo_chefe_id` do service atende chamadas programáticas. Adicionar campo ao `UserAdmin` é mudança de formulário fora do escopo do issue. |
| Migrations / schema | Nenhuma mudança de model. `make setup` não é necessário. |
| Contrato OpenAPI | Projeto é renderizado no servidor sem camada REST (AGENTS.md). Não se aplica. |
