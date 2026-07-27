"""Testes de services de accounts — gestão de cadastro (USR-04/05/07, VinculoAuxiliar)."""

import pytest

from apps.accounts.models import Setor, SetorClassificacao, User, VinculoAuxiliar


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def setor_a(db):
    return Setor.objects.create(
        codigo='SA', nome='Setor A', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def setor_b(db):
    return Setor.objects.create(
        codigo='SB', nome='Setor B', classificacao=SetorClassificacao.COMUM
    )


@pytest.fixture
def usuario_ativo_a(db, setor_a):
    return User.objects.create_user(
        matricula='U01', nome='Ativo A', password='senha', setor=setor_a
    )


@pytest.fixture
def usuario_ativo_b(db, setor_a):
    """Segundo usuário ativo no setor_a (para candidato a chefe)."""
    return User.objects.create_user(
        matricula='U02', nome='Ativo B', password='senha', setor=setor_a
    )


@pytest.fixture
def usuario_outro_setor(db, setor_b):
    return User.objects.create_user(
        matricula='U03', nome='Outro Setor', password='senha', setor=setor_b
    )


@pytest.fixture
def usuario_inativo(db, setor_a):
    return User.objects.create_user(
        matricula='U04',
        nome='Inativo',
        password='senha',
        setor=setor_a,
        is_active=False,
    )


@pytest.fixture
def superusuario(db, setor_a):
    return User.objects.create_superuser(
        matricula='S01', nome='Super', password='senha', setor=setor_a
    )


# ---------------------------------------------------------------------------
# TestTrocarChefSetor — USR-04 / USR-05
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTrocarChefeSetor:
    def test_chefe_ativo_do_setor_e_designado(
        self, superusuario, setor_a, usuario_ativo_a
    ):
        from apps.accounts.services import trocar_chefe_setor

        trocar_chefe_setor(
            ator_id=superusuario.pk,
            setor_id=setor_a.pk,
            novo_chefe_id=usuario_ativo_a.pk,
        )
        setor_a.refresh_from_db()
        assert setor_a.chefe_id == usuario_ativo_a.pk

    def test_chefe_inativo_lanca_dados_invalidos(
        self, superusuario, setor_a, usuario_inativo
    ):
        from apps.core.exceptions import DadosInvalidos
        from apps.accounts.services import trocar_chefe_setor

        with pytest.raises(DadosInvalidos) as exc_info:
            trocar_chefe_setor(
                ator_id=superusuario.pk,
                setor_id=setor_a.pk,
                novo_chefe_id=usuario_inativo.pk,
            )
        assert exc_info.value.code == 'chefe_inativo'

    def test_chefe_de_outro_setor_lanca_dados_invalidos(
        self, superusuario, setor_a, usuario_outro_setor
    ):
        from apps.core.exceptions import DadosInvalidos
        from apps.accounts.services import trocar_chefe_setor

        with pytest.raises(DadosInvalidos) as exc_info:
            trocar_chefe_setor(
                ator_id=superusuario.pk,
                setor_id=setor_a.pk,
                novo_chefe_id=usuario_outro_setor.pk,
            )
        assert exc_info.value.code == 'chefe_setor_errado'

    def test_chefe_duplicado_lanca_conflito(
        self, superusuario, setor_a, setor_b, usuario_ativo_a
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.accounts.services import trocar_chefe_setor

        setor_b.chefe = usuario_ativo_a
        setor_b.save(update_fields=['chefe'])
        with pytest.raises(ConflitoDominio) as exc_info:
            trocar_chefe_setor(
                ator_id=superusuario.pk,
                setor_id=setor_a.pk,
                novo_chefe_id=usuario_ativo_a.pk,
            )
        assert exc_info.value.code == 'chefe_duplicado'

    def test_ator_nao_superusuario_lanca_permissao_negada(
        self, setor_a, usuario_ativo_a, usuario_ativo_b
    ):
        from apps.core.exceptions import PermissaoNegada
        from apps.accounts.services import trocar_chefe_setor

        with pytest.raises(PermissaoNegada):
            trocar_chefe_setor(
                ator_id=usuario_ativo_a.pk,
                setor_id=setor_a.pk,
                novo_chefe_id=usuario_ativo_b.pk,
            )


# ---------------------------------------------------------------------------
# TestDesativarUsuario — USR-07
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDesativarUsuario:
    def test_chefe_sem_substituto_lanca_conflito(
        self, superusuario, setor_a, usuario_ativo_a
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.accounts.services import desativar_usuario

        setor_a.chefe = usuario_ativo_a
        setor_a.save(update_fields=['chefe'])
        with pytest.raises(ConflitoDominio) as exc_info:
            desativar_usuario(ator_id=superusuario.pk, usuario_id=usuario_ativo_a.pk)
        assert exc_info.value.code == 'usuario_chefe_sem_substituto'

    def test_chefe_com_substituto_valido_desativa(
        self, superusuario, setor_a, usuario_ativo_a, usuario_ativo_b
    ):
        from apps.accounts.services import desativar_usuario

        setor_a.chefe = usuario_ativo_a
        setor_a.save(update_fields=['chefe'])
        desativar_usuario(
            ator_id=superusuario.pk,
            usuario_id=usuario_ativo_a.pk,
            novo_chefe_id=usuario_ativo_b.pk,
        )
        usuario_ativo_a.refresh_from_db()
        setor_a.refresh_from_db()
        assert usuario_ativo_a.is_active is False
        assert setor_a.chefe_id == usuario_ativo_b.pk

    def test_usuario_nao_chefe_desativa_normalmente(
        self, superusuario, usuario_ativo_a
    ):
        from apps.accounts.services import desativar_usuario

        desativar_usuario(ator_id=superusuario.pk, usuario_id=usuario_ativo_a.pk)
        usuario_ativo_a.refresh_from_db()
        assert usuario_ativo_a.is_active is False

    def test_ja_inativo_e_idempotente(self, superusuario, usuario_inativo):
        from apps.accounts.services import desativar_usuario

        desativar_usuario(ator_id=superusuario.pk, usuario_id=usuario_inativo.pk)
        usuario_inativo.refresh_from_db()
        assert usuario_inativo.is_active is False

    def test_ator_nao_superusuario_lanca_permissao_negada(
        self, setor_a, usuario_ativo_a, usuario_ativo_b
    ):
        from apps.core.exceptions import PermissaoNegada
        from apps.accounts.services import desativar_usuario

        with pytest.raises(PermissaoNegada):
            desativar_usuario(ator_id=usuario_ativo_a.pk, usuario_id=usuario_ativo_b.pk)


# ---------------------------------------------------------------------------
# TestVinculoAuxiliar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVinculoAuxiliar:
    def test_ativar_vinculo_cria_vinculo_ativo(
        self, superusuario, setor_a, usuario_ativo_a
    ):
        from apps.accounts.services import ativar_vinculo_auxiliar

        ativar_vinculo_auxiliar(
            ator_id=superusuario.pk, usuario_id=usuario_ativo_a.pk, setor_id=setor_a.pk
        )
        assert VinculoAuxiliar.objects.filter(
            usuario=usuario_ativo_a, setor=setor_a, ativo=True
        ).exists()

    def test_ativar_vinculo_ja_ativo_lanca_conflito(
        self, superusuario, setor_a, usuario_ativo_a
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.accounts.services import ativar_vinculo_auxiliar

        VinculoAuxiliar.objects.create(
            usuario=usuario_ativo_a, setor=setor_a, ativo=True
        )
        with pytest.raises(ConflitoDominio) as exc_info:
            ativar_vinculo_auxiliar(
                ator_id=superusuario.pk,
                usuario_id=usuario_ativo_a.pk,
                setor_id=setor_a.pk,
            )
        assert exc_info.value.code == 'vinculo_ja_ativo'

    def test_desativar_vinculo_ativo(self, superusuario, setor_a, usuario_ativo_a):
        from apps.accounts.services import desativar_vinculo_auxiliar

        vinculo = VinculoAuxiliar.objects.create(
            usuario=usuario_ativo_a, setor=setor_a, ativo=True
        )
        desativar_vinculo_auxiliar(ator_id=superusuario.pk, vinculo_id=vinculo.pk)
        vinculo.refresh_from_db()
        assert vinculo.ativo is False
        assert vinculo.desativado_em is not None

    def test_desativar_vinculo_ja_inativo_lanca_conflito(
        self, superusuario, setor_a, usuario_ativo_a
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.accounts.services import desativar_vinculo_auxiliar

        vinculo = VinculoAuxiliar.objects.create(
            usuario=usuario_ativo_a, setor=setor_a, ativo=False
        )
        with pytest.raises(ConflitoDominio) as exc_info:
            desativar_vinculo_auxiliar(ator_id=superusuario.pk, vinculo_id=vinculo.pk)
        assert exc_info.value.code == 'vinculo_ja_inativo'

    def test_ator_nao_superusuario_lanca_permissao_negada(
        self, setor_a, usuario_ativo_a, usuario_ativo_b
    ):
        from apps.core.exceptions import PermissaoNegada
        from apps.accounts.services import ativar_vinculo_auxiliar

        with pytest.raises(PermissaoNegada):
            ativar_vinculo_auxiliar(
                ator_id=usuario_ativo_a.pk,
                usuario_id=usuario_ativo_b.pk,
                setor_id=setor_a.pk,
            )


# ---------------------------------------------------------------------------
# TestDesativarSetor — USR-06 (issue #107)
# ---------------------------------------------------------------------------


@pytest.fixture
def requisicao_em(db, usuario_ativo_a):
    """Cria uma requisição num setor e estado dados, sem passar por service.

    A montagem é direta porque o objeto sob teste é `desativar_setor`; o ciclo
    de vida da requisição tem cobertura própria em `apps/requisicoes`.
    """

    def _criar(setor, estado):
        from apps.requisicoes.models import Requisicao

        return Requisicao.objects.create(
            estado=estado,
            criador=usuario_ativo_a,
            beneficiario=usuario_ativo_a,
            setor_beneficiario=setor,
        )

    return _criar


@pytest.mark.django_db
class TestDesativarSetor:
    def test_requisicao_aguardando_autorizacao_bloqueia_desativacao(
        self, superusuario, setor_a, requisicao_em
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.accounts.services import desativar_setor
        from apps.requisicoes.models import EstadoRequisicao

        requisicao_em(setor_a, EstadoRequisicao.AGUARDANDO_AUTORIZACAO)

        with pytest.raises(ConflitoDominio) as exc_info:
            desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        assert exc_info.value.code == 'setor_com_requisicoes_em_voo'
        setor_a.refresh_from_db()
        assert setor_a.ativo is True

    def test_setor_sem_requisicoes_desativa(self, superusuario, setor_a):
        from apps.accounts.services import desativar_setor

        desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is False

    def test_rascunho_nao_bloqueia_desativacao(
        self, superusuario, setor_a, requisicao_em
    ):
        """Rascunho não está na fila de ninguém — não depende de autorizador."""
        from apps.accounts.services import desativar_setor
        from apps.requisicoes.models import EstadoRequisicao

        requisicao_em(setor_a, EstadoRequisicao.RASCUNHO)

        desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is False

    def test_requisicao_autorizada_nao_bloqueia_desativacao(
        self, superusuario, setor_a, requisicao_em
    ):
        """Requisição autorizada segue pelo almoxarifado, não pelo chefe do setor."""
        from apps.accounts.services import desativar_setor
        from apps.requisicoes.models import EstadoRequisicao

        requisicao_em(setor_a, EstadoRequisicao.AUTORIZADA)

        desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is False

    def test_requisicao_em_voo_de_outro_setor_nao_bloqueia(
        self, superusuario, setor_a, setor_b, requisicao_em
    ):
        from apps.accounts.services import desativar_setor
        from apps.requisicoes.models import EstadoRequisicao

        requisicao_em(setor_b, EstadoRequisicao.AGUARDANDO_AUTORIZACAO)

        desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is False

    def test_setor_ja_inativo_e_idempotente(self, superusuario, setor_a):
        from apps.accounts.services import desativar_setor

        setor_a.ativo = False
        setor_a.save(update_fields=['ativo'])

        desativar_setor(ator_id=superusuario.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is False

    def test_ator_nao_superusuario_lanca_permissao_negada(
        self, setor_a, usuario_ativo_a
    ):
        from apps.core.exceptions import PermissaoNegada
        from apps.accounts.services import desativar_setor

        with pytest.raises(PermissaoNegada):
            desativar_setor(ator_id=usuario_ativo_a.pk, setor_id=setor_a.pk)

        setor_a.refresh_from_db()
        assert setor_a.ativo is True
