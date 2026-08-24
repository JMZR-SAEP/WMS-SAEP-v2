"""Testes de view para estoque.saidas_excepcionais."""

import re
from html.parser import HTMLParser
from pathlib import Path

from django.urls import reverse


URL = reverse('estoque:listar_saidas_excepcionais')


_TAGS_VAZIAS = {'input', 'br', 'hr', 'img', 'meta', 'link'}


class _PilhaDeTags(HTMLParser):
    """Valida aninhamento/fechamento de tags num fragmento HTML (issue #88)."""

    def __init__(self):
        super().__init__()
        self.pilha = []

    def handle_starttag(self, tag, attrs):
        if tag not in _TAGS_VAZIAS:
            self.pilha.append(tag)

    def handle_endtag(self, tag):
        assert self.pilha and self.pilha[-1] == tag, (
            f'fechamento inesperado de </{tag}>: pilha atual {self.pilha}'
        )
        self.pilha.pop()


def _assert_html_balanceado(fragmento):
    parser = _PilhaDeTags()
    parser.feed(fragmento)
    assert parser.pilha == [], f'tags não fechadas: {parser.pilha}'


class TestListarSaidasExcepcionaisView:
    def test_chefe_almox_acessa_lista(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        assert response.status_code == 200

    def test_aux_almox_acessa_lista(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL)
        assert response.status_code == 200

    def test_superuser_acessa_lista(self, client, superuser):
        client.force_login(superuser)
        response = client.get(URL)
        assert response.status_code == 200

    def test_solicitante_recebe_403(self, client, solicitante):
        client.force_login(solicitante)
        response = client.get(URL)
        assert response.status_code == 403

    def test_usuario_inativo_redirecionado_para_login(self, client, usuario_inativo):
        # Django ModelBackend trata is_active=False como não-autenticado;
        # @login_required redireciona para login (USR-01).
        client.force_login(usuario_inativo)
        response = client.get(URL)
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_anonimo_redirecionado_para_login(self, client):
        response = client.get(URL)
        assert response.status_code == 302
        assert (
            '/login' in response['Location'] or 'accounts/login' in response['Location']
        )

    def test_contexto_contem_saidas(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        assert 'saidas' in response.context

    def test_botao_ver_detalhe_preserva_aria_label(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        html = response.content.decode('utf-8')
        assert (
            f'aria-label="Ver detalhe da saída {saida_registrada.numero_publico}"'
            in html
        )

    def test_botao_ver_detalhe_fallback_pk_sem_numero_publico(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        saida_registrada.numero_publico = ''
        saida_registrada.save(update_fields=['numero_publico'])
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        html = response.content.decode('utf-8')
        assert f'aria-label="Ver detalhe da saída {saida_registrada.pk}"' in html

    def test_empty_state_cta_delega_para_componente_button(
        self, client, chefe_almoxarifado
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        html = response.content.decode('utf-8')
        titulo_idx = html.index('Nenhuma saída excepcional registrada')
        match = re.search(r'<a\b[^>]*>', html[titulo_idx:])
        assert match is not None
        tag = match.group()
        assert 'min-h-11' in tag
        assert 'justify-center' in tag
        assert 'focus-visible:ring-offset-1' in tag
        assert 'ring-offset-2' not in tag

    def test_pode_registrar_verdadeiro_para_chefe(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        assert response.context['pode_registrar'] is True

    def test_pode_registrar_falso_para_aux(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL)
        assert response.context['pode_registrar'] is False

    def test_pode_registrar_verdadeiro_para_superuser(self, client, superuser):
        # Superuser tem override técnico para registrar (matriz-permissoes.md linha 78)
        client.force_login(superuser)
        response = client.get(URL)
        assert response.context['pode_registrar'] is True

    def test_vazia_com_permissao_exibe_cta(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL)
        html = response.content.decode()
        assert 'border-dashed border-border-strong' in html
        assert 'Nenhuma saída excepcional registrada' in html
        assert 'Registre a primeira baixa administrativa direta de material.' in html
        assert reverse('estoque:nova_saida_excepcional') in html

    def test_vazia_sem_permissao_oculta_cta(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL)
        html = response.content.decode()
        assert 'Nenhuma saída excepcional registrada' in html
        assert 'Não há saídas excepcionais no sistema.' in html
        assert reverse('estoque:nova_saida_excepcional') not in html


URL_NOVA = reverse('estoque:nova_saida_excepcional')
URL_BUSCAR = reverse('estoque:buscar_materiais_saida_excepcional')


class TestNovaSaidaExcepcionalView:
    def test_chefe_acessa_formulario(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA)
        assert response.status_code == 200

    def test_get_formset_tem_uma_linha_inicial_vazia(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA)
        assert response.status_code == 200
        assert len(response.context['formset'].forms) == 1

    def test_container_itens_usa_factory_alpine_itensformset(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA)
        html = response.content.decode()
        assert 'id="itens-container"' in html
        # A factory passa a receber o prefixo do formset para ler o TOTAL_FORMS,
        # que é a fonte única do índice da próxima linha.
        assert 'x-data="itensFormset({ prefixo: \'itens\' })"' in html
        assert 'data-itens-container' in html

    def test_botao_remover_usa_click_alpine_sem_onclick_inline(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA)
        html = response.content.decode()
        assert '@click="removerLinha($event)"' in html
        assert 'onclick=' not in html

    def test_superuser_acessa_formulario(self, client, superuser, estoque_principal):
        client.force_login(superuser)
        response = client.get(URL_NOVA)
        assert response.status_code == 200

    def test_aux_recebe_403(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL_NOVA)
        assert response.status_code == 403

    def test_solicitante_recebe_403(self, client, solicitante):
        client.force_login(solicitante)
        response = client.get(URL_NOVA)
        assert response.status_code == 403

    def test_anonimo_redirecionado_para_login(self, client):
        response = client.get(URL_NOVA)
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_post_nao_htmx_valido_cria_saida_e_redireciona(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Caixas molhadas',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 302
        from apps.estoque.models import SaidaExcepcional

        assert SaidaExcepcional.objects.count() == 1
        saida = SaidaExcepcional.objects.get()
        assert saida.numero_publico.startswith('SXP-')

    def test_post_htmx_valido_cria_saida_e_retorna_hx_redirect(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Caixas molhadas',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 204
        assert response['HX-Redirect'] == reverse('estoque:listar_saidas_excepcionais')
        from apps.estoque.models import SaidaExcepcional

        assert SaidaExcepcional.objects.count() == 1

    def test_post_sem_motivo_retorna_form_com_erro(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': '',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 200
        assert 'motivo' in response.context['form'].errors

    def test_post_motivo_invalido_retorna_form_com_erro(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'nao_existe',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 200
        assert 'motivo' in response.context['form'].errors

    def test_post_sem_observacao_retorna_form_com_erro(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': '',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 200
        assert 'observacao' in response.context['form'].errors

    def test_post_sem_itens_retorna_formset_com_erro(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '0',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
            },
        )
        assert response.status_code == 200
        assert any(
            'ao menos um item' in e
            for e in response.context['formset'].non_form_errors()
        )

    def test_post_item_duplicado_retorna_erro_na_linha(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '2',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
                'itens-1-material_id': str(material_disponivel.pk),
                'itens-1-quantidade': '3',
            },
        )
        assert response.status_code == 200
        formset = response.context['formset']
        assert any('material_label' in f.errors for f in formset.forms)

    def test_post_quantidade_invalida_retorna_erro_na_linha(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '0',
            },
        )
        assert response.status_code == 200
        formset = response.context['formset']
        assert 'quantidade' in formset.forms[0].errors

    def test_post_material_inelegivel_retorna_erro_na_linha(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        from apps.estoque.models import Material, SaldoEstoque, UnidadeMedida

        material_inativo = Material.objects.create(
            codigo='MAT097', nome='Serrote', unidade=UnidadeMedida.UNIDADE, ativo=False
        )
        SaldoEstoque.objects.create(
            estoque=estoque_principal, material=material_inativo, saldo_fisico=10
        )
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_inativo.pk),
                'itens-0-quantidade': '1',
            },
        )
        assert response.status_code == 200
        formset = response.context['formset']
        assert 'material_label' in formset.forms[0].errors

    def test_post_aux_recebe_403_sem_persistencia(
        self, client, aux_almoxarifado, estoque_principal, material_disponivel
    ):
        from apps.estoque.models import SaidaExcepcional

        client.force_login(aux_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Teste',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 403
        assert SaidaExcepcional.objects.count() == 0

    def test_post_solicitante_recebe_403_sem_persistencia(
        self, client, solicitante, estoque_principal, material_disponivel
    ):
        from apps.estoque.models import SaidaExcepcional

        client.force_login(solicitante)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Teste',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 403
        assert SaidaExcepcional.objects.count() == 0

    def test_post_anonimo_redireciona_sem_persistencia(
        self, client, material_disponivel
    ):
        from apps.estoque.models import SaidaExcepcional

        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Teste',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-quantidade': '5',
            },
        )
        assert response.status_code == 302
        assert 'login' in response['Location']
        assert SaidaExcepcional.objects.count() == 0

    def test_dados_invalidos_do_service_gera_messages_error_e_rerender(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        """DadosInvalidos do service (ex: race pós-clean) vira messages.error e
        re-renderiza o form — sem redirect, mesma request (docs/CONVENTIONS.md)."""
        from unittest.mock import patch

        from apps.core.exceptions import DadosInvalidos

        client.force_login(chefe_almoxarifado)
        with patch(
            'apps.estoque.views.registrar_saida_excepcional',
            side_effect=DadosInvalidos('material inativo'),
        ):
            response = client.post(
                URL_NOVA,
                data={
                    'motivo': 'avaria',
                    'observacao': 'Teste',
                    'itens-TOTAL_FORMS': '1',
                    'itens-INITIAL_FORMS': '0',
                    'itens-MIN_NUM_FORMS': '0',
                    'itens-MAX_NUM_FORMS': '1000',
                    'itens-0-material_id': str(material_disponivel.pk),
                    'itens-0-quantidade': '5',
                },
            )

        assert response.status_code == 200
        mensagens = list(response.wsgi_request._messages)
        assert len(mensagens) == 1
        assert mensagens[0].level_tag == 'error'
        assert str(mensagens[0]) == 'material inativo'

    def test_conflito_dominio_do_service_gera_messages_warning_e_rerender(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        """ConflitoDominio do service (ex: saldo insuficiente na corrida entre
        clean() e select_for_update()) vira messages.warning e re-renderiza."""
        from unittest.mock import patch

        from apps.core.exceptions import ConflitoDominio

        client.force_login(chefe_almoxarifado)
        with patch(
            'apps.estoque.views.registrar_saida_excepcional',
            side_effect=ConflitoDominio('saldo físico insuficiente'),
        ):
            response = client.post(
                URL_NOVA,
                data={
                    'motivo': 'avaria',
                    'observacao': 'Teste',
                    'itens-TOTAL_FORMS': '1',
                    'itens-INITIAL_FORMS': '0',
                    'itens-MIN_NUM_FORMS': '0',
                    'itens-MAX_NUM_FORMS': '1000',
                    'itens-0-material_id': str(material_disponivel.pk),
                    'itens-0-quantidade': '5',
                },
            )

        assert response.status_code == 200
        mensagens = list(response.wsgi_request._messages)
        assert len(mensagens) == 1
        assert mensagens[0].level_tag == 'warning'
        assert str(mensagens[0]) == 'saldo físico insuficiente'


class TestBuscarMateriasSaidaExcepcionalView:
    def test_chefe_recebe_json(self, client, chefe_almoxarifado, material_disponivel):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_BUSCAR, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert response.status_code == 200
        data = response.json()
        assert 'resultados' in data

    def test_filtra_por_q(self, client, chefe_almoxarifado, material_disponivel):
        client.force_login(chefe_almoxarifado)
        response = client.get(
            URL_BUSCAR + '?q=Parafuso', HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        assert response.status_code == 200
        data = response.json()
        assert any('Parafuso' in r['nome'] for r in data['resultados'])

    def test_aux_recebe_403(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL_BUSCAR, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert response.status_code == 403

    def test_anonimo_redirecionado(self, client):
        response = client.get(URL_BUSCAR)
        assert response.status_code == 302

    def test_aux_permissao_negada_retorna_json_403_nao_redirect(
        self, client, aux_almoxarifado
    ):
        """Opt-out: PermissaoNegada em buscar_materiais_saida_excepcional deve retornar
        JsonResponse 403 (não redirect com messages)."""
        client.force_login(aux_almoxarifado)
        response = client.get(URL_BUSCAR)
        assert response.status_code == 403
        assert response['Content-Type'].startswith('application/json')
        assert 'error' in response.json()


class TestDetalheSaidaExcepcionalView:
    def _url(self, pk):
        return reverse('estoque:detalhe_saida_excepcional', args=[pk])

    def test_chefe_almox_acessa_detalhe(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 200

    def test_aux_almox_acessa_detalhe(self, client, aux_almoxarifado, saida_registrada):
        client.force_login(aux_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 200

    def test_superuser_acessa_detalhe(self, client, superuser, saida_registrada):
        client.force_login(superuser)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 200

    def test_solicitante_recebe_403(self, client, solicitante, saida_registrada):
        client.force_login(solicitante)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 403

    def test_anonimo_redirecionado_para_login(self, client, saida_registrada):
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_usuario_inativo_redirecionado_para_login(
        self, client, usuario_inativo, saida_registrada
    ):
        client.force_login(usuario_inativo)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_pk_inexistente_retorna_404(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(self._url(999999))
        assert response.status_code == 404

    def test_contexto_contem_saida_e_pode_estornar(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        assert 'saida' in response.context
        assert 'pode_estornar' in response.context
        assert response.context['pode_estornar'] is True

    def test_aux_nao_pode_estornar_no_contexto(
        self, client, aux_almoxarifado, saida_registrada
    ):
        client.force_login(aux_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        assert response.context['pode_estornar'] is False

    def test_post_retorna_405(self, client, chefe_almoxarifado, saida_registrada):
        client.force_login(chefe_almoxarifado)
        response = client.post(self._url(saida_registrada.pk), data={})
        assert response.status_code == 405

    def test_modal_estorno_usa_componente_com_textarea_obrigatorio(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """Modal de estorno migrado para components/modal.html (issue #78)."""
        client.force_login(chefe_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        html = response.content.decode('utf-8')
        assert 'data-modal-trigger="estornar-saida"' in html
        dialog_inicio = html.index('id="estornar-saida"')
        dialog_fim = html.index('</dialog>', dialog_inicio)
        dialog_html = html[dialog_inicio:dialog_fim]
        assert '<textarea' in dialog_html
        assert 'name="justificativa"' in dialog_html
        assert 'required' in dialog_html
        assert f'action="{self._estornar_url(saida_registrada.pk)}"' in dialog_html

    def _estornar_url(self, pk):
        return reverse('estoque:estornar_saida_excepcional', args=[pk])


class TestEstornarSaidaExcepcionalView:
    def _url(self, pk):
        return reverse('estoque:estornar_saida_excepcional', args=[pk])

    def test_chefe_estorna_e_redireciona_para_detalhe(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Registro equivocado.'},
        )
        assert response.status_code == 302
        assert str(saida_registrada.pk) in response['Location']

    def test_superuser_estorna_e_redireciona(self, client, superuser, saida_registrada):
        client.force_login(superuser)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Override técnico.'},
        )
        assert response.status_code == 302
        assert str(saida_registrada.pk) in response['Location']

    def test_aux_recebe_403(self, client, aux_almoxarifado, saida_registrada):
        client.force_login(aux_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Tentativa.'},
        )
        assert response.status_code == 403

    def test_solicitante_recebe_403(self, client, solicitante, saida_registrada):
        client.force_login(solicitante)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Tentativa.'},
        )
        assert response.status_code == 403

    def test_anonimo_redirecionado_para_login(self, client, saida_registrada):
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Tentativa.'},
        )
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_pk_inexistente_retorna_404(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.post(self._url(999999), data={'justificativa': 'x'})
        assert response.status_code == 404

    def test_get_retorna_405(self, client, chefe_almoxarifado, saida_registrada):
        client.force_login(chefe_almoxarifado)
        response = client.get(self._url(saida_registrada.pk))
        assert response.status_code == 405

    def test_justificativa_vazia_redireciona_com_mensagem_erro(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': ''},
        )
        assert response.status_code == 302
        assert str(saida_registrada.pk) in response['Location']
        messages_list = list(response.wsgi_request._messages)
        assert any(m.tags == 'error' for m in messages_list)

    def test_saida_ja_estornada_redireciona_com_mensagem_warning(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        from apps.estoque.services import estornar_saida_excepcional

        estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Primeiro.',
        )
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Segundo.'},
        )
        assert response.status_code == 302
        assert str(saida_registrada.pk) in response['Location']
        messages_list = list(response.wsgi_request._messages)
        assert any(m.tags == 'warning' for m in messages_list)
        assert not any(m.tags == 'error' for m in messages_list)

    def test_estorno_nao_duplica_mensagem_no_detalhe(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Registro equivocado.'},
        )
        assert response.status_code == 302
        assert str(saida_registrada.pk) in response['Location']

        detalhe_response = client.get(response['Location'])
        assert detalhe_response.status_code == 200
        conteudo = detalhe_response.content.decode()
        mensagem = f'Saída {saida_registrada.numero_publico} estornada com sucesso.'
        assert conteudo.count(mensagem) == 1

    def test_conflito_dominio_mostra_warning_nao_error(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """Drift 6 (canônico): ConflitoDominio em estornar_saida_excepcional deve
        gerar messages.warning, nunca messages.error."""
        from unittest.mock import patch

        from apps.core.exceptions import ConflitoDominio

        client.force_login(chefe_almoxarifado)
        with patch(
            'apps.estoque.services.estornar_saida_excepcional',
            side_effect=ConflitoDominio('Já estornada'),
        ):
            response = client.post(
                self._url(saida_registrada.pk),
                data={'justificativa': 'Motivo'},
            )

        messages_list = list(response.wsgi_request._messages)
        assert any(m.tags == 'warning' for m in messages_list)
        assert not any(m.tags == 'error' for m in messages_list)

    def test_sem_htmx_post_valido_grava_o_estorno(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """Fallback sem JS: redirecionar para o lugar certo não basta.

        Sem esta metade, o teste passaria numa view que redireciona para o
        detalhe sem ter gravado nada — a mesma pergunta sem resposta que a
        issue trata, só que pela porta do fallback (ADR-0010).
        """
        from apps.estoque.models import EstadoSaidaExcepcional

        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Registro equivocado.'},
        )
        assert response.status_code == 302
        saida_registrada.refresh_from_db()
        assert saida_registrada.estado == EstadoSaidaExcepcional.ESTORNADA
        assert saida_registrada.estornado_em is not None

    def test_sem_htmx_post_invalido_nao_grava_nada(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        from apps.estoque.models import EstadoSaidaExcepcional

        client.force_login(chefe_almoxarifado)
        client.post(self._url(saida_registrada.pk), data={'justificativa': ''})
        saida_registrada.refresh_from_db()
        assert saida_registrada.estado == EstadoSaidaExcepcional.REGISTRADA
        assert saida_registrada.estornado_em is None

    def test_htmx_sucesso_devolve_204_com_hx_redirect(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """Sucesso via HTMX é PRG por cabeçalho, não 302 seguido pelo XHR.

        O modal faz `hx-post` com `hx-target="[data-modal-body]"` e
        `hx-swap="outerHTML"`: um 302 é seguido pelo próprio XHR, que recebe a
        página de detalhe inteira e a injeta dentro da caixa do modal.
        """
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Registro equivocado.'},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 204
        assert response['HX-Redirect'] == reverse(
            'estoque:detalhe_saida_excepcional', args=[saida_registrada.pk]
        )

    def test_htmx_erro_de_dominio_devolve_422_com_corpo_do_modal(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """Erro de domínio via HTMX mantém o modal de pé, sem página inteira."""
        client.force_login(chefe_almoxarifado)
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': ''},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 422
        conteudo = response.content.decode()
        assert 'data-modal-body="estornar-saida"' in conteudo
        assert 'data-modal-erro' in conteudo
        # Não pode ter vindo página inteira dentro da caixa do modal.
        assert '<html' not in conteudo
        assert 'app-bar' not in conteudo

    def test_htmx_erro_preserva_justificativa_digitada(
        self, client, chefe_almoxarifado, saida_registrada
    ):
        """O 422 devolve a caixa aberta com o texto digitado, não em branco.

        É o que `recusar_requisicao_view` já faz com `motivo_recusa`. Sem isso a
        pessoa reescreve a justificativa a cada erro.
        """
        client.force_login(chefe_almoxarifado)
        from apps.estoque.services import estornar_saida_excepcional

        estornar_saida_excepcional(
            ator_id=chefe_almoxarifado.pk,
            saida_id=saida_registrada.pk,
            justificativa='Primeiro.',
        )
        response = client.post(
            self._url(saida_registrada.pk),
            data={'justificativa': 'Texto que não pode sumir.'},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 422
        assert 'Texto que não pode sumir.' in response.content.decode()


class TestPreviewImportacaoScpiView:
    """Contrato HTTP de preview_importacao_scpi_view."""

    URL = '/estoque/importacao-scpi/pre-visualizacao/'

    def _csv_valido(
        self, codigo: str = '000.000.001', quantidade: str = '10.000'
    ) -> bytes:
        return f'CADPRO;DENOMINACAO;QUAN3\n{codigo};Teste;{quantidade}\n'.encode(
            'utf-8'
        )

    def test_nao_autenticado_redireciona_para_login(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 302
        assert '/login/' in resp['Location']

    def test_sem_permissao_retorna_403(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        resp = client.get(self.URL)
        assert resp.status_code == 403

    def test_superuser_get_retorna_200(self, client, superuser):
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_post_csv_valido_retorna_200_com_preview(
        self, client, superuser, estoque_principal, material_scpi
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_bytes = self._csv_valido(material_scpi.codigo, '100.000')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        resp = client.post(self.URL, {'arquivo': arquivo})
        assert resp.status_code == 200
        assert (
            b'CADPRO' in resp.content or material_scpi.codigo.encode() in resp.content
        )

    def _preview_com_novos_e_divergencias(self, client, superuser, material_scpi):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_bytes = (
            f'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi.codigo};Teste;150.000\n'
            f'000.000.999;Material Novo;5.000\n'
        ).encode('utf-8')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        return client.post(self.URL, {'arquivo': arquivo}).content.decode()

    def _preview_de_arquivo_so_com_cabecalho(self, client, superuser):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        arquivo = SimpleUploadedFile(
            'vazio.csv', b'CADPRO;DENOMINACAO;QUAN3\n', content_type='text/csv'
        )
        return client.post(self.URL, {'arquivo': arquivo}).content.decode()

    def test_arquivo_so_com_cabecalho_nao_volta_em_silencio(
        self, client, superuser, estoque_principal
    ):
        """Enviar um CSV sem linhas de dados não pode parecer não ter feito nada.

        O template tinha um estado vazio para este caso, mas ele era inalcançável:
        o ramo de preview só é atingido com `linhas` truthy, então o `{% else %}`
        de dentro dele nunca renderizava. Na prática o POST caía de volta no
        formulário de upload, idêntico ao que a pessoa já estava vendo — sem
        alerta, sem foco, sem pista de que o arquivo foi lido e estava vazio.

        Num ritual recorrente feito por quem confia mais no papel que no
        software, uma tela que não reage é indistinguível de uma tela travada.
        """
        conteudo = self._preview_de_arquivo_so_com_cabecalho(client, superuser)

        assert 'linhas de dados' in conteudo
        assert 'Carregar arquivo CSV do SCPI' not in conteudo, (
            'voltou ao formulário de upload como se nada tivesse acontecido'
        )

    def test_arquivo_so_com_cabecalho_amarra_o_erro_ao_campo_de_retry(
        self, client, superuser, estoque_principal
    ):
        """Depois de um POST full-page o que anuncia é o foco, não live region.

        O caminho de erro do arquivo já tem o mecanismo montado — `autofocus`,
        `aria-invalid` e `aria-describedby` amarrando o texto ao campo. Reusá-lo
        é mais barato e mais acessível que inventar um quarto estado de tela.
        """
        conteudo = self._preview_de_arquivo_so_com_cabecalho(client, superuser)

        assert 'id="erro-arquivo-alerta"' in conteudo
        assert 'aria-describedby="erro-arquivo-alerta"' in conteudo
        assert 'autofocus' in conteudo

    def test_preview_nao_carrega_estado_vazio_inalcancavel(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """A caixa clonada à mão sai do arquivo, não vira include.

        Ela replicava as classes do `empty_state.html` sem usá-lo e carregava
        `text-text-disabled` (slate-400, 2.63:1 sobre branco, abaixo dos 4.5:1
        da WCAG 1.4.3). Trocá-la pelo componente manteria marcação que nunca
        renderiza; o certo é apagar e tratar o caso vazio onde ele de fato
        acontece.
        """
        conteudo = self._preview_com_novos_e_divergencias(
            client, superuser, material_scpi
        )

        assert 'border-dashed border-border-strong' not in conteudo

    def test_alerta_de_divergencia_mantem_variante_warning_e_role_status(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """O token âmbar e o anúncio não-assertivo são decisão de produto.

        Divergência é estado esperado da coexistência com o SCPI e a decisão é
        do chefe de almoxarifado — âmbar é exatamente "a decisão está com
        alguém". E no preview ela pede leitura, não interrupção: por isso o
        `role="status"` explícito, que sobrescreve o `alert` automático da
        variante. Sem este teste, nada impede uma passagem futura de "corrigir"
        qualquer um dos dois.
        """
        conteudo = self._preview_com_novos_e_divergencias(
            client, superuser, material_scpi
        )

        assert (
            'border-primary-border bg-primary-subtle text-primary-text-emphasis'
            in conteudo
        )
        assert 'border-warning-border bg-warning-subtle text-warning-text' in conteudo
        assert 'role="status"' in conteudo

    def test_preview_nao_declara_live_region_inerte(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """Live region só dispara com mudança.

        Os três `aria_live` passados a `alert.html` descreviam um anúncio que
        nunca aconteceu: o conteúdo já está presente no carregamento da
        resposta do POST. Sobra um só `aria-live`, o da barra de resumo, que
        não passa por `alert.html` e agora é o alvo do foco programático.
        """
        conteudo = self._preview_com_novos_e_divergencias(
            client, superuser, material_scpi
        )

        assert conteudo.count('aria-live=') == 1

    def test_resumo_do_preview_recebe_foco_no_retorno_do_upload(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """Depois de um POST full-page, o que anuncia é o foco, não a live region.

        Mesmo padrão GOV.UK de `components/error_summary.html`: `tabindex="-1"`
        mais foco no mount. O anel usa `focus:` e não `focus-visible:`, porque
        `focus-visible` não casa em foco programático que não veio do teclado.
        """
        conteudo = self._preview_com_novos_e_divergencias(
            client, superuser, material_scpi
        )

        assert 'tabindex="-1"' in conteudo
        assert 'x-init="$el.focus()"' in conteudo
        assert 'focus:ring-2' in conteudo

    def test_erro_de_arquivo_amarra_a_mensagem_ao_campo_de_retry(
        self, client, superuser
    ):
        """O `aria_live="assertive"` daqui também nunca anunciou nada.

        O mecanismo que funciona já estava meio pronto: o campo de retry tem
        `autofocus` e `aria-invalid`. Falta o texto do erro chegar junto — é o
        que o checklist do design system cobra, `aria-invalid` mais
        `aria-describedby`.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        arquivo = SimpleUploadedFile(
            'ruim.csv', b'COLUNA_ERRADA;OUTRA\nX;Y\n', content_type='text/csv'
        )
        conteudo = client.post(self.URL, {'arquivo': arquivo}).content.decode()

        assert 'id="erro-arquivo-alerta"' in conteudo
        assert 'aria-describedby="erro-arquivo-alerta"' in conteudo
        assert 'aria-live=' not in conteudo

    def test_botao_de_confirmar_e_descrito_pelos_alertas_da_importacao(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """Os alertas não estão na ordem de tabulação.

        Quem navega por teclado vai da barra de resumo direto ao botão de
        confirmar e nunca passa pelos dois alertas — ouviria as contagens e
        gravaria sem saber que a decisão é do chefe de almoxarifado. O
        `aria-describedby` põe a copy inteira no anúncio do próprio botão, no
        momento exato da decisão de gravar.

        O `id` fica no bloco que embrulha os alertas, não em cada um: o bloco
        existe sempre, os alertas são condicionais, e assim o
        `aria-describedby` nunca aponta para um `id` inexistente.
        """
        conteudo = self._preview_com_novos_e_divergencias(
            client, superuser, material_scpi
        )

        assert 'id="alertas-importacao"' in conteudo
        assert 'aria-describedby="alertas-importacao"' in conteudo

    def test_post_csv_com_dois_novos_flexiona_plural_corretamente(
        self, client, superuser, estoque_principal
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_bytes = (
            'CADPRO;DENOMINACAO;QUAN3\n'
            '000.000.997;Material Novo 1;5.000\n'
            '000.000.998;Material Novo 2;5.000\n'
        ).encode('utf-8')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        resp = client.post(self.URL, {'arquivo': arquivo})
        conteudo = resp.content.decode()

        assert 'serão criados' in conteudo
        assert 'seráão' not in conteudo

    def test_confirmar_importacao_passa_por_modal_e_nao_por_submit_nu(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """A gravação é irreversível e precisa de porta.

        Era a única escrita irreversível do sistema sem confirmação: um submit
        direto, com o botão depois de centenas de cartões. O PRODUCT.md declara
        que este fluxo exige "confirmação explícita antes de gravar", para gente
        que confia mais no papel do que no software.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_bytes = self._csv_valido(material_scpi.codigo, '150.000')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        conteudo = client.post(self.URL, {'arquivo': arquivo}).content.decode()

        assert 'data-modal-trigger="confirmar-importacao-scpi"' in conteudo
        assert '<dialog' in conteudo
        assert 'id="confirmar-importacao-scpi"' in conteudo
        assert 'Confirmar importação do SCPI?' in conteudo

    def test_modal_de_confirmacao_recapitula_os_numeros_a_gravar(
        self, client, superuser, estoque_principal, material_scpi
    ):
        """No momento de confirmar, a lista já saiu da tela.

        A recapitulação repete os números em vez de mandar rolar de volta —
        inclusive os zeros, porque "nenhum material novo" é informação para quem
        confere contra o papel.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_bytes = (
            f'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi.codigo};Teste;150.000\n'
            f'000.000.999;Material Novo;5.000\n'
        ).encode('utf-8')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        conteudo = client.post(self.URL, {'arquivo': arquivo}).content.decode()

        assert 'Materiais novos a criar' in conteudo
        assert 'Divergências a registrar' in conteudo
        assert 'Linhas lidas do arquivo' in conteudo
        assert 'Nenhum saldo do WMS é sobrescrito' in conteudo
        assert 'teste.csv' in conteudo

    def test_preview_ordena_divergencia_e_novo_antes_de_ok(
        self, client, superuser, estoque_principal, material_scpi, material_scpi_critico
    ):
        """A tela existe para evidenciar delta.

        Na ordem do arquivo, conferir as divergências num CSV de centenas de
        linhas é caçar. O CSV entra na ordem inversa da desejada — "ok"
        primeiro, "divergente" por último — para que a asserção só passe se a
        ordenação de fato aconteceu.

        Os três status precisam existir de verdade: com só `novo` e `ok` o teste
        passa sem nunca exercitar a prioridade de `divergente`, que é a razão de
        a ordenação existir.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        # material_scpi tem saldo físico 100; material_scpi_critico tem 2.
        csv_bytes = (
            f'CADPRO;DENOMINACAO;QUAN3\n'
            f'{material_scpi_critico.codigo};Saldo igual;2.000\n'
            f'000.000.999;Material Novo;5.000\n'
            f'{material_scpi.codigo};Saldo diferente;250.000\n'
        ).encode('utf-8')
        arquivo = SimpleUploadedFile('teste.csv', csv_bytes, content_type='text/csv')
        resp = client.post(self.URL, {'arquivo': arquivo})

        status_renderizados = [linha.status for linha in resp.context['linhas']]
        assert status_renderizados == ['divergente', 'novo', 'ok']

    def test_post_sem_arquivo_retorna_200_com_erro(self, client, superuser):
        client.force_login(superuser)
        resp = client.post(self.URL, {})
        assert resp.status_code == 200
        assert b'arquivo' in resp.content.lower() or b'obrigat' in resp.content.lower()

    def test_post_csv_invalido_retorna_200_com_mensagem_erro(
        self, client, superuser, estoque_principal
    ):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        csv_ruim = b'COLUNA_ERRADA;OUTRA\nX;Y\n'
        arquivo = SimpleUploadedFile('ruim.csv', csv_ruim, content_type='text/csv')
        resp = client.post(self.URL, {'arquivo': arquivo})
        assert resp.status_code == 200
        assert b'CADPRO' in resp.content or b'inv' in resp.content.lower()


class TestConfirmarImportacaoScpiView:
    """Contrato HTTP de confirmar_importacao_scpi_view (POST) + sucesso_importacao_scpi_view (GET)."""

    URL_PREVIEW = '/estoque/importacao-scpi/pre-visualizacao/'
    URL = '/requisicoes/importacao-scpi/confirmar/'

    def _csv(self, cadpro: str = '000.888.001', quantidade: str = '10.000') -> bytes:
        return f'CADPRO;DENOMINACAO;QUAN3\n{cadpro};Teste;{quantidade}\n'.encode(
            'utf-8'
        )

    def _seed_session(self, client, superuser, csv_bytes: bytes) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        client.force_login(superuser)
        arquivo = SimpleUploadedFile('seed.csv', csv_bytes, content_type='text/csv')
        client.post(self.URL_PREVIEW, {'arquivo': arquivo})

    def test_nao_autenticado_redireciona_para_login(self, client):
        resp = client.post(self.URL, {})
        assert resp.status_code == 302
        assert '/login/' in resp['Location']

    def test_sem_permissao_retorna_403(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        resp = client.post(self.URL, {})
        assert resp.status_code == 403

    def test_sem_session_retorna_200_com_erro(self, client, superuser):
        client.force_login(superuser)
        resp = client.post(self.URL, {})
        assert resp.status_code == 200
        assert (
            b'pr\xc3\xa9' in resp.content.lower()
            or b'upload' in resp.content.lower()
            or b'visualiza' in resp.content.lower()
            or b'novamente' in resp.content.lower()
        )

    def test_post_com_session_valida_redireciona_para_sucesso(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.010')
        self._seed_session(client, superuser, csv_bytes)
        resp = client.post(self.URL, {})
        assert resp.status_code == 302
        assert '/confirmada/' in resp['Location']

    def test_get_sucesso_retorna_200_com_metadados(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.011')
        self._seed_session(client, superuser, csv_bytes)
        redirect = client.post(self.URL, {})
        assert redirect.status_code == 302
        resp = client.get(redirect['Location'])
        assert resp.status_code == 200
        assert (
            b'sucesso' in resp.content.lower() or b'confirmad' in resp.content.lower()
        )

    def test_hash_duplicado_retorna_200_com_mensagem_erro(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.020')
        self._seed_session(client, superuser, csv_bytes)
        client.post(self.URL, {})

        self._seed_session(client, superuser, csv_bytes)
        resp = client.post(self.URL, {})
        assert resp.status_code == 200
        assert (
            b'duplicad' in resp.content.lower()
            or b'reimporta' in resp.content.lower()
            or b'j\xc3\xa1' in resp.content.lower()
        )

    def test_sem_htmx_post_valido_grava_a_importacao(
        self, client, superuser, estoque_principal
    ):
        from apps.estoque.models import ImportacaoSCPI

        self._seed_session(client, superuser, self._csv('000.888.070'))
        antes = ImportacaoSCPI.objects.count()
        resp = client.post(self.URL, {})
        assert resp.status_code == 302
        assert ImportacaoSCPI.objects.count() == antes + 1

    def test_sem_htmx_sem_preview_nao_grava_nada(self, client, superuser):
        from apps.estoque.models import ImportacaoSCPI

        client.force_login(superuser)
        antes = ImportacaoSCPI.objects.count()
        resp = client.post(self.URL, {})
        assert resp.status_code == 200
        assert ImportacaoSCPI.objects.count() == antes

    def test_htmx_sucesso_devolve_204_com_hx_redirect(
        self, client, superuser, estoque_principal
    ):
        """A única escrita irreversível declarada do sistema não pode terminar
        com a página de sucesso injetada dentro da caixa do modal."""
        from django.urls import reverse

        from apps.estoque.models import ImportacaoSCPI

        self._seed_session(client, superuser, self._csv('000.888.040'))
        resp = client.post(self.URL, {}, HTTP_HX_REQUEST='true')
        assert resp.status_code == 204
        importacao = ImportacaoSCPI.objects.latest('pk')
        assert resp['HX-Redirect'] == reverse(
            'estoque:sucesso_importacao_scpi', kwargs={'pk': importacao.pk}
        )

    def test_htmx_sem_preview_na_sessao_devolve_422(self, client, superuser):
        """Segunda tentativa é o pior caso: a sessão do preview já foi limpa e a
        pessoa fica com duas evidências contraditórias, ambas dentro da caixa."""
        client.force_login(superuser)
        resp = client.post(self.URL, {}, HTTP_HX_REQUEST='true')
        assert resp.status_code == 422
        conteudo = resp.content.decode()
        assert 'data-modal-body="confirmar-importacao-scpi"' in conteudo
        assert 'data-modal-erro' in conteudo
        assert '<html' not in conteudo

    def test_htmx_hash_duplicado_devolve_422(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.050')
        self._seed_session(client, superuser, csv_bytes)
        client.post(self.URL, {})

        self._seed_session(client, superuser, csv_bytes)
        resp = client.post(self.URL, {}, HTTP_HX_REQUEST='true')
        assert resp.status_code == 422
        conteudo = resp.content.decode()
        assert 'data-modal-body="confirmar-importacao-scpi"' in conteudo
        assert '<html' not in conteudo

    def test_htmx_sem_estoque_ativo_devolve_422(self, client, superuser):
        from apps.estoque.models import Estoque

        self._seed_session(client, superuser, self._csv('000.888.060'))
        Estoque.objects.update(ativo=False)
        resp = client.post(self.URL, {}, HTTP_HX_REQUEST='true')
        assert resp.status_code == 422
        assert 'data-modal-body="confirmar-importacao-scpi"' in resp.content.decode()

    def test_get_sucesso_usa_components_alert_com_aria(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.030')
        self._seed_session(client, superuser, csv_bytes)
        redirect = client.post(self.URL, {})
        resp = client.get(redirect['Location'])
        conteudo = resp.content.decode()

        assert 'border-success-border' in conteudo
        assert 'bg-success-subtle' in conteudo
        assert 'role="status"' in conteudo
        # `role="status"` já implica aria-live polido; declarar os dois fazia o
        # leitor de tela anunciar duas vezes. `aria_live` saiu do alert na #127.
        assert 'aria-live=' not in conteudo

    def test_hash_duplicado_usa_components_alert_com_aria(
        self, client, superuser, estoque_principal
    ):
        csv_bytes = self._csv('000.888.031')
        self._seed_session(client, superuser, csv_bytes)
        client.post(self.URL, {})

        self._seed_session(client, superuser, csv_bytes)
        resp = client.post(self.URL, {})
        conteudo = resp.content.decode()

        assert 'border-danger-border' in conteudo
        assert 'bg-danger-subtle' in conteudo
        assert 'role="alert"' in conteudo
        # `role="alert"` já é assertivo — a combinação era redundante (#127).
        assert 'aria-live=' not in conteudo

    def test_get_nao_permitido_retorna_405(self, client, superuser):
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert resp.status_code == 405


class TestHistoricoImportacoesScpiView:
    """Contrato HTTP de historico_importacoes_scpi_view."""

    URL = '/estoque/importacao-scpi/historico/'

    def test_nao_autenticado_redireciona_para_login(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 302
        assert '/login/' in resp['Location']

    def test_sem_permissao_retorna_403(self, client, solicitante):
        client.force_login(solicitante)
        resp = client.get(self.URL)
        assert resp.status_code == 403

    def test_superuser_get_retorna_200(self, client, superuser):
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_chefe_almoxarifado_get_retorna_200(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_post_retorna_405(self, client, superuser):
        client.force_login(superuser)
        resp = client.post(self.URL, {})
        assert resp.status_code == 405

    def test_lista_vazia_retorna_200(self, client, superuser):
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_exibe_metadados_da_importacao(self, client, superuser, estoque_principal):
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        ImportacaoSCPI.objects.create(
            arquivo_nome='relatorio.csv',
            arquivo_hash='e' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
            total_linhas=10,
            total_novos=2,
            total_divergentes=3,
        )
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert resp.status_code == 200
        assert b'relatorio.csv' in resp.content

    def test_nao_expoe_csv_bruto(self, client, superuser, estoque_principal):
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        ImportacaoSCPI.objects.create(
            arquivo_nome='bruto.csv',
            arquivo_hash='f' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        client.force_login(superuser)
        resp = client.get(self.URL)
        assert b'conteudo_csv' not in resp.content

    def test_renderiza_cartoes_com_metadados(
        self, client, superuser, estoque_principal
    ):
        """Esta tela não tinha renderização em cartões e ganhou uma quando as
        tabelas saíram do sistema — sem ela, ficaria sem listagem nenhuma.
        """
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        ImportacaoSCPI.objects.create(
            arquivo_nome='relatorio.csv',
            arquivo_hash='a' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        client.force_login(superuser)
        conteudo = client.get(self.URL).content.decode()
        assert (
            '<article class="rounded-xl border border-border bg-surface p-4 shadow-sm">'
            in conteudo
        )
        assert 'relatorio.csv' in conteudo
        assert 'Concluída' in conteudo
        assert '<table' not in conteudo

    def test_listagem_nao_usa_contentor_de_scroll_horizontal(
        self, client, superuser, estoque_principal
    ):
        """Antes a tabela ficava num wrapper `overflow-x-auto` que rolava em
        qualquer janela de desktop não maximizada. O cartão dispensa o wrapper.
        """
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        ImportacaoSCPI.objects.create(
            arquivo_nome='relatorio.csv',
            arquivo_hash='b' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        client.force_login(superuser)
        conteudo = client.get(self.URL).content.decode()
        assert 'overflow-x-auto' not in conteudo

    def test_exibe_link_de_download_quando_ha_arquivo(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        from django.core.files.base import ContentFile

        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        settings.MEDIA_ROOT = str(tmp_path)
        importacao = ImportacaoSCPI.objects.create(
            arquivo_nome='com_arquivo.csv',
            arquivo=ContentFile(b'CADPRO;DENOMINACAO;QUAN3\n', name='com_arquivo.csv'),
            arquivo_hash='b' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        client.force_login(superuser)
        resp = client.get(self.URL)
        url_download = f'/estoque/importacao-scpi/{importacao.pk}/arquivo/'
        assert url_download.encode() in resp.content
        # Nome acessível distingue as linhas: "Baixar" sozinho se repete na coluna.
        assert b'aria-label="Baixar CSV de com_arquivo.csv"' in resp.content

    def test_nao_exibe_link_quando_importacao_legada(
        self, client, superuser, estoque_principal
    ):
        """Importação anterior ao arquivamento não ganha link morto."""
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        importacao = ImportacaoSCPI.objects.create(
            arquivo_nome='legada.csv',
            arquivo_hash='c' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        client.force_login(superuser)
        resp = client.get(self.URL)
        url_download = f'/estoque/importacao-scpi/{importacao.pk}/arquivo/'
        assert url_download.encode() not in resp.content

    def test_status_nao_mapeado_grita_em_vez_de_cinza_plausivel(
        self, client, superuser, estoque_principal
    ):
        """Decisão A-1 da issue #122: status fora do enum passava pelo
        `{% else %}` antigo e virava um badge cinza plausível. O
        `{% else %}` novo repassa o valor sob o prefixo `desconhecida:` e
        deixa o fallback vermelho do badge.html gritar.
        """
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        importacao = ImportacaoSCPI.objects.create(
            arquivo_nome='status-invalido.csv',
            arquivo_hash='d' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        ImportacaoSCPI.objects.filter(pk=importacao.pk).update(status='invalido')
        client.force_login(superuser)
        conteudo = client.get(self.URL).content.decode()
        assert 'Indisponível' in conteudo
        assert 'data-badge-variant="desconhecida:invalido"' in conteudo

    def test_status_orange_colide_mas_gruda_no_fallback(
        self, client, superuser, estoque_principal
    ):
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        importacao = ImportacaoSCPI.objects.create(
            arquivo_nome='status-orange.csv',
            arquivo_hash='9' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )
        ImportacaoSCPI.objects.filter(pk=importacao.pk).update(status='orange')
        client.force_login(superuser)
        conteudo = client.get(self.URL).content.decode()
        assert 'Indisponível' in conteudo
        assert 'bg-orange-100' not in conteudo

    def test_status_conhecido_mantem_variante_de_hoje(
        self, client, superuser, estoque_principal
    ):
        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        ImportacaoSCPI.objects.create(
            arquivo_nome='com-alertas.csv',
            arquivo_hash='8' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.COM_ALERTAS,
        )
        client.force_login(superuser)
        conteudo = client.get(self.URL).content.decode()
        assert 'bg-yellow-100' in conteudo
        assert 'Com alertas' in conteudo


class TestBaixarArquivoImportacaoScpiView:
    """Contrato HTTP de baixar_arquivo_importacao_scpi_view."""

    CSV = b'CADPRO;DENOMINACAO;QUAN3\n000.111.222;Parafuso M6;010.000\n'

    def _url(self, pk: int) -> str:
        return f'/estoque/importacao-scpi/{pk}/arquivo/'

    def _importacao(
        self,
        superuser,
        estoque_principal,
        *,
        arquivo_nome='relatorio.csv',
        com_arquivo=True,
    ):
        from django.core.files.base import ContentFile

        from apps.estoque.models import ImportacaoSCPI, StatusImportacaoSCPI

        return ImportacaoSCPI.objects.create(
            arquivo_nome=arquivo_nome,
            arquivo=ContentFile(self.CSV, name='arquivado.csv') if com_arquivo else '',
            arquivo_hash='1' * 64,
            importado_por=superuser,
            estoque=estoque_principal,
            status=StatusImportacaoSCPI.CONCLUIDA,
        )

    def _corpo(self, resp) -> bytes:
        return b''.join(resp.streaming_content)

    def test_nao_autenticado_get_redireciona_para_login(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 302
        assert '/login/' in resp['Location']

    def test_nao_autenticado_post_redireciona_para_login(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        """`login_required` por fora de `require_http_methods`: anônimo vê login, não 405."""
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        resp = client.post(self._url(importacao.pk), {})
        assert resp.status_code == 302
        assert '/login/' in resp['Location']

    def test_post_autenticado_retorna_405(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        client.force_login(superuser)
        resp = client.post(self._url(importacao.pk), {})
        assert resp.status_code == 405

    def test_solicitante_retorna_403(
        self, client, settings, tmp_path, solicitante, superuser, estoque_principal
    ):
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        client.force_login(solicitante)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 403

    def test_chefe_almoxarifado_baixa_o_csv(
        self,
        client,
        settings,
        tmp_path,
        chefe_almoxarifado,
        superuser,
        estoque_principal,
    ):
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        client.force_login(chefe_almoxarifado)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 200
        assert resp['Content-Disposition'] == 'attachment; filename="relatorio.csv"'
        assert self._corpo(resp) == self.CSV

    def test_content_disposition_usa_basename_do_nome_original(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        """Nome com componentes de caminho não vaza para o header."""
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(
            superuser, estoque_principal, arquivo_nome='subdir/relatorio.csv'
        )
        client.force_login(superuser)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 200
        assert resp['Content-Disposition'] == 'attachment; filename="relatorio.csv"'

    def test_pk_inexistente_retorna_404(self, client, superuser):
        client.force_login(superuser)
        resp = client.get(self._url(999999))
        assert resp.status_code == 404

    def test_importacao_sem_arquivo_retorna_404(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal, com_arquivo=False)
        client.force_login(superuser)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 404

    def test_arquivo_removido_do_storage_retorna_404(
        self, client, settings, tmp_path, superuser, estoque_principal
    ):
        """Sem abrir o arquivo antes do FileResponse, isto estouraria 500 no meio do stream."""
        from pathlib import Path

        settings.MEDIA_ROOT = str(tmp_path)
        importacao = self._importacao(superuser, estoque_principal)
        Path(importacao.arquivo.path).unlink()
        client.force_login(superuser)
        resp = client.get(self._url(importacao.pk))
        assert resp.status_code == 404


URL_MATERIAIS = reverse('estoque:lista_materiais')


class TestListaMateriaisView:
    def test_chefe_almox_acessa_lista(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 200

    def test_aux_almox_acessa_lista(self, client, aux_almoxarifado):
        client.force_login(aux_almoxarifado)
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 200

    def test_superuser_acessa_lista(self, client, superuser):
        client.force_login(superuser)
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 200

    def test_solicitante_acessa_lista(self, client, solicitante):
        # Consultar materiais é permitido para todos os papéis ativos (matriz-permissoes.md).
        client.force_login(solicitante)
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 200

    def test_usuario_inativo_redirecionado_para_login(self, client, usuario_inativo):
        # Django ModelBackend trata is_active=False como não-autenticado;
        # @login_required redireciona para login (USR-01).
        client.force_login(usuario_inativo)
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_anonimo_redirecionado_para_login(self, client):
        response = client.get(URL_MATERIAIS)
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_contexto_contem_saldos(
        self, client, chefe_almoxarifado, material_disponivel, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        assert 'saldos' in response.context

    def test_contexto_contem_busca_vazia_por_padrao(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        assert response.context['busca'] == ''

    def test_nenhum_material_cadastrado_exibe_empty_state_dashed(
        self, client, chefe_almoxarifado
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        html = response.content.decode()
        assert 'border-dashed border-border-strong' in html
        assert 'border-slate-200 bg-white p-8' not in html
        assert 'Nenhum material no cat' in html

    def test_catalogo_vazio_diz_por_onde_o_material_entra(
        self, client, chefe_almoxarifado
    ):
        """Estado vazio de primeiro uso sem próxima ação é beco sem saída.

        Não existe cadastro manual de material: o catálogo é alimentado pela
        importação do SCPI. Dizer só "nenhum material" deixa quem abriu a tela
        sem saber se falta dado, falta permissão ou falta um passo — e o passo
        existe. A frase nomeia a rota sem virar link, porque importar é
        privilégio do chefe de almoxarifado e o componente não decide permissão.
        """
        client.force_login(chefe_almoxarifado)
        html = client.get(URL_MATERIAIS).content.decode()
        # A navegação lateral também cita a importação SCPI: recortar a caixa do
        # estado vazio é o que separa "a tela diz" de "a tela tem um link no menu".
        inicio = html.index('border-dashed border-border-strong')
        caixa = html[inicio : html.index('</div>', inicio)]
        assert 'importa' in caixa and 'SCPI' in caixa

    def test_busca_sem_resultado_diz_o_que_tentar_alem_do_cta(
        self, client, chefe_almoxarifado
    ):
        """O CTA leva de volta; a descrição diz como acertar da próxima vez."""
        client.force_login(chefe_almoxarifado)
        html = client.get(URL_MATERIAIS, {'busca': 'inexistente-xyz'}).content.decode()
        assert 'Confira o c' in html

    def test_busca_sem_resultado_exibe_cta_secundario_link(
        self, client, chefe_almoxarifado
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS, {'busca': 'inexistente-xyz'})
        html = response.content.decode()
        assert 'border-dashed border-border-strong' in html
        titulo_idx = html.index('Nenhum material encontrado para')
        match = re.search(r'<a\b[^>]*>', html[titulo_idx:])
        assert match is not None
        tag = match.group()
        assert re.search(r'href="[^"]*"', tag)
        assert 'underline' in tag
        assert 'bg-blue-600' not in tag

    def test_busca_filtra_por_codigo(
        self,
        client,
        chefe_almoxarifado,
        material_disponivel,
        material_scpi_critico,
        estoque_principal,
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS, {'busca': 'MAT001'})
        assert response.status_code == 200
        saldos = list(response.context['saldos'])
        assert len(saldos) == 1
        assert saldos[0].material.codigo == 'MAT001'

    def test_flag_divergente_visivel_no_contexto(
        self, client, chefe_almoxarifado, material_scpi_critico, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        saldos = list(response.context['saldos'])
        critico = next(s for s in saldos if s.material == material_scpi_critico)
        assert critico.divergente_calculado is True

    def test_renderiza_cartoes(
        self, client, chefe_almoxarifado, material_disponivel, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        conteudo = client.get(URL_MATERIAIS).content.decode()
        # <article> literal aqui: o estilo do cartão depende do estado de
        # divergência, então esta tela não usa o #card_abertura do chrome.
        assert '<article' in conteudo
        assert 'grid items-start gap-3 sm:grid-cols-2' in conteudo
        assert '<table' not in conteudo

    def test_material_divergente_realca_linha_e_card(
        self, client, chefe_almoxarifado, material_scpi_critico, estoque_principal
    ):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MATERIAIS)
        conteudo = response.content.decode()
        # Sem tabela, o realce de divergência vive só no cartão.
        assert 'border-danger-border-strong bg-danger-subtle' in conteudo
        assert 'aria-label="Material com divergência crítica"' in conteudo
        assert conteudo.count('Divergente') == 1


URL_MOVIMENTACOES = reverse('estoque:historico_movimentacoes')


class TestHistoricoMovimentacoesView:
    def test_chefe_almox_acessa(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 200

    def test_superuser_acessa(self, client, superuser):
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 200

    def test_solicitante_recebe_403(self, client, solicitante):
        client.force_login(solicitante)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 403

    def test_anonimo_redirecionado_para_login(self, client):
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 302
        assert 'login' in response['Location']

    def test_contexto_tem_page_obj(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert 'page_obj' in response.context

    def test_view_alimenta_page_obj_com_selector_escopado(
        self,
        client,
        chefe_obras,
        requisicao_autorizada,
        saida_registrada,
        movimentacao_outro_setor,
    ):
        # Contrato HTTP/render: a view delega o escopo ao selector e pagina o
        # resultado. A matriz de visibilidade em si é coberta em test_selectors.
        from apps.estoque.selectors import movimentacoes_visiveis_para

        client.force_login(chefe_obras)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 200
        assert 'estoque/historico_movimentacoes.html' in {
            t.name for t in response.templates
        }
        esperado = movimentacoes_visiveis_para(chefe_obras.pk).count()
        assert response.context['page_obj'].paginator.count == esperado

    def test_aux_setor_acessa_e_recebe_o_recorte_do_selector(
        self,
        client,
        aux_obras,
        requisicao_autorizada,
        movimentacao_requisicao_do_aux,
        saida_registrada,
        movimentacao_outro_setor,
    ):
        # Contrato HTTP/render: a policy não mudou (#112), então o auxiliar entra
        # na página, e o que ela renderiza é o recorte do selector. A matriz de
        # visibilidade em si é coberta em test_selectors.
        from apps.estoque.selectors import movimentacoes_visiveis_para

        client.force_login(aux_obras)
        response = client.get(URL_MOVIMENTACOES)

        assert response.status_code == 200
        assert {m.pk for m in response.context['page_obj'].object_list} == set(
            movimentacoes_visiveis_para(aux_obras.pk).values_list('pk', flat=True)
        )

    def test_paginacao_server_side(
        self,
        client,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque

        req, _ = requisicao_autorizada
        for _ in range(30):
            MovimentacaoEstoque.objects.create(
                tipo=TipoMovimentacaoEstoque.CONSUMO,
                material=material_disponivel,
                estoque=estoque_principal,
                delta_fisico=Decimal('-1'),
                delta_reservado=Decimal('-1'),
                requisicao=req,
                ator=superuser,
            )
        client.force_login(superuser)
        page1 = client.get(URL_MOVIMENTACOES)
        assert len(page1.context['page_obj'].object_list) == 25
        assert page1.context['page_obj'].has_next() is True
        page2 = client.get(URL_MOVIMENTACOES, {'page': 2})
        assert page2.status_code == 200
        assert len(page2.context['page_obj'].object_list) >= 1

    def test_empty_state_quando_ledger_vazio(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert response.context['page_obj'].paginator.count == 0
        assert b'Nenhuma movimenta' in response.content

    def test_paginacao_usa_componente_com_rotulo_e_aria_label_proprios(
        self,
        client,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque

        req, _ = requisicao_autorizada
        for _ in range(30):
            MovimentacaoEstoque.objects.create(
                tipo=TipoMovimentacaoEstoque.CONSUMO,
                material=material_disponivel,
                estoque=estoque_principal,
                delta_fisico=Decimal('-1'),
                delta_reservado=Decimal('-1'),
                requisicao=req,
                ator=superuser,
            )
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES)
        total = response.context['page_obj'].paginator.count
        assert 'aria-label="Paginação das movimentações"'.encode() in response.content
        esperado = f'<span class="tabular-nums">{total}</span> movimentações'
        assert esperado.encode() in response.content

    def test_menu_mostra_link_para_almox(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert URL_MOVIMENTACOES.encode() in response.content

    def test_comentarios_dos_partials_nao_vazam_para_a_tela(
        self, client, superuser, requisicao_autorizada
    ):
        # Comentário multilinha precisa ser {% comment %}, não {# #} (que é
        # single-line) — senão o texto do comentário renderiza como conteúdo.
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES)
        assert 'Badge semântico'.encode() not in response.content
        assert 'Célula de delta'.encode() not in response.content
        assert 'Paginação server-side'.encode() not in response.content


class TestHistoricoMovimentacoesFiltros:
    """Camada de filtros HTMX sobre o ledger (issue #7)."""

    def test_filtro_material_reduz_resultado(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        com = client.get(URL_MOVIMENTACOES, {'material': 'MAT001'})
        sem = client.get(URL_MOVIMENTACOES, {'material': 'inexistente'})
        assert com.context['page_obj'].paginator.count >= 1
        assert sem.context['page_obj'].paginator.count == 0

    def test_requisicao_htmx_devolve_so_partial(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert any(
            t.name == 'resultados'
            and t.origin.template_name == 'estoque/historico_movimentacoes.html'
            for t in response.templates
        )
        nomes = {t.name for t in response.templates}
        # Não renderiza o template completo (app-bar) num swap parcial.
        assert 'estoque/historico_movimentacoes.html' not in nomes

    def test_requisicao_normal_devolve_template_completo(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES)
        nomes = {t.name for t in response.templates}
        assert 'estoque/historico_movimentacoes.html' in nomes

    def test_ordenacao_asc_inverte_cronologia(
        self,
        client,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque

        req, _ = requisicao_autorizada
        for _ in range(2):
            MovimentacaoEstoque.objects.create(
                tipo=TipoMovimentacaoEstoque.CONSUMO,
                material=material_disponivel,
                estoque=estoque_principal,
                delta_fisico=Decimal('-1'),
                delta_reservado=Decimal('-1'),
                requisicao=req,
                ator=superuser,
            )
        client.force_login(superuser)
        desc = client.get(URL_MOVIMENTACOES).context['page_obj'].object_list
        asc = (
            client.get(URL_MOVIMENTACOES, {'ordem': 'asc'})
            .context['page_obj']
            .object_list
        )
        assert [m.pk for m in asc] == [m.pk for m in reversed(list(desc))]
        assert client.get(URL_MOVIMENTACOES, {'ordem': 'asc'}).context['ordem'] == 'asc'

    def test_filtro_setor_visivel_so_para_almox(
        self, client, chefe_almoxarifado, chefe_obras
    ):
        client.force_login(chefe_almoxarifado)
        assert client.get(URL_MOVIMENTACOES).context['mostrar_filtro_setor'] is True
        client.force_login(chefe_obras)
        assert client.get(URL_MOVIMENTACOES).context['mostrar_filtro_setor'] is False

    def test_chefe_setor_nao_filtra_por_setor_via_querystring(
        self, client, chefe_obras, requisicao_autorizada, movimentacao_outro_setor
    ):
        # Mesmo forçando ?setor=<outro> na URL, chefe de setor não vaza dado.
        setor_ti = movimentacao_outro_setor.requisicao.setor_beneficiario_id
        client.force_login(chefe_obras)
        response = client.get(URL_MOVIMENTACOES, {'setor': setor_ti})
        assert response.status_code == 200
        pks = {m.pk for m in response.context['page_obj'].object_list}
        assert movimentacao_outro_setor.pk not in pks

    def test_querystring_invalida_nao_quebra(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        response = client.get(
            URL_MOVIMENTACOES,
            {
                'data_ini': 'abc',
                'data_fim': '2026-13-99',
                'setor': 'xyz',
                'ordem': 'lixo',
                'tipos': 'nao_existe',
                'page': 'foo',
            },
        )
        assert response.status_code == 200

    def test_chip_so_saidas_marca_estado_ativo(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        ativo = client.get(
            URL_MOVIMENTACOES,
            {'tipos': ['consumo', 'saida_excepcional']},
        )
        inativo = client.get(URL_MOVIMENTACOES)
        assert ativo.context['so_saidas_ativo'] is True
        assert inativo.context['so_saidas_ativo'] is False

    def test_chip_so_saidas_reemitido_via_oob_no_swap_htmx(
        self, client, superuser, requisicao_autorizada
    ):
        # Bug-regressão: o chip vive fora de #resultados-movimentacoes, então
        # numa resposta HTMX precisa ser reemitido como out-of-band para o
        # estado ativo e a URL de alternância refletirem o novo recorte.
        client.force_login(superuser)
        parcial = client.get(
            URL_MOVIMENTACOES,
            {'tipos': ['consumo', 'saida_excepcional']},
            HTTP_HX_REQUEST='true',
        ).content
        assert b'id="chip-so-saidas"' in parcial
        assert b'hx-swap-oob="true"' in parcial
        assert b'aria-current="true"' in parcial

    def test_chip_so_saidas_sem_oob_na_pagina_completa(
        self, client, superuser, requisicao_autorizada
    ):
        # Render completo: chip único, sem atributo OOB (evita id duplicado).
        client.force_login(superuser)
        conteudo = client.get(URL_MOVIMENTACOES).content
        assert conteudo.count(b'id="chip-so-saidas"') == 1
        assert b'hx-swap-oob' not in conteudo

    def test_flag_tem_filtro_ativo(self, client, superuser, requisicao_autorizada):
        client.force_login(superuser)
        com = client.get(URL_MOVIMENTACOES, {'material': 'x'})
        sem = client.get(URL_MOVIMENTACOES)
        assert com.context['tem_filtro_ativo'] is True
        assert sem.context['tem_filtro_ativo'] is False

    def test_empty_state_contextual_distingue_filtro_de_ledger_vazio(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        # Filtro sem resultado → mensagem específica de filtro, e NÃO a de
        # ledger vazio.
        filtrado = client.get(URL_MOVIMENTACOES, {'material': 'inexistente'}).content
        assert 'Nenhum resultado para este filtro'.encode() in filtrado
        assert 'Nenhuma movimentação encontrada'.encode() not in filtrado

    def test_chip_so_saidas_preserva_filtros_atuais(
        self, client, chefe_almoxarifado, setor_obras
    ):
        # Bug-regressão: alternar o chip não pode descartar o recorte atual.
        client.force_login(chefe_almoxarifado)
        response = client.get(
            URL_MOVIMENTACOES,
            {'material': 'parafuso', 'ordem': 'asc', 'setor': setor_obras.pk},
        )
        url_chip = response.context['url_chip_so_saidas']
        assert 'material=parafuso' in url_chip
        assert 'ordem=asc' in url_chip
        assert f'setor={setor_obras.pk}' in url_chip
        assert 'tipos=consumo' in url_chip
        assert 'tipos=saida_excepcional' in url_chip


class TestHistoricoMovimentacoesFiltrosPartials:
    """Cobertura da extração dos campos de filtro em partials (issue #88)."""

    def test_form_expoe_method_get_e_action_nativos(self, client, superuser):
        client.force_login(superuser)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        assert 'method="get"' in content
        assert f'action="{URL_MOVIMENTACOES}"' in content

    def test_submissao_nativa_sem_htmx_retorna_pagina_completa_filtrada(
        self, client, superuser, requisicao_autorizada
    ):
        # Sem HTTP_HX_REQUEST simula o fallback de navegação nativa do
        # <form method="get">: precisa renderizar a página completa (não só
        # o partial 'resultados') e ainda assim aplicar o filtro.
        client.force_login(superuser)
        response = client.get(URL_MOVIMENTACOES, {'material': 'MAT001'})
        nomes = {t.name for t in response.templates}
        assert 'estoque/historico_movimentacoes.html' in nomes
        assert response.context['page_obj'].paginator.count >= 1

    def test_limpar_filtros_href_navegacao_nativa(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        content = client.get(URL_MOVIMENTACOES, {'material': 'MAT001'}).content.decode()
        assert f'href="{URL_MOVIMENTACOES}"' in content
        assert 'Limpar filtros' in content

    def test_checkbox_tipo_tem_alvo_de_toque(self, client, superuser):
        client.force_login(superuser)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        idx = content.index('name="tipos"')
        label_ini = content.rindex('<label', 0, idx)
        label_fim = content.index('</label>', idx) + len('</label>')
        assert 'min-h-11' in content[label_ini:label_fim]

    def test_filtro_setor_label_vinculado_ao_select(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        assert 'for="filtro-setor"' in content
        assert 'id="filtro-setor"' in content

    def test_filtro_setor_ausente_para_chefe_de_setor(self, client, chefe_obras):
        client.force_login(chefe_obras)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        assert 'id="filtro-setor"' not in content

    def test_limpar_filtros_reemitido_via_oob_no_swap_htmx(
        self, client, superuser, requisicao_autorizada
    ):
        # Bug-regressão (achado do CodeRabbit): filter_acoes.html vive fora
        # de #resultados-movimentacoes (dentro do <form>), então numa
        # resposta HTMX precisa ser reemitido como out-of-band pra refletir
        # tem_filtro_ativo — senão "Limpar filtros" fica com o estado da
        # primeira renderização full-page. Mesmo padrão de
        # _chip_so_saidas.html (oob_chip).
        client.force_login(superuser)
        parcial = client.get(
            URL_MOVIMENTACOES, {'material': 'MAT001'}, HTTP_HX_REQUEST='true'
        ).content
        assert b'id="filtro-acoes-movimentacoes"' in parcial
        assert b'hx-swap-oob="true"' in parcial
        assert b'Limpar filtros' in parcial

    def test_limpar_filtros_sem_oob_na_pagina_completa(
        self, client, superuser, requisicao_autorizada
    ):
        client.force_login(superuser)
        conteudo = client.get(URL_MOVIMENTACOES, {'material': 'MAT001'}).content
        assert conteudo.count(b'id="filtro-acoes-movimentacoes"') == 1
        assert b'hx-swap-oob' not in conteudo

    def test_todos_os_campos_esperados_presentes(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        for campo in (
            'name="material"',
            'name="data_ini"',
            'name="data_fim"',
            'name="setor"',
            'name="tipos"',
        ):
            assert campo in content


class TestHistoricoMovimentacoesResponsivo:
    """Testes de estrutura HTML responsiva e atributos de acessibilidade."""

    def test_disclosure_nativo_presente_na_pagina(self, client, chefe_almoxarifado):
        # A barra de filtros usa <details>/<summary> nativo para disclosure mobile
        # — funciona sem JavaScript (progressive enhancement).
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 200
        assert b'<details' in response.content
        assert b'<summary' in response.content

    def test_chip_so_saidas_visivel_fora_do_disclosure(
        self, client, chefe_almoxarifado
    ):
        # O chip "só saídas" deve aparecer ANTES do <details> no HTML para
        # garantir visibilidade permanente no mobile sem abrir o disclosure.
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_MOVIMENTACOES)
        assert response.status_code == 200
        content = response.content.decode()
        pos_chip = content.find('id="chip-so-saidas"')
        pos_details = content.find('<details')
        assert pos_chip != -1, 'chip-so-saidas não encontrado'
        assert pos_details != -1, '<details não encontrado'
        assert pos_chip < pos_details, 'chip deve aparecer antes do <details>'

    def _consumos_isolados(
        self,
        n,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        """Cria `n` consumos e devolve o filtro que isola só eles.

        Duas coisas precisam ser verdade ao mesmo tempo: a contagem anunciada
        tem de ser exatamente `n`, e o ledger não pode ficar incoerente só para
        o teste caber.

        O isolamento é pelo **tipo**, não por um material inventado. As fixtures
        deixam uma `reserva` no ledger, então filtrar por `consumo` já separa o
        que este teste criou — sem material órfão, fora da requisição e sem
        `SaldoEstoque`. O material continua sendo o da própria requisição.

        A escrita direta no ledger é a mesma dos testes vizinhos desta classe:
        aqui o assunto é a frase anunciada, não a aritmética de saldo, que tem
        cobertura própria nos testes de service.
        """
        from decimal import Decimal

        from apps.estoque.models import MovimentacaoEstoque, TipoMovimentacaoEstoque

        req, _ = requisicao_autorizada
        for _ in range(n):
            MovimentacaoEstoque.objects.create(
                tipo=TipoMovimentacaoEstoque.CONSUMO,
                material=material_disponivel,
                estoque=estoque_principal,
                delta_fisico=Decimal('-1'),
                delta_reservado=Decimal('-1'),
                requisicao=req,
                ator=superuser,
            )
        return {'tipos': TipoMovimentacaoEstoque.CONSUMO.value}

    def test_lista_de_resultados_nao_e_live_region(self, client, chefe_almoxarifado):
        """Marcar a listagem inteira como live region faz o leitor reler tudo.

        O wrapper carregava `aria-live="polite" aria-atomic="true"`: a cada
        ajuste de filtro, as 25 linhas eram relidas do começo. O anúncio útil é
        o tamanho do resultado, não o resultado — e ele vive fora da lista, no
        mesmo padrão que o histórico de requisições já usa.
        """
        client.force_login(chefe_almoxarifado)
        html = client.get(URL_MOVIMENTACOES).content.decode()

        inicio = html.index('id="resultados-movimentacoes"')
        wrapper = html[html.rindex('<div', 0, inicio) : html.index('>', inicio) + 1]

        assert 'aria-live' not in wrapper
        assert 'aria-atomic' not in wrapper

    def test_regiao_de_resumo_e_live_region_de_verdade(
        self, client, chefe_almoxarifado
    ):
        """Um `<p>` sem `role` troca de texto sem anunciar nada.

        Ele passaria em todos os testes de mensagem e não anunciaria uma única
        vez. O `role` é o contrato; o texto é só a carga.
        """
        client.force_login(chefe_almoxarifado)
        html = client.get(URL_MOVIMENTACOES).content.decode()

        inicio = html.index('id="resumo-movimentacoes"')
        tag = html[html.rindex('<', 0, inicio) : html.index('>', inicio) + 1]

        assert 'role="status"' in tag
        assert 'sr-only' in tag
        assert html[html.index('>', inicio) + 1 :].lstrip().startswith('<'), (
            'a região nasce vazia: no carregamento inicial nada mudou ainda'
        )

    def test_swap_oob_preserva_o_elemento_da_live_region(
        self, client, chefe_almoxarifado
    ):
        """`innerHTML:` troca o conteúdo; um oob sem prefixo levaria o `role` junto.

        A resposta HTMX não carrega o `<p>` — carrega só o conteúdo dele. Exigir
        `role="status"` aqui seria exigir o oposto do que o modo de swap faz. O
        que dá para provar numa resposta Django é o modo, e a ausência de um
        segundo `id` que reintroduziria a região por cima.
        """
        client.force_login(chefe_almoxarifado)
        html = client.get(URL_MOVIMENTACOES, HTTP_HX_REQUEST='true').content.decode()

        assert 'hx-swap-oob="innerHTML:#resumo-movimentacoes"' in html
        assert 'id="resumo-movimentacoes"' not in html

    def test_filtro_sem_resultado_anuncia_zero_movimentacoes(
        self, client, chefe_almoxarifado
    ):
        """O caso que a issue nomeia: a lista some e nada é dito.

        Sem anúncio, quem filtrou não sabe se filtrou demais ou se a requisição
        travou.
        """
        client.force_login(chefe_almoxarifado)
        html = client.get(
            URL_MOVIMENTACOES, {'material': 'inexistente-xyz'}, HTTP_HX_REQUEST='true'
        ).content.decode()

        assert 'Nenhuma movimentação encontrada.' in html

    def test_anuncio_no_singular_com_uma_movimentacao(
        self,
        client,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        """ "1 movimentações" é o erro que um teste só do zero deixa passar."""
        filtro = self._consumos_isolados(
            1,
            superuser,
            requisicao_autorizada,
            material_disponivel,
            estoque_principal,
        )
        client.force_login(superuser)
        html = client.get(
            URL_MOVIMENTACOES, filtro, HTTP_HX_REQUEST='true'
        ).content.decode()

        assert '1 movimentação encontrada.' in html

    def test_anuncio_no_plural_com_duas_movimentacoes(
        self,
        client,
        superuser,
        requisicao_autorizada,
        material_disponivel,
        estoque_principal,
    ):
        """Os dois `pluralize` flexionando juntos, casados na frase inteira."""
        filtro = self._consumos_isolados(
            2,
            superuser,
            requisicao_autorizada,
            material_disponivel,
            estoque_principal,
        )
        client.force_login(superuser)
        html = client.get(
            URL_MOVIMENTACOES, filtro, HTTP_HX_REQUEST='true'
        ).content.decode()

        assert '2 movimentações encontradas.' in html


class TestHistoricoMovimentacoesFiltrosResponsivo:
    """Paridade estrutural da barra de filtros extraída (issue #88)."""

    def test_barra_filtros_html_balanceado(self, client, superuser):
        client.force_login(superuser)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        inicio = content.index('<details')
        fim = content.index('</details>', inicio) + len('</details>')
        _assert_html_balanceado(content[inicio:fim])

    def test_wrapper_form_tem_sm_block_important(self, client, superuser):
        # Regressão de drift: historico_movimentacoes.html não tinha
        # `sm:block!` no wrapper do form (só historico_requisicoes.html
        # tinha) — filter_shell.html#abertura unifica as 2 telas.
        client.force_login(superuser)
        content = client.get(URL_MOVIMENTACOES).content.decode()
        assert 'sm:block!' in content

    def test_template_usa_partials_de_filtro_sem_duplicar_campos_inline(self):
        caminho = (
            Path(__file__).resolve().parent.parent
            / 'templates'
            / 'estoque'
            / 'historico_movimentacoes.html'
        )
        fonte = caminho.read_text()
        assert 'components/filter_shell.html#abertura' in fonte
        assert 'components/filter_busca.html' in fonte
        assert 'components/filter_data.html' in fonte
        assert 'components/filter_checkbox_group.html' in fonte
        assert 'components/filter_acoes.html' in fonte
        assert 'type="search"' not in fonte
        assert 'type="date"' not in fonte
        assert 'type="checkbox"' not in fonte

    def test_chip_so_saidas_composto_fora_do_filter_shell(self):
        caminho = (
            Path(__file__).resolve().parent.parent
            / 'templates'
            / 'estoque'
            / 'historico_movimentacoes.html'
        )
        fonte = caminho.read_text()
        idx_chip = fonte.index('_chip_so_saidas.html')
        idx_shell = fonte.index('filter_shell.html#abertura')
        assert idx_chip < idx_shell


URL_NOVA_LINHA_ITEM = reverse('estoque:nova_linha_item_saida_excepcional')


class TestNovaLinhaItemSaidaExcepcionalView:
    def test_chefe_recebe_partial_com_linha_vazia(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA_LINHA_ITEM, {'index': '2'})
        assert response.status_code == 200
        html = response.content.decode()
        assert 'itens-2-material_id' in html
        assert 'itens-2-quantidade' in html

    def test_index_ausente_usa_zero(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        response = client.get(URL_NOVA_LINHA_ITEM)
        assert response.status_code == 200
        assert 'itens-0-material_id' in response.content.decode()

    def test_solicitante_recebe_403(self, client, solicitante):
        client.force_login(solicitante)
        response = client.get(URL_NOVA_LINHA_ITEM)
        assert response.status_code == 403

    def test_anonimo_redirecionado_para_login(self, client):
        response = client.get(URL_NOVA_LINHA_ITEM)
        assert response.status_code == 302
        assert 'login' in response['Location']


class TestNovaSaidaExcepcionalAvisoDivergencia:
    """Issue #111: a view liga o hook de aviso e avisa o operador."""

    def _post(self, client, material, quantidade):
        return client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'Material avariado em vistoria',
                'itens-TOTAL_FORMS': '1',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material.pk),
                'itens-0-quantidade': quantidade,
            },
            follow=False,
        )

    def test_view_injeta_o_hook_de_divergencia(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        """O service é chamado com _pos_saida_hook não nulo."""
        from unittest.mock import patch

        from apps.estoque.models import SaidaExcepcional

        client.force_login(chefe_almoxarifado)
        with patch(
            'apps.estoque.views.registrar_saida_excepcional',
            return_value=SaidaExcepcional(numero_publico='SXP-2026-000001'),
        ) as service:
            self._post(client, material_disponivel, '5')

        # A view envolve o hook num closure para capturar os ids avisados, então
        # não dá para comparar identidade com
        # registrar_timeline_divergencia_saida_excepcional. O efeito real é
        # travado pelos dois testes de integração abaixo.
        assert service.call_count == 1
        hook = service.call_args.kwargs['_pos_saida_hook']
        assert hook is not None
        assert callable(hook)

    def test_baixa_que_cria_divergencia_avisa_o_operador(
        self,
        client,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        """messages.warning além do success, citando as requisições afetadas."""
        client.force_login(chefe_almoxarifado)
        response = self._post(client, material_disponivel, '98')

        mensagens = list(response.wsgi_request._messages)
        niveis = [m.level_tag for m in mensagens]
        assert 'success' in niveis
        assert 'warning' in niveis

        # Texto completo: a contagem faz parte do contrato, e uma asserção de
        # substring aceitaria qualquer dígito solto vindo do número da saída.
        aviso = next(m for m in mensagens if m.level_tag == 'warning')
        assert str(aviso) == (
            'Esta baixa criou divergência crítica de estoque: '
            '1 requisição autorizada foi avisada. A separação delas fica bloqueada '
            'até a divergência ser resolvida ou a requisição ser cancelada.'
        )

    def test_baixa_sem_divergencia_nao_avisa_o_operador(
        self,
        client,
        chefe_almoxarifado,
        estoque_principal,
        material_disponivel,
        requisicao_autorizada,
    ):
        """Sem divergência criada, só o success de sempre."""
        client.force_login(chefe_almoxarifado)
        response = self._post(client, material_disponivel, '5')

        mensagens = list(response.wsgi_request._messages)
        assert [m.level_tag for m in mensagens] == ['success']


class TestSumarioDeErrosNaSaidaExcepcional:
    """A tela onde falhar em silêncio custa mais — a issue #125.

    Baixa administrativa direta, restrita ao chefe de almoxarifado, com formset
    de itens e autocomplete, sem reversão fácil. Era a única tela longa de
    formset **sem** o sumário que o projeto construiu para exatamente isso.
    """

    DADOS_INVALIDOS = {
        'motivo': 'avaria',
        'observacao': '',
        'itens-TOTAL_FORMS': '1',
        'itens-INITIAL_FORMS': '0',
        'itens-MIN_NUM_FORMS': '0',
        'itens-MAX_NUM_FORMS': '1000',
        'itens-0-material_id': '',
        'itens-0-quantidade': '',
    }

    def _post_invalido(self, client, chefe_almoxarifado):
        client.force_login(chefe_almoxarifado)
        return client.post(URL_NOVA, data=self.DADOS_INVALIDOS)

    def test_post_invalido_traz_o_sumario(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        """O guarda de arquivo vê o include; só o POST vê a view montar o contexto.

        `{% erros_do_formulario form formset %}` depende de a view devolver os
        dois nomes no contexto de erro. Uma tag correta sobre um contexto vazio
        renderiza silêncio — que é exatamente a falha que a tela tinha.
        """
        html = self._post_invalido(client, chefe_almoxarifado).content.decode()
        assert 'id="sumario-erros"' in html
        assert 'autofocus' in html
        assert 'problema' in html

    def test_post_invalido_nomeia_o_campo_com_erro(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        html = self._post_invalido(client, chefe_almoxarifado).content.decode()
        assert 'href="#id_observacao"' in html

    def test_erro_de_formset_aparece_uma_vez_so(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        """A duplicata que a #125 removeu: sumário no topo e alerta lá embaixo.

        Num viewport de 375px os dois pontos ficam a várias roladas de
        distância, sem marcador de que são o mesmo erro. O usuário lê o total
        no topo, corrige, e reencontra um deles achando que é mais um.
        """
        html = self._post_invalido(client, chefe_almoxarifado).content.decode()
        assert html.count('A saída precisa ter ao menos um item.') == 1

    def test_item_duplicado_conta_um_problema_e_nao_dois(
        self, client, chefe_almoxarifado, estoque_principal, material_disponivel
    ):
        """A duplicata que sobrou depois da #125: duas redações, uma falha.

        `BaseItemSaidaExcepcionalFormSet.clean()` anexava o erro à linha ("Este
        material já foi adicionado em outra linha.") e levantava outra frase no
        formset ("Não é permitido adicionar o mesmo material mais de uma vez.").
        A proteção de `coletar_erros` casa mensagens **idênticas**, então as
        duas passavam: o sumário abria com "2 problemas encontrados" para um
        material repetido, e o segundo item não tinha âncora para lugar nenhum.
        """
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '2',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
                'itens-0-material_id': str(material_disponivel.pk),
                'itens-0-material_label': material_disponivel.nome,
                'itens-0-quantidade': '1',
                'itens-1-material_id': str(material_disponivel.pk),
                'itens-1-material_label': material_disponivel.nome,
                'itens-1-quantidade': '2',
            },
        )

        html = response.content.decode()
        assert response.status_code == 200
        assert '1 problema encontrado' in html
        assert 'problemas encontrados' not in html
        assert 'mais de uma vez' not in html

    def test_erro_de_formset_leva_a_secao_de_materiais(
        self, client, chefe_almoxarifado, estoque_principal
    ):
        """O item sem campo do sumário precisa ser link, e o alvo precisa existir.

        "A saída precisa ter ao menos um item." não pertence a campo nenhum, e
        por isso saía do sumário como texto solto no meio de uma lista de links.
        O sumário anunciava e contava, mas não levava — a terceira coisa que ele
        promete valia só para erro de campo.
        """
        client.force_login(chefe_almoxarifado)
        response = client.post(
            URL_NOVA,
            data={
                'motivo': 'avaria',
                'observacao': 'obs válida',
                'itens-TOTAL_FORMS': '0',
                'itens-INITIAL_FORMS': '0',
                'itens-MIN_NUM_FORMS': '0',
                'itens-MAX_NUM_FORMS': '1000',
            },
        )

        html = response.content.decode()
        assert 'href="#sec-materiais"' in html
        assert 'id="sec-materiais"' in html
        assert 'tabindex="-1"' in html
