"""Testes de services de requisições (ADR-0010).

3 casos por transição: caminho feliz, estado inválido, permissão negada.
"""

import pytest
from decimal import Decimal

from apps.core.exceptions import DadosInvalidos, EstadoInvalido, PermissaoNegada
from apps.requisicoes.models import EstadoRequisicao, EventoTimeline, Requisicao
from apps.requisicoes.services import (
    criar_requisicao,
    editar_rascunho,
    recusar_requisicao,
    retornar_para_rascunho,
)


# ---------------------------------------------------------------------------
# TR-001: criar_requisicao — caminho feliz
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_requisicao_estado_rascunho(solicitante, material_disponivel):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('5'),
            }
        ],
    )
    assert req.pk is not None
    assert req.estado == EstadoRequisicao.RASCUNHO


@pytest.mark.django_db
def test_criar_requisicao_sem_numero_publico(solicitante, material_disponivel):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    assert req.numero_publico is None


@pytest.mark.django_db
def test_criar_requisicao_snapshot_setor_beneficiario(
    chefe_obras, outro_usuario_obras, setor_obras, material_disponivel
):
    """setor_beneficiario é snapshot do setor do beneficiário no momento da criação."""
    req = criar_requisicao(
        ator_id=chefe_obras.pk,
        beneficiario_id=outro_usuario_obras.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )
    assert req.setor_beneficiario_id == setor_obras.pk
    assert req.criador_id == chefe_obras.pk
    assert req.beneficiario_id == outro_usuario_obras.pk


@pytest.mark.django_db
def test_criar_requisicao_registra_evento_criacao(solicitante, material_disponivel):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('3'),
            }
        ],
    )
    evento = req.eventos.get()
    assert evento.evento == EventoTimeline.CRIACAO
    assert evento.ator_id == solicitante.pk
    assert evento.estado_resultante == EstadoRequisicao.RASCUNHO


@pytest.mark.django_db
def test_criar_requisicao_cria_itens(
    solicitante, material_disponivel, material_disponivel_2
):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('5'),
            },
            {
                'material_id': material_disponivel_2.pk,
                'quantidade_solicitada': Decimal('2'),
            },
        ],
    )
    assert req.itens.count() == 2


# ---------------------------------------------------------------------------
# TR-001: criar_requisicao — permissão negada
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_requisicao_solicitante_nao_pode_criar_para_terceiro(
    solicitante, outro_usuario_obras, material_disponivel
):
    with pytest.raises(PermissaoNegada):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=outro_usuario_obras.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


# ---------------------------------------------------------------------------
# TR-001: criar_requisicao — dados inválidos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_criar_requisicao_sem_itens(solicitante):
    with pytest.raises(DadosInvalidos, match='ao menos um item'):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[],
        )


@pytest.mark.django_db
def test_criar_requisicao_material_inativo(solicitante, material_inativo):
    with pytest.raises(DadosInvalidos):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_inativo.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


@pytest.mark.django_db
def test_criar_requisicao_material_sem_saldo(solicitante, material_sem_saldo):
    with pytest.raises(DadosInvalidos):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_sem_saldo.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


@pytest.mark.django_db
def test_criar_requisicao_material_divergente(solicitante, material_divergente):
    with pytest.raises(DadosInvalidos):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_divergente.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


@pytest.mark.django_db
def test_criar_requisicao_quantidade_zero(solicitante, material_disponivel):
    with pytest.raises(DadosInvalidos, match='Quantidade'):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('0'),
                }
            ],
        )


@pytest.mark.django_db
def test_criar_requisicao_material_duplicado(solicitante, material_disponivel):
    with pytest.raises(DadosInvalidos, match='mesmo material'):
        criar_requisicao(
            ator_id=solicitante.pk,
            beneficiario_id=solicitante.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('1'),
                },
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('2'),
                },
            ],
        )


# ---------------------------------------------------------------------------
# TR-002: editar_rascunho — caminho feliz
# ---------------------------------------------------------------------------


@pytest.fixture
def rascunho(db, solicitante, setor_obras, material_disponivel):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('3'),
            }
        ],
    )
    return req


@pytest.mark.django_db
def test_editar_rascunho_atualiza_itens(
    rascunho, solicitante, material_disponivel, material_disponivel_2
):
    editar_rascunho(
        ator_id=solicitante.pk,
        requisicao_id=rascunho.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('10'),
            },
            {
                'material_id': material_disponivel_2.pk,
                'quantidade_solicitada': Decimal('5'),
            },
        ],
    )
    rascunho.refresh_from_db()
    assert rascunho.itens.count() == 2
    item = rascunho.itens.get(material_id=material_disponivel.pk)
    assert item.quantidade_solicitada == Decimal('10')


@pytest.mark.django_db
def test_editar_rascunho_atualiza_observacao(
    rascunho, solicitante, material_disponivel
):
    editar_rascunho(
        ator_id=solicitante.pk,
        requisicao_id=rascunho.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
        observacao_geral='Nova observação.',
    )
    rascunho.refresh_from_db()
    assert rascunho.observacao_geral == 'Nova observação.'


@pytest.mark.django_db
def test_editar_rascunho_nao_altera_beneficiario(
    rascunho, solicitante, material_disponivel, setor_obras
):
    beneficiario_original = rascunho.beneficiario_id
    setor_original = rascunho.setor_beneficiario_id
    editar_rascunho(
        ator_id=solicitante.pk,
        requisicao_id=rascunho.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )
    rascunho.refresh_from_db()
    assert rascunho.beneficiario_id == beneficiario_original
    assert rascunho.setor_beneficiario_id == setor_original


# ---------------------------------------------------------------------------
# TR-002: editar_rascunho — permissão negada
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_editar_rascunho_nao_criador_levanta_permissao_negada(
    rascunho, outro_usuario_obras, material_disponivel
):
    with pytest.raises(PermissaoNegada):
        editar_rascunho(
            ator_id=outro_usuario_obras.pk,
            requisicao_id=rascunho.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


# ---------------------------------------------------------------------------
# TR-002: editar_rascunho — estado inválido
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_editar_rascunho_estado_invalido(solicitante, setor_obras, material_disponivel):
    req = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-000099',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    # Policy passa (ator é o criador), mas transitions lança EstadoInvalido
    with pytest.raises(EstadoInvalido):
        editar_rascunho(
            ator_id=solicitante.pk,
            requisicao_id=req.pk,
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('1'),
                }
            ],
        )


# ---------------------------------------------------------------------------
# TR-005: enviar_para_autorizacao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enviar_para_autorizacao_emite_numero_publico(rascunho, solicitante):
    from apps.requisicoes.services import enviar_para_autorizacao

    req = enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)
    assert req.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO
    assert req.numero_publico is not None
    from django.utils import timezone

    ano = timezone.now().year
    assert req.numero_publico.startswith(f'REQ-{ano}-')
    assert req.numero_publico == f'REQ-{ano}-{1:06d}'


@pytest.mark.django_db
def test_enviar_sequencia_anual_incrementa(
    solicitante, material_disponivel, material_disponivel_2
):
    from apps.requisicoes.services import enviar_para_autorizacao

    r1 = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    r2 = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel_2.pk,
                'quantidade_solicitada': Decimal('1'),
            }
        ],
    )
    n1 = enviar_para_autorizacao(
        ator_id=solicitante.pk, requisicao_id=r1.pk
    ).numero_publico
    n2 = enviar_para_autorizacao(
        ator_id=solicitante.pk, requisicao_id=r2.pk
    ).numero_publico
    assert int(n1.rsplit('-', 1)[1]) + 1 == int(n2.rsplit('-', 1)[1])


@pytest.mark.django_db
def test_enviar_reenvio_preserva_numero_publico(rascunho, solicitante):
    """Rascunho retornado mantém número público no reenvio (REQ-04)."""
    from apps.requisicoes.services import enviar_para_autorizacao

    req = enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)
    numero_original = req.numero_publico

    # Simula retorno para rascunho preservando o número
    req.estado = EstadoRequisicao.RASCUNHO
    req.save(update_fields=['estado'])

    req2 = enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)
    assert req2.numero_publico == numero_original
    assert req2.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO


@pytest.mark.django_db
def test_enviar_registra_timeline_envio_autorizacao(rascunho, solicitante):
    from apps.requisicoes.services import enviar_para_autorizacao

    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)
    evento = rascunho.eventos.filter(evento=EventoTimeline.ENVIO_AUTORIZACAO).get()
    assert evento.ator_id == solicitante.pk
    assert evento.estado_resultante == EstadoRequisicao.AGUARDANDO_AUTORIZACAO


@pytest.mark.django_db
def test_enviar_sem_itens_levanta_dados_invalidos(solicitante, setor_obras):
    from apps.requisicoes.services import enviar_para_autorizacao

    req = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )
    with pytest.raises(DadosInvalidos, match='ao menos um item'):
        enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)


@pytest.mark.django_db
def test_enviar_em_estado_invalido_levanta_estado_invalido(rascunho, solicitante):
    from apps.requisicoes.services import enviar_para_autorizacao

    rascunho.estado = EstadoRequisicao.AGUARDANDO_AUTORIZACAO
    rascunho.numero_publico = 'REQ-2026-000999'
    rascunho.save(update_fields=['estado', 'numero_publico'])

    with pytest.raises(EstadoInvalido):
        enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)


@pytest.mark.django_db
def test_enviar_por_terceiro_levanta_permissao_negada(rascunho, outro_usuario_obras):
    from apps.requisicoes.services import enviar_para_autorizacao

    with pytest.raises(PermissaoNegada):
        enviar_para_autorizacao(
            ator_id=outro_usuario_obras.pk, requisicao_id=rascunho.pk
        )


@pytest.mark.django_db
def test_enviar_por_criador_inativo_levanta_permissao_negada(rascunho, solicitante):
    from apps.requisicoes.services import enviar_para_autorizacao

    solicitante.is_active = False
    solicitante.save(update_fields=['is_active'])
    with pytest.raises(PermissaoNegada):
        enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)


@pytest.mark.django_db
def test_enviar_nao_reserva_estoque(rascunho, solicitante, material_disponivel):
    from apps.estoque.models import SaldoEstoque
    from apps.requisicoes.services import enviar_para_autorizacao

    saldo_antes = SaldoEstoque.objects.get(material=material_disponivel)
    reservado_antes = saldo_antes.saldo_reservado
    fisico_antes = saldo_antes.saldo_fisico

    enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=rascunho.pk)

    saldo_depois = SaldoEstoque.objects.get(material=material_disponivel)
    assert saldo_depois.saldo_reservado == reservado_antes
    assert saldo_depois.saldo_fisico == fisico_antes


# ---------------------------------------------------------------------------
# TR-006 / TR-011: retorno para rascunho e recusa
# ---------------------------------------------------------------------------


@pytest.fixture
def requisicao_aguardando(solicitante, material_disponivel):
    from apps.requisicoes.services import enviar_para_autorizacao

    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )
    return enviar_para_autorizacao(ator_id=solicitante.pk, requisicao_id=req.pk)


@pytest.mark.django_db
def test_retornar_para_rascunho_preserva_numero_publico_e_registra_timeline(
    requisicao_aguardando, solicitante
):
    numero_original = requisicao_aguardando.numero_publico

    req = retornar_para_rascunho(
        ator_id=solicitante.pk,
        requisicao_id=requisicao_aguardando.pk,
        observacao='Corrigir quantidade.',
    )

    assert req.estado == EstadoRequisicao.RASCUNHO
    assert req.numero_publico == numero_original
    evento = req.eventos.filter(evento=EventoTimeline.RETORNO_RASCUNHO).get()
    assert evento.ator_id == solicitante.pk
    assert evento.estado_resultante == EstadoRequisicao.RASCUNHO
    assert evento.justificativa == 'Corrigir quantidade.'


@pytest.mark.django_db
def test_retornar_para_rascunho_restaura_visibilidade_creator_only(
    aux_obras, solicitante, material_disponivel
):
    from apps.requisicoes.selectors import requisicoes_visiveis_para
    from apps.requisicoes.services import enviar_para_autorizacao

    req = criar_requisicao(
        ator_id=aux_obras.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )
    req = enviar_para_autorizacao(ator_id=aux_obras.pk, requisicao_id=req.pk)

    retornar_para_rascunho(ator_id=solicitante.pk, requisicao_id=req.pk)

    assert req not in list(requisicoes_visiveis_para(solicitante.pk))
    assert req in list(requisicoes_visiveis_para(aux_obras.pk))


@pytest.mark.django_db
def test_retornar_para_rascunho_estado_invalido(solicitante, material_disponivel):
    req = criar_requisicao(
        ator_id=solicitante.pk,
        beneficiario_id=solicitante.pk,
        itens=[
            {
                'material_id': material_disponivel.pk,
                'quantidade_solicitada': Decimal('2'),
            }
        ],
    )

    with pytest.raises(EstadoInvalido):
        retornar_para_rascunho(ator_id=solicitante.pk, requisicao_id=req.pk)


@pytest.mark.django_db
def test_retornar_para_rascunho_terceiro_sem_permissao(
    requisicao_aguardando, usuario_ti
):
    with pytest.raises(PermissaoNegada):
        retornar_para_rascunho(
            ator_id=usuario_ti.pk,
            requisicao_id=requisicao_aguardando.pk,
        )


@pytest.mark.django_db
def test_recusar_requisicao_aplica_estado_e_registra_timeline(
    requisicao_aguardando, chefe_obras
):
    req = recusar_requisicao(
        ator_id=chefe_obras.pk,
        requisicao_id=requisicao_aguardando.pk,
        motivo='Material solicitado precisa de revisão.',
    )

    assert req.estado == EstadoRequisicao.RECUSADA
    evento = req.eventos.filter(evento=EventoTimeline.RECUSA).get()
    assert evento.ator_id == chefe_obras.pk
    assert evento.estado_resultante == EstadoRequisicao.RECUSADA
    assert evento.justificativa == 'Material solicitado precisa de revisão.'


@pytest.mark.django_db
def test_recusar_requisicao_exige_motivo(requisicao_aguardando, chefe_obras):
    with pytest.raises(DadosInvalidos, match='motivo'):
        recusar_requisicao(
            ator_id=chefe_obras.pk,
            requisicao_id=requisicao_aguardando.pk,
            motivo='  ',
        )
    requisicao_aguardando.refresh_from_db()
    assert requisicao_aguardando.estado == EstadoRequisicao.AGUARDANDO_AUTORIZACAO


@pytest.mark.django_db
def test_recusar_requisicao_estado_invalido(requisicao_aguardando, chefe_obras):
    retornar_para_rascunho(
        ator_id=requisicao_aguardando.criador_id,
        requisicao_id=requisicao_aguardando.pk,
    )

    with pytest.raises(EstadoInvalido):
        recusar_requisicao(
            ator_id=chefe_obras.pk,
            requisicao_id=requisicao_aguardando.pk,
            motivo='Não aprovado.',
        )


@pytest.mark.django_db
def test_recusar_requisicao_outro_setor_sem_permissao(
    requisicao_aguardando, chefe_almoxarifado
):
    with pytest.raises(PermissaoNegada):
        recusar_requisicao(
            ator_id=chefe_almoxarifado.pk,
            requisicao_id=requisicao_aguardando.pk,
            motivo='Não aprovado.',
        )


@pytest.mark.django_db
def test_recusar_requisicao_nao_altera_estoque(
    requisicao_aguardando, chefe_obras, material_disponivel
):
    from apps.estoque.models import SaldoEstoque

    saldo_antes = SaldoEstoque.objects.get(material=material_disponivel)
    reservado_antes = saldo_antes.saldo_reservado
    fisico_antes = saldo_antes.saldo_fisico

    recusar_requisicao(
        ator_id=chefe_obras.pk,
        requisicao_id=requisicao_aguardando.pk,
        motivo='Não aprovado.',
    )

    saldo_depois = SaldoEstoque.objects.get(material=material_disponivel)
    assert saldo_depois.saldo_reservado == reservado_antes
    assert saldo_depois.saldo_fisico == fisico_antes
