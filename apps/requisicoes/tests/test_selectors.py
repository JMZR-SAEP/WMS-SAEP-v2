"""Testes unitários para seletores de requisições."""

from datetime import date
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.papeis import PapelEfetivo
from apps.requisicoes.models import EstadoRequisicao, Operacao, Requisicao
from apps.requisicoes.selectors import (
    acoes_disponiveis,
    chefe_autorizador_do_setor,
    fila_atendimento,
    fila_autorizacao,
    filtrar_historico_requisicoes,
    historico_requisicoes_visiveis_para,
    material_eh_elegivel,
    materiais_para_requisicao,
    minhas_requisicoes,
    pode_filtrar_historico_por_setor,
    requisicoes_visiveis_para,
    saldos_por_materiais,
    setores_do_historico,
)


@pytest.mark.django_db
def test_materiais_para_requisicao_inclui_disponivel(material_disponivel):
    assert material_disponivel in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_inativo(material_inativo):
    assert material_inativo not in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_sem_saldo(material_sem_saldo):
    assert material_sem_saldo not in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_divergente(material_divergente):
    assert material_divergente not in materiais_para_requisicao()


@pytest.mark.django_db
def test_material_eh_elegivel_true_se_disponivel(material_disponivel):
    assert material_eh_elegivel(material_disponivel)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_inativo(material_inativo):
    assert not material_eh_elegivel(material_inativo)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_sem_saldo(material_sem_saldo):
    assert not material_eh_elegivel(material_sem_saldo)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_divergente(material_divergente):
    assert not material_eh_elegivel(material_divergente)


# ---------------------------------------------------------------------------
# Fixtures de requisições para testes de visibilidade
# ---------------------------------------------------------------------------


@pytest.fixture
def req_solicitante_rascunho(db, solicitante, setor_obras):
    """Rascunho criado pelo solicitante para si."""
    return Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_solicitante_enviada(db, solicitante, setor_obras):
    """Requisição enviada pelo solicitante para si."""
    return Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0001',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_aux_para_solicitante_rascunho(db, aux_obras, solicitante, setor_obras):
    """Rascunho criado pelo auxiliar em nome do solicitante (beneficiário)."""
    return Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=aux_obras,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_aux_para_solicitante_enviada(db, aux_obras, solicitante, setor_obras):
    """Enviada pelo aux em nome do solicitante."""
    return Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0002',
        criador=aux_obras,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_outro_setor(db, usuario_ti, setor_ti):
    """Requisição enviada em outro setor (TI)."""
    return Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0003',
        criador=usuario_ti,
        beneficiario=usuario_ti,
        setor_beneficiario=setor_ti,
    )


# ---------------------------------------------------------------------------
# requisicoes_visiveis_para — por papel
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_visiveis_solicitante_ve_proprias_como_criador(
    solicitante, req_solicitante_rascunho, req_solicitante_enviada, req_outro_setor
):
    vis = list(requisicoes_visiveis_para(solicitante.pk))
    assert req_solicitante_rascunho in vis
    assert req_solicitante_enviada in vis
    assert req_outro_setor not in vis


@pytest.mark.django_db
def test_visiveis_solicitante_nao_ve_rascunho_de_terceiro_onde_eh_beneficiario(
    solicitante, req_aux_para_solicitante_rascunho
):
    vis = list(requisicoes_visiveis_para(solicitante.pk))
    assert req_aux_para_solicitante_rascunho not in vis


@pytest.mark.django_db
def test_visiveis_solicitante_ve_enviada_onde_eh_beneficiario(
    solicitante, req_aux_para_solicitante_enviada
):
    vis = list(requisicoes_visiveis_para(solicitante.pk))
    assert req_aux_para_solicitante_enviada in vis


@pytest.mark.django_db
def test_visiveis_aux_setor_nao_ve_setor_inteiro(
    aux_obras, req_solicitante_enviada, req_outro_setor
):
    vis = list(requisicoes_visiveis_para(aux_obras.pk))
    assert req_solicitante_enviada not in vis
    assert req_outro_setor not in vis


@pytest.mark.django_db
def test_visiveis_chefe_setor_ve_setor_exceto_rascunho_de_terceiro(
    chefe_obras,
    req_solicitante_rascunho,
    req_solicitante_enviada,
    req_outro_setor,
):
    vis = list(requisicoes_visiveis_para(chefe_obras.pk))
    assert req_solicitante_enviada in vis
    assert req_solicitante_rascunho not in vis
    assert req_outro_setor not in vis


@pytest.mark.django_db
def test_visiveis_aux_almox_ve_todas_exceto_rascunho_de_terceiro(
    aux_almoxarifado,
    req_solicitante_rascunho,
    req_solicitante_enviada,
    req_outro_setor,
):
    vis = list(requisicoes_visiveis_para(aux_almoxarifado.pk))
    assert req_solicitante_enviada in vis
    assert req_outro_setor in vis
    assert req_solicitante_rascunho not in vis


@pytest.mark.django_db
def test_visiveis_chefe_almox_ve_todas_exceto_rascunho_de_terceiro(
    chefe_almoxarifado,
    req_solicitante_rascunho,
    req_solicitante_enviada,
    req_outro_setor,
):
    vis = list(requisicoes_visiveis_para(chefe_almoxarifado.pk))
    assert req_solicitante_enviada in vis
    assert req_outro_setor in vis
    assert req_solicitante_rascunho not in vis


@pytest.mark.django_db
def test_visiveis_superuser_ve_tudo(
    db,
    setor_obras,
    req_solicitante_rascunho,
    req_solicitante_enviada,
    req_outro_setor,
):
    su = User.objects.create_superuser(
        matricula='999', nome='Super', password='senha', setor=setor_obras
    )
    vis = list(requisicoes_visiveis_para(su.pk))
    assert req_solicitante_rascunho in vis
    assert req_solicitante_enviada in vis
    assert req_outro_setor in vis


@pytest.mark.django_db
def test_visiveis_inativo_vazio(usuario_inativo, req_solicitante_enviada):
    assert list(requisicoes_visiveis_para(usuario_inativo.pk)) == []


@pytest.mark.django_db
def test_visiveis_ator_inexistente_vazio(req_solicitante_enviada):
    assert list(requisicoes_visiveis_para(999999)) == []


# ---------------------------------------------------------------------------
# minhas_requisicoes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_minhas_inclui_propria_rascunho_e_enviada(
    solicitante, req_solicitante_rascunho, req_solicitante_enviada
):
    minhas = list(minhas_requisicoes(solicitante.pk))
    assert req_solicitante_rascunho in minhas
    assert req_solicitante_enviada in minhas


@pytest.mark.django_db
def test_minhas_inclui_onde_eh_beneficiario_fora_rascunho(
    solicitante, req_aux_para_solicitante_enviada
):
    minhas = list(minhas_requisicoes(solicitante.pk))
    assert req_aux_para_solicitante_enviada in minhas


@pytest.mark.django_db
def test_minhas_exclui_rascunho_de_terceiro_onde_eh_beneficiario(
    solicitante, req_aux_para_solicitante_rascunho
):
    minhas = list(minhas_requisicoes(solicitante.pk))
    assert req_aux_para_solicitante_rascunho not in minhas


@pytest.mark.django_db
def test_minhas_chefe_setor_nao_inclui_terceiros_do_setor(
    chefe_obras, req_solicitante_enviada
):
    minhas = list(minhas_requisicoes(chefe_obras.pk))
    assert req_solicitante_enviada not in minhas


@pytest.mark.django_db
def test_minhas_ordenadas_por_criado_em_desc(
    solicitante, req_solicitante_rascunho, req_solicitante_enviada
):
    minhas = list(minhas_requisicoes(solicitante.pk))
    criado_ems = [r.criado_em for r in minhas]
    assert criado_ems == sorted(criado_ems, reverse=True)


# ---------------------------------------------------------------------------
# fila_autorizacao
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fila_autorizacao_chefe_setor_ve_apenas_setor_chefiado(
    chefe_obras, req_solicitante_enviada, req_outro_setor
):
    fila = list(fila_autorizacao(chefe_obras.pk))
    assert req_solicitante_enviada in fila
    assert req_outro_setor not in fila


@pytest.mark.django_db
def test_fila_autorizacao_exclui_estados_fora_de_aguardando(
    chefe_obras, req_solicitante_enviada
):
    req_solicitante_enviada.estado = EstadoRequisicao.RASCUNHO
    req_solicitante_enviada.save(update_fields=['estado'])
    assert list(fila_autorizacao(chefe_obras.pk)) == []


@pytest.mark.django_db
def test_fila_autorizacao_chefe_almox_ve_apenas_setor_almox(
    chefe_almoxarifado,
    setor_almoxarifado,
    req_solicitante_enviada,
):
    req_almox = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0100',
        criador=chefe_almoxarifado,
        beneficiario=chefe_almoxarifado,
        setor_beneficiario=setor_almoxarifado,
    )
    fila = list(fila_autorizacao(chefe_almoxarifado.pk))
    assert req_almox in fila
    assert req_solicitante_enviada not in fila


@pytest.mark.django_db
def test_fila_autorizacao_superuser_ve_todos_setores(
    db, setor_obras, req_solicitante_enviada, req_outro_setor
):
    su = User.objects.create_superuser(
        matricula='990', nome='Super Fila', password='senha', setor=setor_obras
    )
    fila = list(fila_autorizacao(su.pk))
    assert req_solicitante_enviada in fila
    assert req_outro_setor in fila


@pytest.mark.django_db
def test_fila_autorizacao_auxiliar_almox_vazia(
    aux_almoxarifado, req_solicitante_enviada
):
    assert list(fila_autorizacao(aux_almoxarifado.pk)) == []


@pytest.mark.django_db
def test_fila_autorizacao_anota_quantidade_itens(
    chefe_obras, req_solicitante_enviada, material_disponivel
):
    req_solicitante_enviada.itens.create(
        material=material_disponivel,
        quantidade_solicitada=1,
    )
    req = fila_autorizacao(chefe_obras.pk).get(pk=req_solicitante_enviada.pk)
    assert req.quantidade_itens == 1


@pytest.mark.django_db
def test_fila_autorizacao_anota_primeiro_material(
    chefe_obras, req_solicitante_enviada, material_disponivel, material_disponivel_2
):
    """O cartão da fila precisa nomear o que foi pedido.

    "Itens: 4" é um dígito, e o chefe de setor autoriza — e reserva saldo — sem
    saber o conteúdo. A fila de atendimento já anotava o primeiro material pelo
    mesmo motivo; a de autorização ficou de fora quando a correção foi feita.
    """
    req_solicitante_enviada.itens.create(
        material=material_disponivel, quantidade_solicitada=1
    )
    req_solicitante_enviada.itens.create(
        material=material_disponivel_2, quantidade_solicitada=2
    )
    req = fila_autorizacao(chefe_obras.pk).get(pk=req_solicitante_enviada.pk)
    assert req.primeiro_material_nome == material_disponivel.nome
    assert req.quantidade_itens == 2


# ---------------------------------------------------------------------------
# fila_atendimento
# ---------------------------------------------------------------------------


@pytest.fixture
def req_autorizada_obras(db, solicitante, setor_obras):
    return Requisicao.objects.create(
        estado=EstadoRequisicao.AUTORIZADA,
        numero_publico='REQ-2026-0100',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_pronta_obras(db, solicitante, setor_obras):
    return Requisicao.objects.create(
        estado=EstadoRequisicao.PRONTA_PARA_RETIRADA,
        numero_publico='REQ-2026-0101',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.fixture
def req_atendida_obras(db, solicitante, setor_obras):
    return Requisicao.objects.create(
        estado=EstadoRequisicao.ATENDIDA,
        numero_publico='REQ-2026-0102',
        criador=solicitante,
        beneficiario=solicitante,
        setor_beneficiario=setor_obras,
    )


@pytest.mark.django_db
def test_fila_atendimento_aux_almox_ve_autorizada_e_pronta(
    aux_almoxarifado, req_autorizada_obras, req_pronta_obras
):
    fila = list(fila_atendimento(aux_almoxarifado.pk))
    assert req_autorizada_obras in fila
    assert req_pronta_obras in fila


@pytest.mark.django_db
def test_fila_atendimento_chefe_almox_ve_autorizada_e_pronta(
    chefe_almoxarifado, req_autorizada_obras, req_pronta_obras
):
    fila = list(fila_atendimento(chefe_almoxarifado.pk))
    assert req_autorizada_obras in fila
    assert req_pronta_obras in fila


@pytest.mark.django_db
def test_fila_atendimento_exclui_outros_estados(
    aux_almoxarifado,
    req_solicitante_enviada,
    req_atendida_obras,
):
    fila = list(fila_atendimento(aux_almoxarifado.pk))
    assert req_solicitante_enviada not in fila
    assert req_atendida_obras not in fila


@pytest.mark.django_db
def test_fila_atendimento_chefe_setor_vazia(
    chefe_obras, req_autorizada_obras, req_pronta_obras
):
    assert list(fila_atendimento(chefe_obras.pk)) == []


@pytest.mark.django_db
def test_fila_atendimento_solicitante_vazia(
    solicitante, req_autorizada_obras, req_pronta_obras
):
    assert list(fila_atendimento(solicitante.pk)) == []


@pytest.mark.django_db
def test_fila_atendimento_superuser_ve_tudo(
    superuser, req_autorizada_obras, req_pronta_obras
):
    fila = list(fila_atendimento(superuser.pk))
    assert req_autorizada_obras in fila
    assert req_pronta_obras in fila


@pytest.mark.django_db
def test_fila_atendimento_inativo_vazia(usuario_inativo, req_autorizada_obras):
    assert list(fila_atendimento(usuario_inativo.pk)) == []


@pytest.mark.django_db
def test_fila_atendimento_ator_inexistente_vazia(req_autorizada_obras):
    assert list(fila_atendimento(999_999)) == []


@pytest.mark.django_db
def test_fila_atendimento_anota_quantidade_itens(
    aux_almoxarifado, req_autorizada_obras, material_disponivel
):
    req_autorizada_obras.itens.create(
        material=material_disponivel,
        quantidade_solicitada=1,
    )
    req = fila_atendimento(aux_almoxarifado.pk).get(pk=req_autorizada_obras.pk)
    assert req.quantidade_itens == 1


# ---------------------------------------------------------------------------
# acoes_disponiveis — puro, sem DB (papel × estado)
# ---------------------------------------------------------------------------

ATOR_ID = 1
SETOR_BENEFICIARIO_ID = 10


def _papel(**kwargs) -> PapelEfetivo:
    defaults = dict(
        ativo=True,
        eh_superusuario=False,
        eh_almoxarifado=False,
        eh_chefe_de_almoxarifado=False,
        setores_em_escopo=(),
        setor_chefiado_ativo_id=None,
        pode_ser_beneficiario=True,
        ator_id=ATOR_ID,
    )
    defaults.update(kwargs)
    return PapelEfetivo(**defaults)


def _req(
    estado: str,
    criador_id: int = ATOR_ID,
    beneficiario_id: int = ATOR_ID,
    setor_beneficiario_id: int = SETOR_BENEFICIARIO_ID,
) -> SimpleNamespace:
    return SimpleNamespace(
        estado=estado,
        criador_id=criador_id,
        beneficiario_id=beneficiario_id,
        setor_beneficiario_id=setor_beneficiario_id,
    )


def test_acoes_disponiveis_inclui_editar_rascunho_para_criador_em_rascunho():
    papel = _papel(ator_id=ATOR_ID)
    req = _req(EstadoRequisicao.RASCUNHO, criador_id=ATOR_ID)

    acoes = acoes_disponiveis(papel, req)

    assert Operacao.EDITAR_RASCUNHO in acoes


def test_acoes_disponiveis_exclui_editar_rascunho_para_nao_criador():
    papel = _papel(ator_id=ATOR_ID)
    req = _req(EstadoRequisicao.RASCUNHO, criador_id=999)

    acoes = acoes_disponiveis(papel, req)

    assert Operacao.EDITAR_RASCUNHO not in acoes


def test_acoes_disponiveis_exclui_editar_rascunho_fora_do_estado_rascunho():
    papel = _papel(ator_id=ATOR_ID)
    req = _req(EstadoRequisicao.AGUARDANDO_AUTORIZACAO, criador_id=ATOR_ID)

    acoes = acoes_disponiveis(papel, req)

    assert Operacao.EDITAR_RASCUNHO not in acoes


def test_acoes_disponiveis_cancelar_disponivel_em_todos_os_estados_cancelaveis():
    papel = _papel(ator_id=ATOR_ID)

    for estado in (
        EstadoRequisicao.RASCUNHO,
        EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        EstadoRequisicao.AUTORIZADA,
        EstadoRequisicao.PRONTA_PARA_RETIRADA,
    ):
        req = _req(estado, criador_id=ATOR_ID)
        assert Operacao.CANCELAR in acoes_disponiveis(papel, req)


def test_acoes_disponiveis_cancelar_ausente_em_estados_finais():
    papel = _papel(ator_id=ATOR_ID)

    for estado in (
        EstadoRequisicao.RECUSADA,
        EstadoRequisicao.ATENDIDA,
        EstadoRequisicao.ESTORNADA,
    ):
        req = _req(estado, criador_id=ATOR_ID)
        assert Operacao.CANCELAR not in acoes_disponiveis(papel, req)


def test_acoes_disponiveis_papel_inativo_retorna_conjunto_vazio():
    papel = _papel(ator_id=ATOR_ID, ativo=False)
    req = _req(EstadoRequisicao.RASCUNHO, criador_id=ATOR_ID)

    acoes = acoes_disponiveis(papel, req)

    assert acoes == frozenset()


def test_acoes_disponiveis_retorna_frozenset():
    papel = _papel(ator_id=ATOR_ID)
    req = _req(EstadoRequisicao.RASCUNHO, criador_id=ATOR_ID)

    assert isinstance(acoes_disponiveis(papel, req), frozenset)


@pytest.mark.parametrize(
    'papel,req,esperado',
    [
        pytest.param(
            _papel(ator_id=ATOR_ID),
            _req(
                EstadoRequisicao.RASCUNHO, criador_id=ATOR_ID, beneficiario_id=ATOR_ID
            ),
            frozenset(
                {
                    Operacao.EDITAR_RASCUNHO,
                    Operacao.ENVIAR_PARA_AUTORIZACAO,
                    Operacao.CANCELAR,
                }
            ),
            id='criador_em_rascunho',
        ),
        pytest.param(
            _papel(ator_id=ATOR_ID, setor_chefiado_ativo_id=SETOR_BENEFICIARIO_ID),
            _req(
                EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
                criador_id=999,
                beneficiario_id=999,
            ),
            # RETORNAR_PARA_RASCUNHO entrou na Etapa 8: sem ela, um saldo
            # insuficiente descoberto na confirmação deixava o chefe só com
            # recusar — encerrar em definitivo o pedido de alguém porque a
            # quantidade não cabia. A condição é a mesma de recusar, então quem
            # já podia encerrar passa a poder devolver.
            frozenset(
                {
                    Operacao.RECUSAR,
                    Operacao.AUTORIZAR,
                    Operacao.RETORNAR_PARA_RASCUNHO,
                }
            ),
            id='chefe_setor_em_aguardando_autorizacao',
        ),
        pytest.param(
            _papel(ator_id=ATOR_ID, eh_almoxarifado=True),
            _req(EstadoRequisicao.AUTORIZADA, criador_id=999, beneficiario_id=999),
            frozenset({Operacao.SEPARAR_PARA_RETIRADA, Operacao.CANCELAR}),
            id='almoxarifado_em_autorizada',
        ),
        pytest.param(
            _papel(ator_id=ATOR_ID, eh_almoxarifado=True),
            _req(
                EstadoRequisicao.PRONTA_PARA_RETIRADA,
                criador_id=999,
                beneficiario_id=999,
            ),
            frozenset({Operacao.REGISTRAR_ATENDIMENTO, Operacao.CANCELAR}),
            id='almoxarifado_em_pronta_para_retirada',
        ),
        pytest.param(
            _papel(ator_id=ATOR_ID, eh_almoxarifado=True),
            _req(EstadoRequisicao.ATENDIDA, criador_id=999, beneficiario_id=999),
            frozenset({Operacao.REGISTRAR_DEVOLUCAO}),
            id='aux_almoxarifado_em_atendida_sem_estornar',
        ),
        pytest.param(
            _papel(
                ator_id=ATOR_ID, eh_almoxarifado=True, eh_chefe_de_almoxarifado=True
            ),
            _req(EstadoRequisicao.ATENDIDA, criador_id=999, beneficiario_id=999),
            frozenset({Operacao.REGISTRAR_DEVOLUCAO, Operacao.ESTORNAR}),
            id='chefe_almoxarifado_em_atendida',
        ),
        pytest.param(
            _papel(ator_id=ATOR_ID),
            _req(
                EstadoRequisicao.RECUSADA, criador_id=ATOR_ID, beneficiario_id=ATOR_ID
            ),
            frozenset(),
            id='estado_final_sem_acoes',
        ),
    ],
)
def test_acoes_disponiveis_conjunto_completo_por_papel_e_estado(papel, req, esperado):
    assert acoes_disponiveis(papel, req) == esperado


# ---------------------------------------------------------------------------
# historico_requisicoes_visiveis_para
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_historico_superuser_ve_tudo(superuser, req_historico_obras, req_historico_ti):
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)
    assert set(visiveis.values_list('pk', flat=True)) == {
        req_historico_obras.pk,
        req_historico_ti.pk,
    }


@pytest.mark.django_db
def test_historico_chefe_almox_ve_tudo(
    chefe_almoxarifado, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(chefe_almoxarifado.pk)
    assert set(visiveis.values_list('pk', flat=True)) == {
        req_historico_obras.pk,
        req_historico_ti.pk,
    }


@pytest.mark.django_db
def test_historico_aux_almox_ve_tudo(
    aux_almoxarifado, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(aux_almoxarifado.pk)
    assert set(visiveis.values_list('pk', flat=True)) == {
        req_historico_obras.pk,
        req_historico_ti.pk,
    }


@pytest.mark.django_db
def test_historico_chefe_setor_ve_so_proprio_setor(
    chefe_obras, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(chefe_obras.pk)
    pks = set(visiveis.values_list('pk', flat=True))
    assert req_historico_obras.pk in pks
    assert req_historico_ti.pk not in pks


@pytest.mark.django_db
def test_historico_chefe_setor_nao_ve_rascunho_de_terceiro(
    chefe_obras, req_solicitante_rascunho, req_historico_obras
):
    visiveis = historico_requisicoes_visiveis_para(chefe_obras.pk)
    pks = set(visiveis.values_list('pk', flat=True))
    assert req_solicitante_rascunho.pk not in pks
    assert req_historico_obras.pk in pks


@pytest.mark.django_db
def test_historico_almoxarifado_nao_ve_rascunho_de_terceiro(
    chefe_almoxarifado, req_solicitante_rascunho, req_historico_obras
):
    visiveis = historico_requisicoes_visiveis_para(chefe_almoxarifado.pk)
    pks = set(visiveis.values_list('pk', flat=True))
    assert req_solicitante_rascunho.pk not in pks
    assert req_historico_obras.pk in pks


@pytest.mark.django_db
def test_historico_chefe_setor_nao_ve_proprio_rascunho(chefe_obras, setor_obras):
    """Histórico não é 'minhas requisições': rascunho próprio também fica de fora."""
    proprio_rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=chefe_obras,
        beneficiario=chefe_obras,
        setor_beneficiario=setor_obras,
    )
    visiveis = historico_requisicoes_visiveis_para(chefe_obras.pk)
    assert proprio_rascunho.pk not in set(visiveis.values_list('pk', flat=True))


@pytest.mark.django_db
def test_historico_almoxarifado_nao_ve_proprio_rascunho(
    chefe_almoxarifado, setor_obras
):
    """Histórico não é 'minhas requisições': rascunho próprio do almoxarifado também fica de fora."""
    proprio_rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=chefe_almoxarifado,
        beneficiario=chefe_almoxarifado,
        setor_beneficiario=setor_obras,
    )
    visiveis = historico_requisicoes_visiveis_para(chefe_almoxarifado.pk)
    assert proprio_rascunho.pk not in set(visiveis.values_list('pk', flat=True))


@pytest.mark.django_db
def test_historico_aux_setor_nao_ve_requisicao_de_terceiro_do_setor(
    aux_obras, req_historico_obras
):
    """Aux de setor não supervisiona o setor (matriz §4, "Ver requisições do setor")."""
    visiveis = historico_requisicoes_visiveis_para(aux_obras.pk)
    assert req_historico_obras.pk not in set(visiveis.values_list('pk', flat=True))


@pytest.mark.django_db
def test_historico_aux_setor_ve_o_que_criou(aux_obras, setor_obras):
    """Como criador, o aux continua no histórico — e o detalhe abre (sem 404)."""
    propria = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0012',
        criador=aux_obras,
        beneficiario=aux_obras,
        setor_beneficiario=setor_obras,
    )
    visiveis = historico_requisicoes_visiveis_para(aux_obras.pk)
    assert propria.pk in set(visiveis.values_list('pk', flat=True))


@pytest.mark.django_db
def test_historico_aux_setor_nao_ve_proprio_rascunho(aux_obras, setor_obras):
    """Histórico não é 'minhas requisições' — vale para o aux como para os demais."""
    proprio_rascunho = Requisicao.objects.create(
        estado=EstadoRequisicao.RASCUNHO,
        criador=aux_obras,
        beneficiario=aux_obras,
        setor_beneficiario=setor_obras,
    )
    visiveis = historico_requisicoes_visiveis_para(aux_obras.pk)
    assert proprio_rascunho.pk not in set(visiveis.values_list('pk', flat=True))


@pytest.mark.django_db
def test_historico_aux_setor_e_subconjunto_do_detalhe(
    aux_obras, setor_obras, req_historico_obras, req_historico_ti
):
    """Nada listado no histórico pode devolver 404 no detalhe (#106)."""
    Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0013',
        criador=aux_obras,
        beneficiario=aux_obras,
        setor_beneficiario=setor_obras,
    )
    historico = set(
        historico_requisicoes_visiveis_para(aux_obras.pk).values_list('pk', flat=True)
    )
    detalhe = set(requisicoes_visiveis_para(aux_obras.pk).values_list('pk', flat=True))
    assert historico
    assert historico - detalhe == set()


@pytest.mark.django_db
def test_historico_chefe_setor_ve_o_que_criou_fora_do_setor_chefiado(
    chefe_obras, usuario_ti, setor_ti
):
    """Cláusula de criador também vale para o chefe — e o detalhe acompanha."""
    criada_fora = Requisicao.objects.create(
        estado=EstadoRequisicao.AGUARDANDO_AUTORIZACAO,
        numero_publico='REQ-2026-0014',
        criador=chefe_obras,
        beneficiario=usuario_ti,
        setor_beneficiario=setor_ti,
    )
    historico = set(
        historico_requisicoes_visiveis_para(chefe_obras.pk).values_list('pk', flat=True)
    )
    detalhe = set(
        requisicoes_visiveis_para(chefe_obras.pk).values_list('pk', flat=True)
    )
    assert criada_fora.pk in historico
    assert criada_fora.pk in detalhe


@pytest.mark.django_db
def test_historico_solicitante_puro_vazio(solicitante, req_historico_obras):
    visiveis = historico_requisicoes_visiveis_para(solicitante.pk)
    assert visiveis.count() == 0


@pytest.mark.django_db
def test_historico_inativo_vazio(usuario_inativo, req_historico_obras):
    visiveis = historico_requisicoes_visiveis_para(usuario_inativo.pk)
    assert visiveis.count() == 0


@pytest.mark.django_db
def test_historico_ator_inexistente_vazio(req_historico_obras):
    visiveis = historico_requisicoes_visiveis_para(999999)
    assert visiveis.count() == 0


# ---------------------------------------------------------------------------
# filtrar_historico_requisicoes / pode_filtrar_historico_por_setor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_filtrar_historico_por_texto_no_criador(
    superuser, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)
    filtrado = filtrar_historico_requisicoes(
        visiveis,
        texto='solicitante',
        estados=[],
        data_ini=None,
        data_fim=None,
        setor=None,
    )
    assert set(filtrado.values_list('pk', flat=True)) == {req_historico_obras.pk}


@pytest.mark.django_db
def test_filtrar_historico_por_texto_no_beneficiario(
    superuser, req_historico_obras, req_historico_ti
):
    # req_historico_ti tem criador (usuario_ti) e beneficiário (outro_usuario_obras)
    # distintos — o texto só bate no beneficiário, não no criador.
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)
    filtrado = filtrar_historico_requisicoes(
        visiveis,
        texto='Maria Obras',
        estados=[],
        data_ini=None,
        data_fim=None,
        setor=None,
    )
    assert set(filtrado.values_list('pk', flat=True)) == {req_historico_ti.pk}


@pytest.mark.django_db
def test_filtrar_historico_por_estado(superuser, req_historico_obras, req_historico_ti):
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)
    filtrado = filtrar_historico_requisicoes(
        visiveis,
        texto='',
        estados=[EstadoRequisicao.AUTORIZADA],
        data_ini=None,
        data_fim=None,
        setor=None,
    )
    assert set(filtrado.values_list('pk', flat=True)) == {req_historico_ti.pk}


@pytest.mark.django_db
def test_filtrar_historico_estado_invalido_e_no_op(
    superuser, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)
    filtrado = filtrar_historico_requisicoes(
        visiveis,
        texto='',
        estados=['nao_existe'],
        data_ini=None,
        data_fim=None,
        setor=None,
    )
    assert filtrado.count() == 2


@pytest.mark.django_db
def test_filtrar_historico_por_periodo(superuser, req_historico_obras):
    hoje = timezone.localtime(req_historico_obras.criado_em).date()
    visiveis = historico_requisicoes_visiveis_para(superuser.pk)

    dentro = filtrar_historico_requisicoes(
        visiveis, texto='', estados=[], data_ini=hoje, data_fim=hoje, setor=None
    )
    assert req_historico_obras.pk in dentro.values_list('pk', flat=True)

    fora = filtrar_historico_requisicoes(
        visiveis,
        texto='',
        estados=[],
        data_ini=date(1999, 1, 1),
        data_fim=date(1999, 1, 2),
        setor=None,
    )
    assert fora.count() == 0


@pytest.mark.django_db
def test_filtrar_historico_por_setor_nao_vaza_outro_setor(
    chefe_almoxarifado, req_historico_obras, req_historico_ti, setor_ti
):
    visiveis = historico_requisicoes_visiveis_para(chefe_almoxarifado.pk)
    filtrado = filtrar_historico_requisicoes(
        visiveis,
        texto='',
        estados=[],
        data_ini=None,
        data_fim=None,
        setor=setor_ti.pk,
    )
    assert set(filtrado.values_list('pk', flat=True)) == {req_historico_ti.pk}


@pytest.mark.django_db
def test_pode_filtrar_historico_por_setor_almox_sim_chefe_setor_nao(
    chefe_almoxarifado, chefe_obras
):
    assert pode_filtrar_historico_por_setor(chefe_almoxarifado.pk) is True
    assert pode_filtrar_historico_por_setor(chefe_obras.pk) is False


@pytest.mark.django_db
def test_pode_filtrar_historico_por_setor_solicitante_nao(solicitante):
    assert pode_filtrar_historico_por_setor(solicitante.pk) is False


@pytest.mark.django_db
def test_setores_do_historico_distintos_e_ordenados_por_nome(
    chefe_almoxarifado, req_historico_obras, req_historico_ti
):
    visiveis = historico_requisicoes_visiveis_para(chefe_almoxarifado.pk)
    nomes = list(setores_do_historico(visiveis).values_list('nome', flat=True))
    assert nomes == ['Obras', 'TI']


# ---------------------------------------------------------------------------
# chefe_autorizador_do_setor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_chefe_autorizador_setor_ativo_chefe_ativo(setor_obras, chefe_obras):
    assert chefe_autorizador_do_setor(setor_obras.pk) == chefe_obras.pk


@pytest.mark.django_db
def test_chefe_autorizador_chefe_inativo(setor_obras, chefe_obras):
    chefe_obras.is_active = False
    chefe_obras.save(update_fields=['is_active'])
    assert chefe_autorizador_do_setor(setor_obras.pk) is None


@pytest.mark.django_db
def test_chefe_autorizador_setor_inativo(setor_obras, chefe_obras):
    setor_obras.ativo = False
    setor_obras.save(update_fields=['ativo'])
    assert chefe_autorizador_do_setor(setor_obras.pk) is None


@pytest.mark.django_db
def test_chefe_autorizador_sem_chefe_e_setor_inexistente(setor_ti):
    assert setor_ti.chefe_id is None
    assert chefe_autorizador_do_setor(setor_ti.pk) is None
    assert chefe_autorizador_do_setor(999999) is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('setor_ativo', 'chefe_ativo'),
    [(True, True), (True, False), (False, True)],
)
def test_chefe_autorizador_equivale_a_fila_autorizacao(
    setor_obras, chefe_obras, req_solicitante_enviada, setor_ativo, chefe_ativo
):
    """NOT-01: quem o selector resolve é exatamente quem vê a fila.

    As duas funções espelham a mesma condição escrita de lados opostos
    (setor→ator e ator→requisições) sem compartilhar código. Este teste é o que
    impede os dois filtros de divergirem numa fatia futura; os casos acima
    olham só um lado do espelho.
    """
    setor_obras.ativo = setor_ativo
    setor_obras.save(update_fields=['ativo'])
    chefe_obras.is_active = chefe_ativo
    chefe_obras.save(update_fields=['is_active'])

    resolve_chefe = chefe_autorizador_do_setor(setor_obras.pk) == chefe_obras.pk
    ve_na_fila = req_solicitante_enviada in list(fila_autorizacao(chefe_obras.pk))

    esperado = setor_ativo and chefe_ativo
    assert resolve_chefe is ve_na_fila
    assert resolve_chefe is esperado


class TestSaldosPorMateriais:
    """`saldos_por_materiais` alimenta o aviso de saldo da linha de item."""

    def test_inclui_a_unidade_do_material(self, material_disponivel):
        """Sem a unidade, a tela escrevia "Saldo disponível: 90" e pronto.

        O número sozinho não diz se sobram 90 unidades ou 90 quilos, e a decisão
        que a pessoa toma logo abaixo é quanto pedir. A unidade também define com
        quantas casas o número é escrito.
        """
        resultado = saldos_por_materiais([material_disponivel.pk])
        assert (
            resultado[material_disponivel.pk]['unidade'] == material_disponivel.unidade
        )

    def test_material_inelegivel_tambem_carrega_a_unidade(self, material_sem_saldo):
        resultado = saldos_por_materiais([material_sem_saldo.pk])
        assert resultado[material_sem_saldo.pk]['elegivel'] is False
        assert resultado[material_sem_saldo.pk]['unidade'] == material_sem_saldo.unidade
