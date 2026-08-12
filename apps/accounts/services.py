"""Comandos de domínio de accounts — gestão de usuários, setores e vínculos."""

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Setor, User, VinculoAuxiliar
from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import ConflitoDominio, DadosInvalidos


def _travar_setores(**criterios: Q) -> dict[int, Setor]:
    """Trava setores por pk crescente numa única consulta, indexados por pk.

    Ordem canônica de aquisição de locks em `accounts`: primeiro as linhas de
    `Setor`, por pk crescente; depois as de `User`, por pk crescente. Duas
    transações que travem as mesmas linhas em ordens opostas formam um ciclo, e
    o desfecho é `OperationalError` do PostgreSQL — não um erro de domínio.

    Os critérios são combinados por `OR` numa consulta só de propósito: um setor
    pode ser encontrado por `chefe_id` e outro por `pk`, então não há como saber
    os dois pks antes de consultar. Duas consultas travariam em ordem não
    determinística.
    """
    if not criterios:
        # `filter(Q())` travaria a tabela inteira em vez de nenhuma linha.
        raise ValueError('_travar_setores exige ao menos um critério.')
    filtro = Q()
    for parcial in criterios.values():
        filtro |= parcial
    travados = Setor.objects.select_for_update().filter(filtro).order_by('pk')
    return {setor.pk: setor for setor in travados}


def _travar_usuarios(*usuario_ids: int | None) -> dict[int, User]:
    """Trava usuários por pk crescente e devolve os encontrados, indexados por pk.

    Ids ausentes vêm no retorno como chaves faltando; a tradução para
    `DadosInvalidos` fica com o chamador, que sabe quais ids eram obrigatórios.
    """
    ids = sorted({i for i in usuario_ids if i is not None})
    travados = User.objects.select_for_update().filter(pk__in=ids).order_by('pk')
    return {usuario.pk: usuario for usuario in travados}


@transaction.atomic
def trocar_chefe_setor(*, ator_id: int, setor_id: int, novo_chefe_id: int) -> None:
    """Designa novo chefe para um setor (USR-04/USR-05)."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
        Setor.objects.get(pk=setor_id)
        User.objects.get(pk=novo_chefe_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    # Ordem canônica de locks: Setor antes de User.
    setores = _travar_setores(alvo=Q(pk=setor_id))
    usuarios = _travar_usuarios(novo_chefe_id)
    if setor_id not in setores or novo_chefe_id not in usuarios:
        raise DadosInvalidos('Referência inválida.', code='referencia_invalida')
    setor, novo_chefe = setores[setor_id], usuarios[novo_chefe_id]

    if not novo_chefe.is_active:
        raise DadosInvalidos(
            f"Usuário '{novo_chefe.nome}' está inativo e não pode ser designado como chefe.",
            code='chefe_inativo',
        )

    if novo_chefe.setor_id != setor.pk:
        raise DadosInvalidos(
            f"Usuário '{novo_chefe.nome}' não pertence ao setor '{setor.nome}'.",
            code='chefe_setor_errado',
        )

    setor_ja_chefiado = (
        Setor.objects.filter(chefe=novo_chefe).exclude(pk=setor.pk).first()
    )
    if setor_ja_chefiado:
        raise ConflitoDominio(
            f"Usuário '{novo_chefe.nome}' já chefia o setor '{setor_ja_chefiado.nome}'.",
            code='chefe_duplicado',
        )

    setor.chefe = novo_chefe
    setor.save(update_fields=['chefe'])


@transaction.atomic
def desativar_usuario(
    *, ator_id: int, usuario_id: int, novo_chefe_id: int | None = None
) -> None:
    """Desativa usuário, bloqueando se chefe de setor ativo sem substituto (USR-07)."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    # Ordem canônica: Setor antes de User. Antes, o usuário era travado no bloco
    # de validação, acima da policy — ordem inversa à de `trocar_chefe_setor`.
    setores = _travar_setores(chefiado=Q(chefe_id=usuario_id, ativo=True))
    usuarios = _travar_usuarios(usuario_id, novo_chefe_id)
    if usuario_id not in usuarios:
        raise DadosInvalidos('Referência inválida.', code='referencia_invalida')
    usuario = usuarios[usuario_id]

    if not usuario.is_active:
        return

    setor_chefiado = next(iter(setores.values()), None)
    if setor_chefiado:
        if novo_chefe_id is None:
            raise ConflitoDominio(
                f"Usuário '{usuario.nome}' é chefe do setor '{setor_chefiado.nome}'. "
                'Informe um novo chefe antes de desativar.',
                code='usuario_chefe_sem_substituto',
            )
        trocar_chefe_setor(
            ator_id=ator_id,
            setor_id=setor_chefiado.pk,
            novo_chefe_id=novo_chefe_id,
        )

    usuario.is_active = False
    usuario.save(update_fields=['is_active'])


@transaction.atomic
def remanejar_usuario(
    *,
    ator_id: int,
    usuario_id: int,
    novo_setor_id: int | None,
    novo_chefe_id: int | None = None,
) -> None:
    """Muda a lotação, bloqueando se chefia setor sem substituto (USR-04).

    Bloqueia a saída de qualquer chefe de setor, ativo ou inativo — o invariante
    `chefe.setor_id == setor.id` do docstring de `Setor` não é qualificado por
    `ativo`. `desativar_usuario` mantém o recorte `ativo=True`; a assimetria é
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
        (setor for setor in setores.values() if setor.chefe_id == usuario_id), None
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


@transaction.atomic
def desativar_setor(*, ator_id: int, setor_id: int) -> None:
    """Desativa setor, bloqueando se há requisições aguardando autorização (USR-06).

    Requisição em `aguardando_autorizacao` depende de um autorizador do próprio
    setor para seguir; desativar o setor sob ela a deixaria presa. As saídas
    sem autorização — TR-006 e TR-012 — têm criador ou beneficiário como ator,
    não o admin, então o service bloqueia em vez de cascatear.

    Não fecha a corrida com `enviar_para_autorizacao`: o guard de envio lê o
    setor sem lock, de propósito, e o `select_for_update` daqui só serializa
    contra outras escritas de cadastro.
    """
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


@transaction.atomic
def ativar_vinculo_auxiliar(
    *, ator_id: int, usuario_id: int, setor_id: int
) -> VinculoAuxiliar:
    """Cria ou reativa vínculo auxiliar entre usuário e setor."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
        usuario = User.objects.get(pk=usuario_id)
        setor = Setor.objects.get(pk=setor_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    vinculo = (
        VinculoAuxiliar.objects.select_for_update()
        .filter(usuario=usuario, setor=setor)
        .first()
    )
    if vinculo and vinculo.ativo:
        raise ConflitoDominio(
            f"Vínculo auxiliar já está ativo para '{usuario.nome}' no setor '{setor.nome}'.",
            code='vinculo_ja_ativo',
        )

    if vinculo:
        vinculo.ativo = True
        vinculo.desativado_em = None
        vinculo.save(update_fields=['ativo', 'desativado_em'])
    else:
        vinculo = VinculoAuxiliar.objects.create(
            usuario=usuario, setor=setor, ativo=True
        )
    return vinculo


@transaction.atomic
def desativar_vinculo_auxiliar(*, ator_id: int, vinculo_id: int) -> VinculoAuxiliar:
    """Desativa vínculo auxiliar existente."""
    from apps.accounts.policies import exigir_pode_gerir_cadastro

    try:
        ator = User.objects.get(pk=ator_id)
        vinculo = VinculoAuxiliar.objects.select_for_update().get(pk=vinculo_id)
    except ObjectDoesNotExist as exc:
        raise DadosInvalidos(
            'Referência inválida.', code='referencia_invalida'
        ) from exc

    papel = papel_efetivo(ator)
    exigir_pode_gerir_cadastro(papel)

    if not vinculo.ativo:
        raise ConflitoDominio(
            'Vínculo auxiliar já está inativo.',
            code='vinculo_ja_inativo',
        )

    vinculo.ativo = False
    vinculo.desativado_em = timezone.now()
    vinculo.save(update_fields=['ativo', 'desativado_em'])
    return vinculo
