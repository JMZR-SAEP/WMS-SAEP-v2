"""Testes de serviço para estoque.registrar_saida_excepcional."""

import pytest

from apps.estoque.models import EstadoSaidaExcepcional, SaidaExcepcional, SaldoEstoque


class TestRegistrarSaidaExcepcional:
    def test_happy_path_cria_saida_e_baixa_saldo(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.estoque.services import registrar_saida_excepcional

        saida = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='Descarte por avaria',
            observacao='Caixas molhadas',
            itens=[{'material_id': material_disponivel.pk, 'quantidade': '5'}],
        )

        assert saida.pk is not None
        assert saida.numero_publico is not None
        assert saida.numero_publico.startswith('SXP-')
        assert saida.estado == EstadoSaidaExcepcional.REGISTRADA
        assert saida.registrado_por_id == chefe_almoxarifado.pk
        assert saida.estoque_id == estoque_principal.pk
        assert saida.itens.count() == 1

        saldo = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        assert saldo.saldo_fisico == 95  # 100 - 5

    def test_numero_publico_formato_sxp(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.estoque.services import registrar_saida_excepcional
        from django.utils import timezone

        saida = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='Teste formato',
            observacao='obs',
            itens=[{'material_id': material_disponivel.pk, 'quantidade': '1'}],
        )

        ano = timezone.localdate().year
        assert saida.numero_publico == f'SXP-{ano}-000001'

    def test_sequencia_incrementa(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida
        from apps.estoque.services import registrar_saida_excepcional
        from django.utils import timezone

        m2 = Material.objects.create(
            codigo='MAT002',
            nome='Parafuso M8',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal, material=m2, saldo_fisico=50, saldo_reservado=0
        )

        saida1 = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='A',
            observacao='',
            itens=[{'material_id': material_disponivel.pk, 'quantidade': '1'}],
        )
        saida2 = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='B',
            observacao='',
            itens=[{'material_id': m2.pk, 'quantidade': '1'}],
        )

        ano = timezone.localdate().year
        assert saida1.numero_publico == f'SXP-{ano}-000001'
        assert saida2.numero_publico == f'SXP-{ano}-000002'

    def test_sem_itens_lanca_dados_invalidos(
        self, chefe_almoxarifado, estoque_principal
    ):
        from apps.core.exceptions import DadosInvalidos
        from apps.estoque.services import registrar_saida_excepcional

        with pytest.raises(DadosInvalidos, match='ao menos um item'):
            registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Teste',
                observacao='Teste válido',
                itens=[],
            )

    def test_material_duplicado_lanca_dados_invalidos(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.core.exceptions import DadosInvalidos
        from apps.estoque.services import registrar_saida_excepcional

        with pytest.raises(DadosInvalidos, match='duplicado'):
            registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Duplicado',
                observacao='Teste válido',
                itens=[
                    {'material_id': material_disponivel.pk, 'quantidade': '5'},
                    {'material_id': material_disponivel.pk, 'quantidade': '3'},
                ],
            )

    def test_saldo_inexistente_lanca_conflito(
        self, chefe_almoxarifado, estoque_principal
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.models import Material, UnidadeMedida
        from apps.estoque.services import registrar_saida_excepcional

        m = Material.objects.create(
            codigo='MAT999', nome='Sem Saldo', unidade=UnidadeMedida.UNIDADE, ativo=True
        )

        with pytest.raises(ConflitoDominio, match='Saldo não encontrado'):
            registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Sem saldo',
                observacao='Teste válido',
                itens=[{'material_id': m.pk, 'quantidade': '1'}],
            )

    def test_quantidade_invalida_lanca_dados_invalidos(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.core.exceptions import DadosInvalidos
        from apps.estoque.services import registrar_saida_excepcional

        with pytest.raises(DadosInvalidos, match='maior que zero'):
            registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Qtd zero',
                observacao='Teste válido',
                itens=[{'material_id': material_disponivel.pk, 'quantidade': '0'}],
            )

    def test_nao_persiste_se_saldo_insuficiente(
        self, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        """Transação atomic: nenhum objeto persistido se saldo_fisico insuficiente."""
        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import registrar_saida_excepcional

        with pytest.raises(ConflitoDominio):
            registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Muito',
                observacao='Teste válido',
                itens=[{'material_id': material_disponivel.pk, 'quantidade': '9999'}],
            )

        assert not SaidaExcepcional.objects.exists()


class TestRegistrarSaidaExcepcionalAuth:
    def test_ator_nao_autorizado_lanca_permissao_negada(
        self, aux_almoxarifado, estoque_principal, material_disponivel
    ):
        import pytest

        from apps.core.exceptions import PermissaoNegada
        from apps.estoque.services import registrar_saida_excepcional

        with pytest.raises(PermissaoNegada):
            registrar_saida_excepcional(
                ator_id=aux_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Avaria',
                observacao='Teste válido',
                itens=[{'material_id': material_disponivel.pk, 'quantidade': '1'}],
            )


class TestEstornarSaidaExcepcional:
    def test_happy_path_estorna_e_restaura_saldo(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from apps.estoque.services import estornar_saida_excepcional

        saldo_obj_antes = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        saldo_fisico_antes = saldo_obj_antes.saldo_fisico
        saldo_reservado_antes = saldo_obj_antes.saldo_reservado

        quantidade_estornada = saida_registrada.itens.first().quantidade

        saida = estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Registro equivocado.',
        )

        assert saida.estado == EstadoSaidaExcepcional.ESTORNADA
        assert saida.estornado_por_id == chefe_almoxarifado.pk
        assert saida.estornado_em is not None
        assert saida.justificativa_estorno == 'Registro equivocado.'

        saldo_obj_depois = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        assert (
            saldo_obj_depois.saldo_fisico == saldo_fisico_antes + quantidade_estornada
        )
        assert saldo_obj_depois.saldo_reservado == saldo_reservado_antes
        assert (
            saldo_obj_depois.saldo_fisico - saldo_obj_depois.saldo_reservado
            == saldo_obj_depois.saldo_disponivel
        )

    def test_estorno_duplo_lanca_conflito(self, chefe_almoxarifado, saida_registrada):
        import pytest

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import estornar_saida_excepcional

        estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Primeiro estorno.',
        )

        with pytest.raises(ConflitoDominio, match='já estornada'):
            estornar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                saida_id=saida_registrada.pk,
                justificativa='Segundo estorno.',
            )

    def test_ator_sem_permissao_lanca_permissao_negada(
        self, aux_almoxarifado, saida_registrada
    ):
        import pytest

        from apps.core.exceptions import PermissaoNegada
        from apps.estoque.services import estornar_saida_excepcional

        with pytest.raises(PermissaoNegada):
            estornar_saida_excepcional(
                ator_id=aux_almoxarifado.pk,
                saida_id=saida_registrada.pk,
                justificativa='Tentativa indevida.',
            )

    def test_justificativa_vazia_lanca_dados_invalidos(
        self, chefe_almoxarifado, saida_registrada
    ):
        import pytest

        from apps.core.exceptions import DadosInvalidos
        from apps.estoque.services import estornar_saida_excepcional

        with pytest.raises(DadosInvalidos, match='justificativa'):
            estornar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                saida_id=saida_registrada.pk,
                justificativa='',
            )

    def test_saida_inexistente_lanca_dados_invalidos(self, chefe_almoxarifado):
        import pytest

        from apps.core.exceptions import DadosInvalidos
        from apps.estoque.services import estornar_saida_excepcional

        with pytest.raises(DadosInvalidos):
            estornar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                saida_id=999999,
                justificativa='Inexistente.',
            )


class TestConfirmarImportacaoScpi:
    """Contrato de confirmar_importacao_scpi."""

    def _csv(self, cadpro: str, denominacao: str, quantidade: str) -> bytes:
        return (
            f'CADPRO;DENOMINACAO;QUAN3\n{cadpro};{denominacao};{quantidade}\n'.encode(
                'utf-8'
            )
        )

    def test_cria_importacao_scpi_com_metadados(self, db, superuser, estoque_principal):
        from apps.estoque.models import ImportacaoSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv('000.999.100', 'Material Qualquer', '10.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='teste.csv',
            estoque_id=estoque_principal.pk,
        )
        assert importacao.pk is not None
        assert importacao.arquivo_nome == 'teste.csv'
        assert importacao.importado_por_id == superuser.pk
        assert importacao.total_linhas == 1
        assert ImportacaoSCPI.objects.filter(pk=importacao.pk).exists()

    def test_persiste_arquivo_csv_confirmado(
        self, db, settings, tmp_path, superuser, estoque_principal
    ):
        """O CSV confirmado é arquivado, não descartado (base da reconciliação LED-02)."""
        from apps.estoque.models import ImportacaoSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        settings.MEDIA_ROOT = str(tmp_path)
        csv_bytes = self._csv('000.999.600', 'Arruela M8', '7.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='saldo_scpi.csv',
            estoque_id=estoque_principal.pk,
        )
        # Relê do banco e abre pelo storage: ler o handle ainda em memória
        # passaria mesmo que nada tivesse sido gravado.
        do_banco = ImportacaoSCPI.objects.get(pk=importacao.pk)
        with do_banco.arquivo.open('rb') as arquivo:
            assert arquivo.read() == csv_bytes
        assert do_banco.arquivo.name.endswith('.csv')

    def test_hash_confere_com_sha256_do_arquivo_persistido(
        self, db, settings, tmp_path, superuser, estoque_principal
    ):
        """O hash gravado descreve o arquivo que ficou no storage, não outro."""
        import hashlib

        from apps.estoque.models import ImportacaoSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        settings.MEDIA_ROOT = str(tmp_path)
        csv_bytes = self._csv('000.999.610', 'Bucha S8', '3.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='conferencia.csv',
            estoque_id=estoque_principal.pk,
        )
        do_banco = ImportacaoSCPI.objects.get(pk=importacao.pk)
        with do_banco.arquivo.open('rb') as arquivo:
            hash_do_arquivo = hashlib.sha256(arquivo.read()).hexdigest()
        assert hash_do_arquivo == do_banco.arquivo_hash

    def test_falha_ao_persistir_arquivo_desfaz_importacao(
        self, db, settings, tmp_path, monkeypatch, superuser, estoque_principal
    ):
        """Erro de storage desfaz a confirmação inteira — as três tabelas do mesmo atomic."""
        import pytest
        from django.core.files.storage import FileSystemStorage

        from apps.estoque.models import ImportacaoSCPI, Material, SaldoEstoque
        from apps.estoque.services import confirmar_importacao_scpi

        settings.MEDIA_ROOT = str(tmp_path)

        def _disco_cheio(self, name, content, max_length=None):
            raise OSError('sem espaço em disco')

        monkeypatch.setattr(FileSystemStorage, '_save', _disco_cheio)

        csv_bytes = self._csv('000.999.700', 'Cantoneira 40mm', '9.000')
        with pytest.raises(OSError):
            confirmar_importacao_scpi(
                ator_id=superuser.pk,
                conteudo_bytes=csv_bytes,
                arquivo_nome='rollback.csv',
                estoque_id=estoque_principal.pk,
            )

        assert not ImportacaoSCPI.objects.filter(arquivo_nome='rollback.csv').exists()
        assert not Material.objects.filter(codigo='000.999.700').exists()
        assert not SaldoEstoque.objects.filter(material__codigo='000.999.700').exists()

    def test_falha_no_hook_desfaz_importacao_mesmo_com_arquivo_gravado(
        self, db, settings, tmp_path, superuser, estoque_principal
    ):
        """O arquivo já foi para o storage, mas o banco volta ao estado anterior.

        Storage não participa da transação: o CSV gravado permanece em disco como
        órfão. É inerte — o download só serve arquivo a partir de uma linha
        existente — e apagá-lo aqui seria perigoso, porque o nome vem do hash do
        conteúdo e poderia colidir com o arquivo de uma importação legítima.
        """
        import pytest
        from django.core.files.storage import default_storage

        from apps.estoque.models import ImportacaoSCPI, Material, SaldoEstoque
        from apps.estoque.services import confirmar_importacao_scpi

        settings.MEDIA_ROOT = str(tmp_path)

        gravado = {}

        def _hook_quebrado(**kwargs):
            gravado['nome'] = kwargs['importacao'].arquivo.name
            raise RuntimeError('hook falhou depois da criação')

        csv_bytes = self._csv('000.999.800', 'Abraçadeira 20mm', '4.000')
        with pytest.raises(RuntimeError):
            confirmar_importacao_scpi(
                ator_id=superuser.pk,
                conteudo_bytes=csv_bytes,
                arquivo_nome='hook.csv',
                estoque_id=estoque_principal.pk,
                _pos_importacao_hook=_hook_quebrado,
            )

        assert not ImportacaoSCPI.objects.filter(arquivo_nome='hook.csv').exists()
        assert not Material.objects.filter(codigo='000.999.800').exists()
        assert not SaldoEstoque.objects.filter(material__codigo='000.999.800').exists()

        # O órfão descrito na docstring precisa ser verificável: sem isto, adiar
        # ou omitir a gravação no storage manteria o teste verde.
        assert default_storage.exists(gravado['nome'])

    def test_cria_material_novo_com_saldo_inicial(
        self, db, superuser, estoque_principal
    ):
        from decimal import Decimal

        from apps.estoque.models import Material, SaldoEstoque
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv('000.999.200', 'Rebite 3mm', '42.000')
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='novo.csv',
            estoque_id=estoque_principal.pk,
        )
        material = Material.objects.get(codigo='000.999.200')
        assert material.nome == 'Rebite 3mm'
        saldo = SaldoEstoque.objects.get(material=material, estoque=estoque_principal)
        assert saldo.saldo_fisico == Decimal('42')
        assert saldo.saldo_reservado == Decimal('0')

    def test_preview_anuncia_a_unidade_que_a_confirmacao_vai_gravar(
        self, db, superuser, estoque_principal
    ):
        """O preview decide a precisão de exibição pela unidade da linha.

        Se ela divergisse da que o service grava, o número mostrado antes de
        confirmar teria precisão diferente do número mostrado depois — a
        divergência apareceria só com o material já criado. Hoje as duas pontas
        leem `UNIDADE_PADRAO_MATERIAL_SCPI`; este teste é o que falha se alguém
        reintroduzir um literal em qualquer uma delas.
        """
        from apps.estoque.models import Material
        from apps.estoque.selectors import gerar_preview_importacao_scpi
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv('000.999.201', 'Bucha de nylon S8', '30.000')
        linha_preview = next(
            linha
            for linha in gerar_preview_importacao_scpi(
                conteudo_bytes=csv_bytes, estoque_id=estoque_principal.pk
            )
            if linha.status == 'novo'
        )
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='unidade.csv',
            estoque_id=estoque_principal.pk,
        )
        material = Material.objects.get(codigo='000.999.201')
        assert linha_preview.unidade == material.unidade

    def test_preview_de_material_existente_usa_a_unidade_dele(
        self, db, superuser, estoque_principal, material_scpi
    ):
        """Material já no WMS exibe com a precisão da própria unidade.

        Sem isso, um material em litro cairia na precisão de `un` no preview e
        `12,5 l` viraria `12` — no lugar onde a conferência com o SCPI acontece.
        """
        from apps.estoque.models import UnidadeMedida
        from apps.estoque.selectors import gerar_preview_importacao_scpi

        material_scpi.unidade = UnidadeMedida.LITRO
        material_scpi.save(update_fields=['unidade'])

        csv_bytes = self._csv(material_scpi.codigo, material_scpi.nome, '9.500')
        linha = gerar_preview_importacao_scpi(
            conteudo_bytes=csv_bytes, estoque_id=estoque_principal.pk
        )[0]
        assert linha.unidade == UnidadeMedida.LITRO

    def test_material_existente_nao_tem_saldo_alterado(
        self, db, superuser, estoque_principal, material_scpi
    ):

        from apps.estoque.models import SaldoEstoque
        from apps.estoque.services import confirmar_importacao_scpi

        saldo_antes = SaldoEstoque.objects.get(
            material=material_scpi, estoque=estoque_principal
        ).saldo_fisico

        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '999.000')
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='existente.csv',
            estoque_id=estoque_principal.pk,
        )
        saldo_depois = SaldoEstoque.objects.get(
            material=material_scpi, estoque=estoque_principal
        ).saldo_fisico
        assert saldo_depois == saldo_antes

    def test_hash_duplicado_lanca_conflito_dominio(
        self, db, superuser, estoque_principal
    ):
        import pytest

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv('000.999.300', 'Porca M4', '5.000')
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='dup.csv',
            estoque_id=estoque_principal.pk,
        )
        with pytest.raises(ConflitoDominio):
            confirmar_importacao_scpi(
                ator_id=superuser.pk,
                conteudo_bytes=csv_bytes,
                arquivo_nome='dup.csv',
                estoque_id=estoque_principal.pk,
            )

    def test_sem_permissao_lanca_permissao_negada(
        self, db, chefe_almoxarifado, estoque_principal
    ):
        import pytest

        from apps.core.exceptions import PermissaoNegada
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv('000.999.400', 'Parafuso', '1.000')
        with pytest.raises(PermissaoNegada):
            confirmar_importacao_scpi(
                ator_id=chefe_almoxarifado.pk,
                conteudo_bytes=csv_bytes,
                arquivo_nome='negado.csv',
                estoque_id=estoque_principal.pk,
            )

    def test_total_novos_e_divergentes_gravados(
        self, db, superuser, estoque_principal, material_scpi
    ):
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = (
            'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi.codigo};Parafuso M6;999.000\n'
            '000.999.500;Material Nv;5.000\n'
        ).encode('utf-8')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='mix.csv',
            estoque_id=estoque_principal.pk,
        )
        assert importacao.total_linhas == 2
        assert importacao.total_novos == 1
        assert importacao.total_divergentes == 1


class TestConfirmarImportacaoScpiDivergenciasPersistidas:
    """A lista de divergências é gravada com a confirmação (#161)."""

    def _csv(self, cadpro: str, denominacao: str, quantidade: str) -> bytes:
        return (
            f'CADPRO;DENOMINACAO;QUAN3\n{cadpro};{denominacao};{quantidade}\n'.encode(
                'utf-8'
            )
        )

    def test_grava_linha_divergente_com_cadpro_saldos_e_delta(
        self, db, superuser, estoque_principal, material_scpi
    ):
        from decimal import Decimal

        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        # material_scpi tem saldo_fisico 100 no WMS.
        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '130.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='div.csv',
            estoque_id=estoque_principal.pk,
        )

        (linha,) = LinhaDivergenteSCPI.objects.filter(importacao=importacao)
        assert linha.cadpro == material_scpi.codigo
        assert linha.denominacao == material_scpi.nome
        assert linha.saldo_wms == Decimal('100.000')
        assert linha.saldo_scpi == Decimal('130.000')
        assert linha.delta == Decimal('30.000')

    def test_importacao_sem_divergencia_nao_grava_linha(
        self, db, superuser, estoque_principal, material_scpi
    ):
        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '100.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='igual.csv',
            estoque_id=estoque_principal.pk,
        )
        assert importacao.total_divergentes == 0
        assert not LinhaDivergenteSCPI.objects.filter(importacao=importacao).exists()

    def test_linha_nova_e_linha_ok_nao_viram_divergencia(
        self, db, superuser, estoque_principal, material_scpi
    ):
        """Só `divergente` entra: `ok` não é informação e `novo` já virou catálogo."""
        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = (
            'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi.codigo};Parafuso M6;100.000\n'
            '000.999.910;Material Novo;5.000\n'
        ).encode('utf-8')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='ok-e-novo.csv',
            estoque_id=estoque_principal.pk,
        )
        assert not LinhaDivergenteSCPI.objects.filter(importacao=importacao).exists()

    def test_contagem_de_linhas_gravadas_bate_com_total_divergentes(
        self, db, superuser, estoque_principal, material_scpi, material_scpi_critico
    ):
        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = (
            'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi.codigo};Parafuso M6;001.000\n'
            f'{material_scpi_critico.codigo};Crítico;009.000\n'
        ).encode('utf-8')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='duas.csv',
            estoque_id=estoque_principal.pk,
        )
        assert importacao.total_divergentes == 2
        assert LinhaDivergenteSCPI.objects.filter(importacao=importacao).count() == 2

    def test_reimportacao_bloqueada_nao_deixa_divergencia_orfa(
        self, db, superuser, estoque_principal, material_scpi
    ):
        """Mesma transação da confirmação: se ela não vale, a lista não existe."""
        import pytest

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '130.000')
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='primeira.csv',
            estoque_id=estoque_principal.pk,
        )
        antes = LinhaDivergenteSCPI.objects.count()

        with pytest.raises(ConflitoDominio):
            confirmar_importacao_scpi(
                ator_id=superuser.pk,
                conteudo_bytes=csv_bytes,
                arquivo_nome='segunda.csv',
                estoque_id=estoque_principal.pk,
            )
        assert LinhaDivergenteSCPI.objects.count() == antes

    def test_denominacao_e_instantaneo_e_nao_acompanha_renomeacao(
        self, db, superuser, estoque_principal, material_scpi
    ):
        """Registro de auditoria: o que foi conferido não muda depois."""
        from apps.estoque.models import LinhaDivergenteSCPI
        from apps.estoque.services import confirmar_importacao_scpi

        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '130.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='snap.csv',
            estoque_id=estoque_principal.pk,
        )
        material_scpi.nome = 'Parafuso M6 sextavado'
        material_scpi.save(update_fields=['nome'])

        (linha,) = LinhaDivergenteSCPI.objects.filter(importacao=importacao)
        assert linha.denominacao == 'Parafuso M6'


class TestConfirmarImportacaoScpiTimelineRequisicoes:
    """atualizacao_estoque_relevante registrado em requisições autorizadas afetadas."""

    def _csv(self, cadpro: str, denominacao: str, quantidade: str) -> bytes:
        """Monta CSV SCPI mínimo com uma linha."""
        return (
            f'CADPRO;DENOMINACAO;QUAN3\n{cadpro};{denominacao};{quantidade}\n'.encode(
                'utf-8'
            )
        )

    def test_cria_evento_quando_divergencia_critica_e_requisicao_autorizada(
        self,
        db,
        superuser,
        estoque_principal,
        material_scpi_critico,
        requisicao_autorizada_critico,
    ):
        """Happy path: material crítico + requisição autorizada → evento criado com metadata correto."""
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        csv_bytes = self._csv(material_scpi_critico.codigo, 'Tinta Branca 18L', '1.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='crit.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=registrar_timeline_divergencia_importacao,
        )

        eventos = TimelineRequisicao.objects.filter(
            requisicao=requisicao_autorizada_critico,
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE,
        )
        assert eventos.count() == 1
        evento = eventos.first()
        assert evento.metadata['importacao_id'] == importacao.pk
        assert any(
            m['codigo'] == material_scpi_critico.codigo
            for m in evento.metadata['materiais']
        )
        assert any(
            m['nome'] == material_scpi_critico.nome
            for m in evento.metadata['materiais']
        )

    def test_nao_cria_evento_quando_saldo_nao_critico(
        self, db, superuser, estoque_principal, solicitante, setor_obras
    ):
        """Material divergente (SCPI != WMS) mas não crítico: sem evento."""
        from decimal import Decimal

        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.models import (
            EstadoRequisicao,
            EventoTimeline,
            ItemRequisicao,
            Requisicao,
            TimelineRequisicao,
        )

        m = Material.objects.create(
            codigo='000.000.010',
            nome='Parafuso M8',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal, material=m, saldo_fisico=10, saldo_reservado=5
        )
        req = Requisicao.objects.create(
            estado=EstadoRequisicao.AUTORIZADA,
            numero_publico='REQ-2025-000010',
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        ItemRequisicao.objects.create(
            requisicao=req,
            material=m,
            quantidade_solicitada=Decimal('5'),
            quantidade_autorizada=Decimal('5'),
        )

        # SCPI diz 8 (divergente de WMS=10), mas saldo_fisico=10 >= saldo_reservado=5
        csv_bytes = self._csv(m.codigo, 'Parafuso M8', '8.000')
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='nao_crit.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=registrar_timeline_divergencia_importacao,
        )

        assert not TimelineRequisicao.objects.filter(
            requisicao=req,
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE,
        ).exists()

    def test_nao_cria_evento_sem_requisicao_autorizada(
        self, db, superuser, estoque_principal, material_scpi_critico
    ):
        """Material crítico mas sem requisição autorizada: sem evento."""
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        csv_bytes = self._csv(material_scpi_critico.codigo, 'Tinta Branca 18L', '1.000')
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='sem_req.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=registrar_timeline_divergencia_importacao,
        )

        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE,
        ).exists()

    def test_evento_agregado_com_multiplos_materiais_criticos(
        self, db, superuser, estoque_principal, solicitante, setor_obras
    ):
        """Dois materiais críticos na mesma requisição: um evento com lista agregada."""
        from decimal import Decimal

        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.models import (
            EstadoRequisicao,
            EventoTimeline,
            ItemRequisicao,
            Requisicao,
            TimelineRequisicao,
        )

        m1 = Material.objects.create(
            codigo='000.000.011',
            nome='Material A',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        m2 = Material.objects.create(
            codigo='000.000.012',
            nome='Material B',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal, material=m1, saldo_fisico=2, saldo_reservado=5
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal, material=m2, saldo_fisico=1, saldo_reservado=3
        )

        req = Requisicao.objects.create(
            estado=EstadoRequisicao.AUTORIZADA,
            numero_publico='REQ-2025-000011',
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        ItemRequisicao.objects.create(
            requisicao=req,
            material=m1,
            quantidade_solicitada=Decimal('3'),
            quantidade_autorizada=Decimal('3'),
        )
        ItemRequisicao.objects.create(
            requisicao=req,
            material=m2,
            quantidade_solicitada=Decimal('2'),
            quantidade_autorizada=Decimal('2'),
        )

        csv_bytes = (
            'CADPRO;DENOMINACAO;QUAN3\n'
            f'{m1.codigo};Material A;1.000\n'
            f'{m2.codigo};Material B;1.000\n'
        ).encode('utf-8')
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='multi.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=registrar_timeline_divergencia_importacao,
        )

        eventos = TimelineRequisicao.objects.filter(
            requisicao=req,
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE,
        )
        assert eventos.count() == 1
        codigos = {m['codigo'] for m in eventos.first().metadata['materiais']}
        assert codigos == {m1.codigo, m2.codigo}
        assert eventos.first().metadata['importacao_id'] == importacao.pk

    def test_hook_retorna_ids_das_requisicoes_avisadas(
        self,
        db,
        superuser,
        estoque_principal,
        material_scpi_critico,
        requisicao_autorizada_critico,
    ):
        """O hook devolve os ids das requisições avisadas, para o chamador reagir."""
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        capturado: list[list[int]] = []

        def _hook(**kwargs):
            capturado.append(registrar_timeline_divergencia_importacao(**kwargs))

        csv_bytes = self._csv(material_scpi_critico.codigo, 'Tinta Branca 18L', '1.000')
        confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='retorno.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=_hook,
        )

        assert capturado == [[requisicao_autorizada_critico.pk]]

    def test_hook_retorna_lista_vazia_sem_divergencia(
        self, db, superuser, estoque_principal, material_scpi
    ):
        """Sem divergência crítica o hook devolve lista vazia, nunca None."""
        from apps.estoque.services import confirmar_importacao_scpi
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_importacao,
        )

        capturado: list[list[int]] = []

        def _hook(**kwargs):
            capturado.append(registrar_timeline_divergencia_importacao(**kwargs))

        csv_bytes = self._csv(material_scpi.codigo, 'Parafuso M6', '100.000')
        importacao = confirmar_importacao_scpi(
            ator_id=superuser.pk,
            conteudo_bytes=csv_bytes,
            arquivo_nome='sem_divergencia.csv',
            estoque_id=estoque_principal.pk,
            _pos_importacao_hook=_hook,
        )

        assert capturado == [[]]
        assert importacao.pk is not None


class TestMovimentacaoEstoqueImutavel:
    @pytest.mark.django_db
    def test_save_apos_criacao_levanta_excecao(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from apps.estoque.models import MovimentacaoEstoque, MovimentacaoEstoqueImutavel

        mov = MovimentacaoEstoque.objects.filter(
            saida_excepcional=saida_registrada
        ).first()
        assert mov is not None
        with pytest.raises(MovimentacaoEstoqueImutavel):
            mov.delta_fisico = mov.delta_fisico + 1
            mov.save()

    @pytest.mark.django_db
    def test_delete_levanta_excecao(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from apps.estoque.models import MovimentacaoEstoque, MovimentacaoEstoqueImutavel

        mov = MovimentacaoEstoque.objects.filter(
            saida_excepcional=saida_registrada
        ).first()
        assert mov is not None
        with pytest.raises(MovimentacaoEstoqueImutavel):
            mov.delete()


class TestLedgerRegistrarSaidaExcepcional:
    @pytest.mark.django_db
    def test_emite_movimentacao_saida_excepcional(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque

        movs = MovimentacaoEstoque.objects.filter(saida_excepcional=saida_registrada)
        assert movs.count() == 1
        mov = movs.first()
        assert mov.tipo == TipoMovimentacaoEstoque.SAIDA_EXCEPCIONAL
        assert mov.material == material_disponivel
        assert mov.estoque == estoque_principal
        assert mov.delta_fisico == Decimal('-5')
        assert mov.delta_reservado == Decimal('0')
        assert mov.ator == chefe_almoxarifado


class TestLedgerEstornarSaidaExcepcional:
    @pytest.mark.django_db
    def test_emite_movimentacao_estorno_saida(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
        from apps.estoque.services import estornar_saida_excepcional

        estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Estorno de teste',
        )

        movs = MovimentacaoEstoque.objects.filter(saida_excepcional=saida_registrada)
        tipos = list(movs.values_list('tipo', flat=True))
        assert TipoMovimentacaoEstoque.ESTORNO_SAIDA in tipos

        mov_estorno = movs.get(tipo=TipoMovimentacaoEstoque.ESTORNO_SAIDA)
        assert mov_estorno.delta_fisico == Decimal('5')
        assert mov_estorno.delta_reservado == Decimal('0')
        assert mov_estorno.ator == chefe_almoxarifado


class TestLedgerReservarSaldos:
    @pytest.mark.django_db
    def test_emite_movimentacao_reserva(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizavel,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
        from apps.estoque.services import (
            OrigemMovimentacaoEstoque,
            reservar_saldos_para_autorizacao,
        )

        reservar_saldos_para_autorizacao(
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_solicitada': Decimal('3'),
                }
            ],
            ator_id=chefe_almoxarifado.pk,
            origem=OrigemMovimentacaoEstoque.de_requisicao(requisicao_autorizavel),
        )

        movs = MovimentacaoEstoque.objects.filter(requisicao=requisicao_autorizavel)
        assert movs.count() == 1
        mov = movs.first()
        assert mov.tipo == TipoMovimentacaoEstoque.RESERVA
        assert mov.delta_fisico == Decimal('0')
        assert mov.delta_reservado == Decimal('3')
        assert mov.ator == chefe_almoxarifado


class TestLedgerLiberarReservas:
    @pytest.mark.django_db
    def test_emite_movimentacao_liberacao(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
        from apps.estoque.services import (
            OrigemMovimentacaoEstoque,
            liberar_reservas_para_cancelamento,
        )

        req, item = requisicao_autorizada

        liberar_reservas_para_cancelamento(
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_reservada': Decimal('5'),
                }
            ],
            ator_id=chefe_almoxarifado.pk,
            origem=OrigemMovimentacaoEstoque.de_requisicao(req),
        )

        movs = MovimentacaoEstoque.objects.filter(
            requisicao=req, tipo=TipoMovimentacaoEstoque.LIBERACAO
        )
        assert movs.count() == 1
        mov = movs.first()
        assert mov.delta_fisico == Decimal('0')
        assert mov.delta_reservado == Decimal('-5')


class TestLedgerConsumirReservas:
    @pytest.mark.django_db
    def test_emite_movimentacao_consumo(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque
        from apps.estoque.services import (
            OrigemMovimentacaoEstoque,
            consumir_e_liberar_reservas_para_atendimento,
        )

        req, item = requisicao_autorizada

        consumir_e_liberar_reservas_para_atendimento(
            itens=[
                {
                    'material_id': material_disponivel.pk,
                    'quantidade_autorizada': Decimal('5'),
                    'quantidade_entregue': Decimal('4'),
                }
            ],
            ator_id=chefe_almoxarifado.pk,
            origem=OrigemMovimentacaoEstoque.de_requisicao(req),
        )

        movs = MovimentacaoEstoque.objects.filter(
            requisicao=req, tipo=TipoMovimentacaoEstoque.CONSUMO
        )
        assert movs.count() == 1
        mov = movs.first()
        assert mov.delta_fisico == Decimal('-4')
        assert mov.delta_reservado == Decimal('-5')


class TestLedgerReconciliacao:
    @pytest.mark.django_db
    def test_soma_delta_fisico_reconcilia_com_saldo(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        saida_registrada,
    ):
        from decimal import Decimal

        from django.db.models import Sum

        from apps.estoque.models import MovimentacaoEstoque, SaldoEstoque
        from apps.estoque.services import estornar_saida_excepcional

        saldo_inicial = Decimal('100')

        estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Reconciliação de teste',
        )

        total_delta = MovimentacaoEstoque.objects.filter(
            estoque=estoque_principal,
            material=material_disponivel,
        ).aggregate(total=Sum('delta_fisico'))['total'] or Decimal('0')

        saldo_atual = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        ).saldo_fisico

        assert saldo_atual == saldo_inicial + total_delta


@pytest.mark.django_db(transaction=True)
class TestLedgerConcorrenciaEST06:
    def test_locks_preservados_com_ledger(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizavel,
    ):
        """EST-06: lock determinístico preservado após retrofit do ledger."""
        import threading
        from decimal import Decimal

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )
        from apps.estoque.services import (
            OrigemMovimentacaoEstoque,
            reservar_saldos_para_autorizacao,
        )

        erros = []

        def reservar():
            try:
                reservar_saldos_para_autorizacao(
                    itens=[
                        {
                            'material_id': material_disponivel.pk,
                            'quantidade_solicitada': Decimal('1'),
                        }
                    ],
                    ator_id=chefe_almoxarifado.pk,
                    origem=OrigemMovimentacaoEstoque.de_requisicao(
                        requisicao_autorizavel
                    ),
                )
            except Exception as e:
                erros.append(e)

        t1 = threading.Thread(target=reservar)
        t2 = threading.Thread(target=reservar)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        saldo = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        movs = MovimentacaoEstoque.objects.filter(
            requisicao=requisicao_autorizavel,
            tipo=TipoMovimentacaoEstoque.RESERVA,
        )
        # Ambas as threads devem ter completado sem erro
        assert not erros
        # saldo_reservado aumentou 2 (1 por thread)
        assert saldo.saldo_reservado == Decimal('10') + Decimal('2')
        # 2 movimentações criadas
        assert movs.count() == 2


@pytest.mark.django_db
class TestDesativarMaterial:
    def _cria_material_com_saldo(self, estoque_principal, fisico, reservado):
        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

        m = Material.objects.create(
            codigo='DESATMAT001',
            nome='Material Desativável',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal,
            material=m,
            saldo_fisico=fisico,
            saldo_reservado=reservado,
        )
        return m

    def test_saldo_fisico_nao_zerado_lanca_conflito(self, superuser, estoque_principal):
        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import desativar_material

        m = self._cria_material_com_saldo(estoque_principal, fisico=10, reservado=0)
        with pytest.raises(ConflitoDominio) as exc_info:
            desativar_material(ator_id=superuser.pk, material_id=m.pk)
        assert exc_info.value.code == 'saldo_fisico_nao_zerado'

    def test_saldo_reservado_nao_zerado_lanca_conflito(
        self, superuser, estoque_principal
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import desativar_material

        m = self._cria_material_com_saldo(estoque_principal, fisico=0, reservado=5)
        with pytest.raises(ConflitoDominio) as exc_info:
            desativar_material(ator_id=superuser.pk, material_id=m.pk)
        assert exc_info.value.code == 'saldo_reservado_nao_zerado'

    def test_saldo_zerado_desativa_material(self, superuser, estoque_principal):
        from apps.estoque.services import desativar_material

        m = self._cria_material_com_saldo(estoque_principal, fisico=0, reservado=0)
        desativar_material(ator_id=superuser.pk, material_id=m.pk)
        m.refresh_from_db()
        assert m.ativo is False

    def test_ja_inativo_e_idempotente(self, superuser, estoque_principal):
        from apps.estoque.services import desativar_material

        m = self._cria_material_com_saldo(estoque_principal, fisico=0, reservado=0)
        m.ativo = False
        m.save(update_fields=['ativo'])
        desativar_material(ator_id=superuser.pk, material_id=m.pk)
        m.refresh_from_db()
        assert m.ativo is False


class TestRegistrarDevolucaoEstoque:
    """Contrato de registrar_devolucao_estoque."""

    def _setup_consumo(self, req, material, estoque, ator, quantidade):
        from django.db.models import F

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )

        MovimentacaoEstoque.objects.create(
            tipo=TipoMovimentacaoEstoque.CONSUMO,
            material=material,
            estoque=estoque,
            delta_fisico=-quantidade,
            delta_reservado=-quantidade,
            requisicao=req,
            ator=ator,
        )
        SaldoEstoque.objects.filter(material=material, estoque=estoque).update(
            saldo_fisico=F('saldo_fisico') - quantidade,
            saldo_reservado=F('saldo_reservado') - quantidade,
        )

    @pytest.mark.django_db
    def test_happy_path_incrementa_saldo_e_emite_ledger(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )
        from apps.estoque.services import registrar_devolucao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('3'),
        )

        saldo = SaldoEstoque.objects.get(material=material_disponivel)
        saldo_fisico_antes = saldo.saldo_fisico

        registrar_devolucao_estoque(
            requisicao_id=req.pk,
            material_id=material_disponivel.pk,
            quantidade=Decimal('2'),
            ator_id=chefe_almoxarifado.pk,
        )

        saldo.refresh_from_db()
        assert saldo.saldo_fisico == saldo_fisico_antes + Decimal('2')

        mov = MovimentacaoEstoque.objects.get(
            requisicao=req,
            material=material_disponivel,
            tipo=TipoMovimentacaoEstoque.DEVOLUCAO,
        )
        assert mov.delta_fisico == Decimal('2')
        assert mov.delta_reservado == Decimal('0')
        assert mov.ator_id == chefe_almoxarifado.pk

    @pytest.mark.django_db
    def test_quantidade_excede_entregue_liquida_lanca_conflito(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import registrar_devolucao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('2'),
        )

        with pytest.raises(ConflitoDominio) as exc:
            registrar_devolucao_estoque(
                requisicao_id=req.pk,
                material_id=material_disponivel.pk,
                quantidade=Decimal('3'),
                ator_id=chefe_almoxarifado.pk,
            )
        assert exc.value.code == 'quantidade_excede_entregue_liquida'

    @pytest.mark.django_db
    def test_material_inativo_lanca_conflito(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import registrar_devolucao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('2'),
        )
        material_disponivel.ativo = False
        material_disponivel.save(update_fields=['ativo'])

        with pytest.raises(ConflitoDominio) as exc:
            registrar_devolucao_estoque(
                requisicao_id=req.pk,
                material_id=material_disponivel.pk,
                quantidade=Decimal('1'),
                ator_id=chefe_almoxarifado.pk,
            )
        assert exc.value.code == 'material_inativo'

    @pytest.mark.django_db
    def test_sem_saldo_lanca_conflito(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.models import SaldoEstoque
        from apps.estoque.services import registrar_devolucao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('2'),
        )
        SaldoEstoque.objects.filter(material=material_disponivel).delete()

        with pytest.raises(ConflitoDominio) as exc:
            registrar_devolucao_estoque(
                requisicao_id=req.pk,
                material_id=material_disponivel.pk,
                quantidade=Decimal('1'),
                ator_id=chefe_almoxarifado.pk,
            )
        assert exc.value.code == 'saldo_nao_encontrado'


class TestEstornarRequisicaoEstoque:
    """Contrato de estornar_requisicao_estoque."""

    def _setup_consumo(self, req, material, estoque, ator, quantidade):
        from django.db.models import F

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )

        MovimentacaoEstoque.objects.create(
            tipo=TipoMovimentacaoEstoque.CONSUMO,
            material=material,
            estoque=estoque,
            delta_fisico=-quantidade,
            delta_reservado=-quantidade,
            requisicao=req,
            ator=ator,
        )
        SaldoEstoque.objects.filter(material=material, estoque=estoque).update(
            saldo_fisico=F('saldo_fisico') - quantidade,
            saldo_reservado=F('saldo_reservado') - quantidade,
        )

    @pytest.mark.django_db
    def test_happy_path_restaura_saldo_e_emite_ledger(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )
        from apps.estoque.services import estornar_requisicao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('4'),
        )

        saldo = SaldoEstoque.objects.get(material=material_disponivel)
        saldo_fisico_antes = saldo.saldo_fisico

        estornar_requisicao_estoque(
            requisicao_id=req.pk,
            material_ids=[material_disponivel.pk],
            ator_id=chefe_almoxarifado.pk,
        )

        saldo.refresh_from_db()
        assert saldo.saldo_fisico == saldo_fisico_antes + Decimal('4')

        mov = MovimentacaoEstoque.objects.get(
            requisicao=req,
            material=material_disponivel,
            tipo=TipoMovimentacaoEstoque.ESTORNO_REQUISICAO,
        )
        assert mov.delta_fisico == Decimal('4')
        assert mov.delta_reservado == Decimal('0')

    @pytest.mark.django_db
    def test_sem_entregue_liquida_lanca_conflito(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.services import estornar_requisicao_estoque

        req, item = requisicao_autorizada

        with pytest.raises(ConflitoDominio) as exc:
            estornar_requisicao_estoque(
                requisicao_id=req.pk,
                material_ids=[material_disponivel.pk],
                ator_id=chefe_almoxarifado.pk,
            )
        assert exc.value.code == 'sem_liquida_para_estorno'

    @pytest.mark.django_db
    def test_sem_saldo_para_material_lanca_conflito(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        from decimal import Decimal

        from apps.core.exceptions import ConflitoDominio
        from apps.estoque.models import SaldoEstoque
        from apps.estoque.services import estornar_requisicao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('3'),
        )
        SaldoEstoque.objects.filter(material=material_disponivel).delete()

        with pytest.raises(ConflitoDominio) as exc:
            estornar_requisicao_estoque(
                requisicao_id=req.pk,
                material_ids=[material_disponivel.pk],
                ator_id=chefe_almoxarifado.pk,
            )
        assert exc.value.code == 'saldo_nao_encontrado'

    @pytest.mark.django_db
    def test_falha_em_saldo_save_rollback_atomico(
        self,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        """Falha durante saldo.save() → SaldoEstoque e ledger permanecem inalterados."""
        from decimal import Decimal
        from unittest.mock import patch

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
        )
        from apps.estoque.services import estornar_requisicao_estoque

        req, item = requisicao_autorizada
        self._setup_consumo(
            req,
            material_disponivel,
            estoque_principal,
            chefe_almoxarifado,
            Decimal('3'),
        )

        saldo = SaldoEstoque.objects.get(material=material_disponivel)
        saldo_fisico_antes = saldo.saldo_fisico
        ledger_antes = MovimentacaoEstoque.objects.filter(
            requisicao=req,
            tipo=TipoMovimentacaoEstoque.ESTORNO_REQUISICAO,
        ).count()

        def _raise(*args, **kwargs):
            raise RuntimeError('erro forçado no saldo.save()')

        with patch.object(SaldoEstoque, 'save', _raise):
            with pytest.raises(RuntimeError):
                estornar_requisicao_estoque(
                    requisicao_id=req.pk,
                    material_ids=[material_disponivel.pk],
                    ator_id=chefe_almoxarifado.pk,
                )

        saldo.refresh_from_db()
        assert saldo.saldo_fisico == saldo_fisico_antes
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=req,
                tipo=TipoMovimentacaoEstoque.ESTORNO_REQUISICAO,
            ).count()
            == ledger_antes
        )


# ---------------------------------------------------------------------------
# Issue #111 — saída excepcional que cria divergência crítica (EST-07) avisa
# as requisições autorizadas afetadas
# ---------------------------------------------------------------------------


@pytest.fixture
def _hook_divergencia_saida():
    """Hook real de divergência da saída excepcional, capturando o retorno."""
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_saida_excepcional,
    )

    capturado: list[list[int]] = []

    def _hook(**kwargs):
        avisadas = registrar_timeline_divergencia_saida_excepcional(**kwargs)
        capturado.append(avisadas)
        return avisadas

    _hook.capturado = capturado
    return _hook


class TestSaidaExcepcionalDivergenciaTimeline:
    """EST-07 criada por saída excepcional avisa as requisições autorizadas."""

    def _baixar(self, *, ator, estoque, material, quantidade, hook):
        from apps.estoque.services import registrar_saida_excepcional

        return registrar_saida_excepcional(
            ator_id=ator.pk,
            estoque_id=estoque.pk,
            motivo='Descarte por avaria',
            observacao='Material avariado em vistoria',
            itens=[{'material_id': material.pk, 'quantidade': quantidade}],
            _pos_saida_hook=hook,
        )

    def test_cria_evento_e_notifica_quando_baixa_gera_divergencia(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
        _hook_divergencia_saida,
    ):
        """Happy path: baixa empurra físico abaixo do reservado → evento com metadata da saída."""
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        req, _item = requisicao_autorizada

        saida = self._baixar(
            ator=chefe_almoxarifado,
            estoque=estoque_principal,
            material=material_disponivel,
            quantidade='98',
            hook=_hook_divergencia_saida,
        )

        eventos = TimelineRequisicao.objects.filter(
            requisicao=req,
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE,
        )
        assert eventos.count() == 1
        evento = eventos.first()
        assert evento.metadata['saida_excepcional_id'] == saida.pk
        assert evento.metadata['numero_publico'] == saida.numero_publico
        assert evento.metadata['materiais'] == [
            {'codigo': material_disponivel.codigo, 'nome': material_disponivel.nome}
        ]
        assert _hook_divergencia_saida.capturado == [[req.pk]]

    def test_nao_cria_evento_quando_baixa_nao_gera_divergencia(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
        _hook_divergencia_saida,
    ):
        """Baixa que mantém físico >= reservado não avisa ninguém."""
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        self._baixar(
            ator=chefe_almoxarifado,
            estoque=estoque_principal,
            material=material_disponivel,
            quantidade='5',
            hook=_hook_divergencia_saida,
        )

        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        ).exists()
        assert _hook_divergencia_saida.capturado == [[]]

    def test_nao_avisa_requisicao_que_nao_esta_autorizada(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizavel,
        _hook_divergencia_saida,
    ):
        """Só requisição AUTORIZADA é avisada; aguardando autorização não é."""
        from apps.estoque.models import SaldoEstoque
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        saldo = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        saldo.saldo_reservado = 50
        saldo.save(update_fields=['saldo_reservado'])

        self._baixar(
            ator=chefe_almoxarifado,
            estoque=estoque_principal,
            material=material_disponivel,
            quantidade='60',
            hook=_hook_divergencia_saida,
        )

        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        ).exists()
        assert _hook_divergencia_saida.capturado == [[]]

    def test_evento_agregado_com_dois_materiais_criticos_na_mesma_requisicao(
        self,
        db,
        chefe_almoxarifado,
        solicitante,
        setor_obras,
        estoque_principal,
        _hook_divergencia_saida,
    ):
        """Um evento por requisição, agregando os dois materiais afetados."""
        from decimal import Decimal

        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida
        from apps.estoque.services import registrar_saida_excepcional
        from apps.requisicoes.models import (
            EstadoRequisicao,
            EventoTimeline,
            ItemRequisicao,
            Requisicao,
            TimelineRequisicao,
        )

        materiais = []
        for indice in (1, 2):
            material = Material.objects.create(
                codigo=f'AGG00{indice}',
                nome=f'Material agregado {indice}',
                unidade=UnidadeMedida.UNIDADE,
                ativo=True,
            )
            SaldoEstoque.objects.create(
                estoque=estoque_principal,
                material=material,
                saldo_fisico=10,
                saldo_reservado=8,
            )
            materiais.append(material)

        req = Requisicao.objects.create(
            estado=EstadoRequisicao.AUTORIZADA,
            numero_publico='REQ-2025-000201',
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_obras,
        )
        for material in materiais:
            ItemRequisicao.objects.create(
                requisicao=req,
                material=material,
                quantidade_solicitada=Decimal('8'),
                quantidade_autorizada=Decimal('8'),
            )

        saida = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='Descarte por avaria',
            observacao='Lote inteiro avariado',
            itens=[{'material_id': m.pk, 'quantidade': '5'} for m in materiais],
            _pos_saida_hook=_hook_divergencia_saida,
        )

        eventos = TimelineRequisicao.objects.filter(
            requisicao=req, evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        )
        assert eventos.count() == 1
        evento = eventos.first()
        assert evento.metadata['saida_excepcional_id'] == saida.pk
        codigos = sorted(m['codigo'] for m in evento.metadata['materiais'])
        assert codigos == ['AGG001', 'AGG002']

    def test_duas_requisicoes_autorizadas_compartilhando_material_critico(
        self,
        db,
        chefe_almoxarifado,
        solicitante,
        setor_obras,
        estoque_principal,
        material_disponivel,
        _hook_divergencia_saida,
    ):
        """Um evento por requisição, sem agregação cruzada nem omissão."""
        from decimal import Decimal

        from apps.accounts.models import User
        from apps.estoque.models import SaldoEstoque
        from apps.requisicoes.models import (
            EstadoRequisicao,
            EventoTimeline,
            ItemRequisicao,
            Requisicao,
            TimelineRequisicao,
        )

        outro_solicitante = User.objects.create_user(
            matricula='0111',
            nome='Carla Solicitante',
            password='senha',
            setor=setor_obras,
        )

        saldo = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        saldo.saldo_reservado = 20
        saldo.save(update_fields=['saldo_reservado'])

        requisicoes = []
        for indice, usuario in enumerate((solicitante, outro_solicitante), start=1):
            req = Requisicao.objects.create(
                estado=EstadoRequisicao.AUTORIZADA,
                numero_publico=f'REQ-2025-00030{indice}',
                criador=usuario,
                beneficiario=usuario,
                setor_beneficiario=setor_obras,
            )
            ItemRequisicao.objects.create(
                requisicao=req,
                material=material_disponivel,
                quantidade_solicitada=Decimal('10'),
                quantidade_autorizada=Decimal('10'),
            )
            requisicoes.append(req)

        saida = self._baixar(
            ator=chefe_almoxarifado,
            estoque=estoque_principal,
            material=material_disponivel,
            quantidade='90',
            hook=_hook_divergencia_saida,
        )

        for req in requisicoes:
            eventos = TimelineRequisicao.objects.filter(
                requisicao=req, evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
            )
            assert eventos.count() == 1
            evento = eventos.first()
            assert evento.metadata['saida_excepcional_id'] == saida.pk
            assert evento.metadata['numero_publico'] == saida.numero_publico
            assert evento.metadata['materiais'] == [
                {'codigo': material_disponivel.codigo, 'nome': material_disponivel.nome}
            ]

        assert sorted(_hook_divergencia_saida.capturado[0]) == sorted(
            r.pk for r in requisicoes
        )

    def test_baixa_persiste_sem_reserva_nem_requisicao_autorizada(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        _hook_divergencia_saida,
    ):
        """SAE-01: o hook seleciona quem notificar, nunca condiciona a baixa."""
        from decimal import Decimal

        from apps.estoque.models import (
            ItemSaidaExcepcional,
            Material,
            MovimentacaoEstoque,
            SaldoEstoque,
            TipoMovimentacaoEstoque,
            UnidadeMedida,
        )
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        material = Material.objects.create(
            codigo='SEMRESERVA',
            nome='Material sem reserva',
            unidade=UnidadeMedida.UNIDADE,
            ativo=True,
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal,
            material=material,
            saldo_fisico=40,
            saldo_reservado=0,
        )

        saida = self._baixar(
            ator=chefe_almoxarifado,
            estoque=estoque_principal,
            material=material,
            quantidade='15',
            hook=_hook_divergencia_saida,
        )

        assert saida.numero_publico.startswith('SXP-')
        assert ItemSaidaExcepcional.objects.filter(saida=saida).count() == 1
        assert MovimentacaoEstoque.objects.filter(
            saida_excepcional=saida,
            material=material,
            tipo=TipoMovimentacaoEstoque.SAIDA_EXCEPCIONAL,
            delta_fisico=Decimal('-15'),
        ).exists()

        saldo = SaldoEstoque.objects.get(estoque=estoque_principal, material=material)
        assert saldo.saldo_fisico == Decimal('25')

        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        ).exists()
        assert _hook_divergencia_saida.capturado == [[]]

    def test_sem_hook_a_baixa_funciona_e_nao_avisa(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        """Compatibilidade retroativa: _pos_saida_hook é opcional."""
        from apps.estoque.services import registrar_saida_excepcional
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        saida = registrar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            estoque_id=estoque_principal.pk,
            motivo='Descarte por avaria',
            observacao='Material avariado em vistoria',
            itens=[{'material_id': material_disponivel.pk, 'quantidade': '98'}],
        )

        assert saida.numero_publico.startswith('SXP-')
        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        ).exists()

    def test_falha_no_hook_reverte_a_saida_inteira(
        self,
        db,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        """SAE-04: exceção no hook acontece antes do commit e derruba tudo."""
        from decimal import Decimal

        from apps.estoque.models import (
            MovimentacaoEstoque,
            SaidaExcepcional,
            SaldoEstoque,
        )
        from apps.requisicoes.models import EventoTimeline, TimelineRequisicao

        saldo_antes = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        ).saldo_fisico

        def _hook_que_falha(**kwargs):
            raise RuntimeError('falha forçada no hook')

        with pytest.raises(RuntimeError):
            self._baixar(
                ator=chefe_almoxarifado,
                estoque=estoque_principal,
                material=material_disponivel,
                quantidade='98',
                hook=_hook_que_falha,
            )

        assert not SaidaExcepcional.objects.exists()
        assert not MovimentacaoEstoque.objects.filter(
            saida_excepcional__isnull=False
        ).exists()
        assert not TimelineRequisicao.objects.filter(
            evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
        ).exists()

        saldo = SaldoEstoque.objects.get(
            estoque=estoque_principal, material=material_disponivel
        )
        assert saldo.saldo_fisico == Decimal(saldo_antes)


@pytest.mark.django_db(transaction=True)
def test_falha_ao_notificar_pos_commit_nao_reverte_a_saida(
    chefe_almoxarifado,
    estoque_principal,
    material_disponivel,
    requisicao_autorizada,
    caplog,
):
    """A entrega da notificação é best-effort: falha depois do commit não reverte nada."""
    from decimal import Decimal
    from unittest.mock import patch

    from apps.estoque.models import MovimentacaoEstoque, SaidaExcepcional, SaldoEstoque
    from apps.estoque.services import registrar_saida_excepcional
    from apps.notificacoes.models import Notificacao
    from apps.requisicoes.models import EventoTimeline, TimelineRequisicao
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_saida_excepcional,
    )

    req, _item = requisicao_autorizada

    with patch(
        'apps.requisicoes.services.ciclo_vida.criar_notificacoes_para',
        side_effect=RuntimeError('falha forçada na notificação'),
    ):
        with caplog.at_level('ERROR', logger='apps.requisicoes.services.ciclo_vida'):
            saida = registrar_saida_excepcional(
                ator_id=chefe_almoxarifado.pk,
                estoque_id=estoque_principal.pk,
                motivo='Descarte por avaria',
                observacao='Material avariado em vistoria',
                itens=[{'material_id': material_disponivel.pk, 'quantidade': '98'}],
                _pos_saida_hook=registrar_timeline_divergencia_saida_excepcional,
            )

    assert SaidaExcepcional.objects.filter(pk=saida.pk).exists()
    assert MovimentacaoEstoque.objects.filter(saida_excepcional=saida).count() == 1
    assert TimelineRequisicao.objects.filter(
        requisicao=req, evento=EventoTimeline.ATUALIZACAO_ESTOQUE_RELEVANTE
    ).exists()

    saldo = SaldoEstoque.objects.get(
        estoque=estoque_principal, material=material_disponivel
    )
    assert saldo.saldo_fisico == Decimal('2')

    assert not Notificacao.objects.exists()
    assert 'Falha ao criar notificação de divergência pós-commit' in caplog.text


def test_tr_015b_continua_bloqueando_separacao_apos_saida_excepcional(
    db,
    chefe_almoxarifado,
    estoque_principal,
    material_disponivel,
    requisicao_autorizada,
):
    """TR-015B intacto: o aviso é aditivo, não substitui o bloqueio da separação."""
    from apps.core.exceptions import DadosInvalidos
    from apps.estoque.models import MovimentacaoEstoque, SaldoEstoque
    from apps.estoque.services import registrar_saida_excepcional
    from apps.requisicoes.models import EstadoRequisicao
    from apps.requisicoes.services.atendimento import separar_para_retirada
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_saida_excepcional,
    )

    req, _item = requisicao_autorizada

    registrar_saida_excepcional(
        ator_id=chefe_almoxarifado.pk,
        estoque_id=estoque_principal.pk,
        motivo='Descarte por avaria',
        observacao='Material avariado em vistoria',
        itens=[{'material_id': material_disponivel.pk, 'quantidade': '98'}],
        _pos_saida_hook=registrar_timeline_divergencia_saida_excepcional,
    )

    saldo_pos_saida = SaldoEstoque.objects.get(
        estoque=estoque_principal, material=material_disponivel
    )
    fisico_pos_saida = saldo_pos_saida.saldo_fisico
    reservado_pos_saida = saldo_pos_saida.saldo_reservado
    ledger_pos_saida = MovimentacaoEstoque.objects.count()

    with pytest.raises(DadosInvalidos) as exc:
        separar_para_retirada(requisicao_id=req.pk, ator_id=chefe_almoxarifado.pk)
    assert exc.value.code == 'separacao_bloqueada'

    req.refresh_from_db()
    assert req.estado == EstadoRequisicao.AUTORIZADA

    saldo_pos_tentativa = SaldoEstoque.objects.get(
        estoque=estoque_principal, material=material_disponivel
    )
    assert saldo_pos_tentativa.saldo_fisico == fisico_pos_saida
    assert saldo_pos_tentativa.saldo_reservado == reservado_pos_saida
    assert MovimentacaoEstoque.objects.count() == ledger_pos_saida
