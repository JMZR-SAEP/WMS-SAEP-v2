"""Testes diretos de {% renderizar_campo_com_aria %} (sem DB, sem view)."""

from decimal import Decimal

import pytest
from django import forms
from django.template import Context, Template

from apps.core.templatetags.core_tags import formatar_quantidade


class _FormDeTeste(forms.Form):
    nome = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'minha-classe', 'placeholder': 'Nome'}),
    )
    apelido = forms.CharField(required=False)


def _render(tag_call: str, **ctx) -> str:
    template = Template('{% load core_tags %}' + tag_call)
    return template.render(Context(ctx))


def test_sem_ajuda_sem_erro_nao_adiciona_aria():
    form = _FormDeTeste()
    html = _render('{% renderizar_campo_com_aria field %}', field=form['nome'])
    assert 'aria-invalid' not in html
    assert 'aria-describedby' not in html


def test_com_ajuda_adiciona_describedby_ajuda():
    form = _FormDeTeste()
    html = _render(
        '{% renderizar_campo_com_aria field tem_ajuda=True %}', field=form['nome']
    )
    assert f'aria-describedby="{form["nome"].id_for_label}-ajuda"' in html
    assert 'aria-invalid' not in html


def test_com_erro_adiciona_aria_invalid_e_describedby_erro():
    form = _FormDeTeste(data={})
    form.is_valid()
    html = _render(
        '{% renderizar_campo_com_aria field tem_erro=field.errors %}',
        field=form['nome'],
    )
    assert 'aria-invalid="true"' in html
    assert f'aria-describedby="{form["nome"].id_for_label}-erro"' in html


def test_com_ajuda_e_erro_compoe_os_dois_ids_em_ordem():
    form = _FormDeTeste(data={})
    form.is_valid()
    html = _render(
        '{% renderizar_campo_com_aria field tem_ajuda=True tem_erro=field.errors %}',
        field=form['nome'],
    )
    id_campo = form['nome'].id_for_label
    assert f'aria-describedby="{id_campo}-ajuda {id_campo}-erro"' in html


def test_preserva_attrs_nativos_do_widget():
    form = _FormDeTeste()
    html = _render('{% renderizar_campo_com_aria field %}', field=form['nome'])
    assert 'minha-classe' in html
    assert 'placeholder="Nome"' in html
    assert 'required' in html


def test_campo_opcional_nao_tem_required_nativo():
    form = _FormDeTeste()
    html = _render('{% renderizar_campo_com_aria field %}', field=form['apelido'])
    assert 'required' not in html


class _FormComDescribedbyNoWidget(forms.Form):
    campo = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'aria-describedby': 'hint-externo'}),
    )


def test_preserva_aria_describedby_ja_definido_no_widget():
    form = _FormComDescribedbyNoWidget()
    html = _render('{% renderizar_campo_com_aria field %}', field=form['campo'])
    assert 'aria-describedby="hint-externo"' in html


def test_compoe_aria_describedby_do_widget_com_ajuda_e_erro():
    form = _FormComDescribedbyNoWidget(data={})
    form.is_valid()
    html = _render(
        '{% renderizar_campo_com_aria field tem_ajuda=True tem_erro=field.errors %}',
        field=form['campo'],
    )
    id_campo = form['campo'].id_for_label
    assert f'aria-describedby="hint-externo {id_campo}-ajuda {id_campo}-erro"' in html


@pytest.mark.parametrize(
    'qtd, unidade, esperado',
    [
        # Unidade → inteiro
        (Decimal('5.000'), 'un', '5'),
        (Decimal('1.000'), 'un', '1'),
        (Decimal('100.000'), 'un', '100'),
        # kg → 1 decimal
        (Decimal('2.500'), 'kg', '2.5'),
        (Decimal('10.000'), 'kg', '10.0'),
        (Decimal('0.100'), 'kg', '0.1'),
        # l → 1 decimal
        (Decimal('3.000'), 'l', '3.0'),
        (Decimal('1.500'), 'l', '1.5'),
        # m → 1 decimal
        (Decimal('4.200'), 'm', '4.2'),
        (Decimal('10.000'), 'm', '10.0'),
        # m2 → strip trailing zeros (casas significativas)
        (Decimal('2.000'), 'm2', '2'),
        (Decimal('1.500'), 'm2', '1.5'),
        (Decimal('1.230'), 'm2', '1.23'),
        # cx, pct, par, rolo → strip trailing zeros
        (Decimal('3.000'), 'cx', '3'),
        (Decimal('2.500'), 'pct', '2.5'),
        (Decimal('1.000'), 'par', '1'),
        (Decimal('6.000'), 'rolo', '6'),
        # None → fallback
        (None, 'un', '—'),
        (None, 'kg', '—'),
    ],
)
def test_formatar_quantidade(qtd, unidade, esperado):
    assert formatar_quantidade(qtd, unidade) == esperado


class TestMinutosTotais:
    """O prazo do bloqueio de login nunca é hardcoded na cópia.

    O filtro existe para que `AXES_COOLOFF_TIME` possa mudar sem que alguém
    lembre de editar o texto de `accounts/login_bloqueado.html`.
    """

    def _filtrar(self, valor):
        from apps.core.templatetags.core_tags import minutos_totais

        return minutos_totais(valor)

    def test_timedelta_vira_minutos_inteiros(self):
        from datetime import timedelta

        assert self._filtrar(timedelta(minutes=15)) == 15

    def test_arredonda_para_baixo(self):
        from datetime import timedelta

        assert self._filtrar(timedelta(seconds=119)) == 1

    def test_none_devolve_none(self):
        assert self._filtrar(None) is None

    def test_variavel_ausente_devolve_none(self):
        """Permalock: o axes omite `cooloff_timedelta` do contexto.

        `axes.helpers` monta o contexto com `if cool_off:` — com
        `AXES_COOLOFF_TIME = None` as chaves não entram. O Django resolve a
        variável ausente como `string_if_invalid`, que é `''` por padrão, e o
        guarda `is None` não pegava esse caso: a tela de bloqueio devolvia 500
        exatamente na configuração que o comentário do template diz suportar.
        """
        assert self._filtrar('') is None

    def test_valor_de_tipo_inesperado_devolve_none(self):
        """Não pode estourar: esta é a tela que o usuário vê já bloqueado."""
        assert self._filtrar('quinze minutos') is None
        assert self._filtrar(15) is None


class TestLoginBloqueadoSemPrazo:
    """A tela de bloqueio precisa renderizar nas duas configurações do axes."""

    def _render(self, **ctx):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        return render_to_string(
            'accounts/login_bloqueado.html', ctx, request=RequestFactory().get('/')
        )

    def test_com_prazo_mostra_os_minutos(self):
        from datetime import timedelta

        html = self._render(cooloff_timedelta=timedelta(minutes=15))
        assert '15 minutos' in html

    def test_sem_cooloff_renderiza_a_copia_sem_prazo(self):
        """Permalock (`AXES_COOLOFF_TIME = None`): sem a chave no contexto."""
        html = self._render()
        assert 'Aguarde e tente novamente mais tarde.' in html
        assert (
            'minuto'
            not in html.split('Aguarde e tente novamente mais tarde.')[0][-200:]
        )

    def test_cooloff_none_renderiza_a_copia_sem_prazo(self):
        html = self._render(cooloff_timedelta=None)
        assert 'Aguarde e tente novamente mais tarde.' in html

    def test_nao_vaza_a_matricula_tentada(self):
        """Repetir a matrícula transformaria a tela em oráculo de enumeração."""
        html = self._render(username='joao.silva')
        assert 'joao.silva' not in html


class _MensagemFalsa:
    """Dublê de `django.contrib.messages.storage.base.Message`.

    O filtro só lê `level_tag`, então o dublê evita montar um storage inteiro
    para exercitar ordenação — os testes de render, esses sim, usam o
    `FallbackStorage` real.
    """

    def __init__(self, level_tag: str, texto: str = ''):
        self.level_tag = level_tag
        self.texto = texto

    def __str__(self) -> str:
        return self.texto or self.level_tag

    def __repr__(self) -> str:
        return f'<{self.level_tag}:{self.texto}>'


class TestMensagensVisiveis:
    """O partial decide wrapper, ordem e visibilidade a partir desta lista.

    Enquanto o template iterava `messages` duas vezes, três defeitos moravam
    juntos: o wrapper polido renderizava vazio, `debug` chegava ao usuário final
    disfarçado de info, e tudo isso dependia de o `BaseStorage` do Django ser
    re-iterável — comportamento de framework que ninguém tinha declarado.
    """

    def _filtrar(self, *niveis):
        from apps.core.templatetags.core_tags import mensagens_visiveis

        return mensagens_visiveis([_MensagemFalsa(n) for n in niveis])

    def _tags(self, *niveis):
        return [m.level_tag for m in self._filtrar(*niveis)]

    def test_descarta_debug(self):
        assert self._tags('debug') == []

    def test_debug_nao_vira_info(self):
        """O catch-all antigo (`!= 'error' and != 'warning'`) renderizava debug."""
        assert self._tags('debug', 'success') == ['success']

    def test_storage_so_com_debug_devolve_lista_vazia(self):
        """É este caso que decide o wrapper: `{% if messages %}` seria verdadeiro."""
        assert self._filtrar('debug', 'debug') == []

    def test_assertivas_antes_de_polidas(self):
        assert self._tags('success', 'error') == ['error', 'success']

    def test_info_e_success_ficam_depois_de_warning(self):
        assert self._tags('info', 'warning') == ['warning', 'info']

    def test_nao_reordena_dentro_do_grupo_assertivo(self):
        """Não existe regra de warning antes de error — manda a ordem da view.

        Os `{% if %}/{% elif %}` do partial sempre foram condicionais por
        mensagem, não ordenação entre níveis: quem enfileirou primeiro aparece
        primeiro, porque é a ordem em que os fatos aconteceram.
        """
        assert self._tags('error', 'warning') == ['error', 'warning']
        assert self._tags('warning', 'error') == ['warning', 'error']

    def test_nao_reordena_dentro_do_grupo_polido(self):
        assert self._tags('info', 'success') == ['info', 'success']
        assert self._tags('success', 'info') == ['success', 'info']

    def test_preserva_ordem_de_chegada_entre_mensagens_do_mesmo_nivel(self):
        from apps.core.templatetags.core_tags import mensagens_visiveis

        mensagens = [_MensagemFalsa('success', t) for t in ('a', 'b', 'c')]
        assert [str(m) for m in mensagens_visiveis(mensagens)] == ['a', 'b', 'c']

    def test_entrada_vazia(self):
        assert self._filtrar() == []

    def test_nivel_desconhecido_e_tratado_como_polido(self):
        """Nível customizado é decisão consciente de quem o registrou.

        Descartar em silêncio esconderia a mensagem; tratar como assertivo daria
        a ela prioridade que ninguém pediu.
        """
        assert self._tags('error', 'custom') == ['error', 'custom']

    def test_devolve_lista_e_nao_gerador(self):
        """O template precisa iterar e testar verdade sobre o mesmo objeto."""
        assert isinstance(self._filtrar('success'), list)


# ---------------------------------------------------------------------------
# {% erros_do_formulario %} e a coleta que ela faz por dentro
#
# Vivem aqui, e não junto dos testes de view de um app: `coletar_erros` é
# apresentação pura — o que ela precisa é de um `Form` com `errors`, não de uma
# regra de domínio. Os casos ficavam em apps/requisicoes/tests/test_views.py
# por acidente de origem, e de lá governavam o comportamento de todas as telas.
# ---------------------------------------------------------------------------


def test_coletar_erros_achata_form_e_formset():
    """FormSet entra como fonte e o `id` sai com o prefixo da linha.

    O formset é montado aqui, e não puxado de `apps.requisicoes.forms`: o que
    está sendo exercido é a leitura de `formset.forms`, não uma regra de
    requisição, e um teste de core não precisa de um app de domínio para provar
    isso.
    """
    from django.forms import formset_factory

    from apps.core.templatetags.core_tags import coletar_erros

    class _LinhaForm(forms.Form):
        item_id = forms.IntegerField(label='Item')
        quantidade_entregue = forms.DecimalField(label='Quantidade entregue')

    FormSet = formset_factory(_LinhaForm, extra=0)
    formset = FormSet(
        data={
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-0-item_id': '',
            'form-0-quantidade_entregue': '',
        }
    )
    assert formset.is_valid() is False
    erros = coletar_erros(formset)
    assert erros
    assert any(e['id'] == 'id_form-0-quantidade_entregue' for e in erros)
    assert all({'id', 'rotulo', 'mensagem'} == set(e) for e in erros)


def _form_invalido(*, campos, erros, prefixo=None):
    """Form já validado e sujo, montado no teste em vez de puxado do domínio.

    `coletar_erros` é apresentação pura: o que ela precisa é de um `Form` com
    `errors`, não de uma regra de requisição. Montar aqui deixa o caso de teste
    ler o que está sendo exercido — dois erros no mesmo campo, `id` repetido
    entre fontes — em vez de escondê-lo atrás de um form de domínio que por
    acaso falha daquele jeito.
    """
    from django import forms

    class _Form(forms.Form):
        pass

    for nome, rotulo in campos.items():
        _Form.base_fields[nome] = forms.CharField(label=rotulo, required=False)

    form = _Form(data={}, prefix=prefixo)
    assert form.is_valid()
    for campo, mensagens in erros.items():
        for mensagem in mensagens:
            form.add_error(campo or None, mensagem)
    return form


def test_coletar_erros_agrega_mensagens_do_mesmo_campo():
    """Duas mensagens num campo são um problema, não dois.

    Antes, cada mensagem virava uma âncora — duas âncoras para o mesmo `#id`,
    e a segunda não movia a tela. O contador dizia "2 problemas" para um único
    lugar a visitar, que é justamente o número que o sumário existe para dar.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'quantidade': 'Quantidade'},
        erros={'quantidade': ['Obrigatório.', 'Deve ser maior que zero.']},
    )

    erros = coletar_erros(form)

    assert len(erros) == 1
    assert erros[0]['id'] == 'id_quantidade'
    assert erros[0]['rotulo'] == 'Quantidade'
    assert erros[0]['mensagem'] == 'Obrigatório. Deve ser maior que zero.'


def test_coletar_erros_nao_agrega_erro_sem_campo():
    """Erro sem alvo não tem chave para agrupar — juntá-los somaria origens.

    `__all__` e `non_form_errors` não apontam para controle nenhum. Agrupá-los
    pela chave vazia colaria erros de fontes diferentes numa linha só.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'quantidade': 'Quantidade'},
        erros={'': ['Combinação inválida.', 'Período fechado.']},
    )

    erros = coletar_erros(form)

    assert [e['mensagem'] for e in erros] == [
        'Combinação inválida.',
        'Período fechado.',
    ]


def test_coletar_erros_preserva_ordem_de_primeira_aparicao():
    """O alvo que errou primeiro fica em primeiro, mesmo recebendo mensagem depois.

    Sem isso a ordem da lista dependeria de qual fonte falou por último, e o
    sumário mudaria de ordem entre dois POSTs com os mesmos erros.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    primeiro = _form_invalido(
        campos={'material': 'Material', 'quantidade': 'Quantidade'},
        erros={'material': ['Obrigatório.'], 'quantidade': ['Obrigatório.']},
    )
    segundo = _form_invalido(
        campos={'material': 'Material'},
        erros={'material': ['Material inativo.']},
    )

    erros = coletar_erros(primeiro, segundo)

    assert [e['id'] for e in erros] == ['id_material', 'id_quantidade']
    assert erros[0]['mensagem'] == 'Obrigatório. Material inativo.'


def test_coletar_erros_nao_repete_mensagem_que_ja_tem_ancora():
    """Formset que faz `add_error` **e** `raise` emite a mesma frase duas vezes.

    `BaseItemAtendimentoFormSet.clean()` marca o campo e levanta a mesma
    mensagem: uma vira erro de campo, outra vira `non_form_error`. Sem
    tratamento o sumário lista as duas — "Item id: Item duplicado" e "Item
    duplicado" — e o dispositivo que existe para acabar com erro repetido passa
    a produzir um.

    Fica a versão com âncora, que leva ao controle; a solta é ruído.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'item_id': 'Item id'},
        erros={
            'item_id': ['Item duplicado no atendimento.'],
            '': ['Item duplicado no atendimento.'],
        },
    )

    erros = coletar_erros(form)

    assert len(erros) == 1
    assert erros[0]['id'] == 'id_item_id'
    assert erros[0]['mensagem'] == 'Item duplicado no atendimento.'


def test_coletar_erros_mantem_mensagem_sem_alvo_que_nao_tem_par():
    """Desduplicar não pode virar engolir: sem par de campo, a mensagem fica."""
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'item_id': 'Item id'},
        erros={
            'item_id': ['Obrigatório.'],
            '': ['A requisição precisa ter ao menos um item.'],
        },
    )

    erros = coletar_erros(form)

    assert [e['mensagem'] for e in erros] == [
        'Obrigatório.',
        'A requisição precisa ter ao menos um item.',
    ]


def test_coletar_erros_mesma_mensagem_em_campos_diferentes_nao_colapsa():
    """ "Obrigatório." em dois campos são dois lugares a visitar, não um."""
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'setor': 'Setor', 'motivo': 'Motivo'},
        erros={'setor': ['Obrigatório.'], 'motivo': ['Obrigatório.']},
    )

    erros = coletar_erros(form)

    assert [e['id'] for e in erros] == ['id_setor', 'id_motivo']


def test_coletar_erros_id_repetido_entre_fontes_mantem_o_primeiro_rotulo():
    """Colisão de `id` consolida, e o rótulo do primeiro é o que fica.

    `id` repetido no DOM viola a unicidade que o HTML espera: o navegador salta
    para o primeiro elemento com aquele `id`, então duas âncoras levariam ao
    mesmo lugar. Consolidar é o comportamento honesto — e o rótulo não pode
    mudar debaixo do item conforme fontes posteriores são lidas.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    primeiro = _form_invalido(
        campos={'quantidade': 'Quantidade'},
        erros={'quantidade': ['Obrigatório.']},
    )
    segundo = _form_invalido(
        campos={'quantidade': 'Qtd.'},
        erros={'quantidade': ['Acima do saldo.']},
    )

    erros = coletar_erros(primeiro, segundo)

    assert len(erros) == 1
    assert erros[0]['rotulo'] == 'Quantidade'
    assert erros[0]['mensagem'] == 'Obrigatório. Acima do saldo.'


def test_coletar_erros_aceita_mensagem_solta_da_view():
    """A falha que a view já traduziu entra pela mesma porta.

    É o erro dos modais: a view captura a exceção de domínio e passa a string.
    Antes ela ia para uma caixa própria, com markup próprio, e o formulário
    passava a ter duas superfícies de erro que não sabiam uma da outra.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    erros = coletar_erros('Justificativa é obrigatória.', None, '   ')

    assert erros == [
        {'id': '', 'rotulo': '', 'mensagem': 'Justificativa é obrigatória.'}
    ]


def test_coletar_erros_mensagem_solta_cede_lugar_a_versao_com_ancora():
    """Mesma frase vinda da view e do Form é uma falha, não duas.

    A proteção já existia para `non_form_errors`; a string da view herda a
    mesma regra por entrar pelo mesmo caminho. Sem isso, uma view que
    reapresenta o erro do serviço junto do form bound duplicaria o item.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    form = _form_invalido(
        campos={'justificativa': 'Justificativa'},
        erros={'justificativa': ['Justificativa é obrigatória.']},
    )

    erros = coletar_erros('Justificativa é obrigatória.', form)

    assert len(erros) == 1
    assert erros[0]['id'] == 'id_justificativa'


def test_erros_do_formulario_devolve_contexto_do_componente():
    """A tag é a única porta: ela coleta e devolve o contexto já montado."""
    from apps.core.templatetags.core_tags import erros_do_formulario

    form = _form_invalido(
        campos={'motivo': 'Motivo'},
        erros={'motivo': ['Obrigatório.']},
    )

    contexto = erros_do_formulario(form, acao='recusar', id='modal-erro', focar=False)

    assert contexto['acao'] == 'recusar'
    assert contexto['id'] == 'modal-erro'
    assert contexto['focar'] is False
    assert [e['id'] for e in contexto['erros']] == ['id_motivo']


def test_erro_sem_campo_vira_link_quando_ha_ancora():
    from apps.core.templatetags.core_tags import coletar_erros

    (item,) = coletar_erros(
        'A saída precisa ter ao menos um item.',
        ancora_geral='sec-materiais',
    )

    assert item == {
        'id': 'sec-materiais',
        'rotulo': '',
        'mensagem': 'A saída precisa ter ao menos um item.',
    }


def test_ancora_geral_nao_vira_chave_de_agrupamento():
    """Duas falhas na mesma seção continuam sendo duas linhas.

    `ancora_geral` é destino, não identidade. Se ele entrasse pelo caminho
    de agrupamento por alvo, duas mensagens de formset colariam numa frase
    só — o oposto do que o sumário existe para fazer.
    """
    from apps.core.templatetags.core_tags import coletar_erros

    erros = coletar_erros(
        'Item inválido para esta requisição.',
        'Item duplicado no atendimento.',
        ancora_geral='sec-itens',
    )

    assert [e['mensagem'] for e in erros] == [
        'Item inválido para esta requisição.',
        'Item duplicado no atendimento.',
    ]
    assert {e['id'] for e in erros} == {'sec-itens'}


def test_sem_ancora_geral_o_item_segue_sem_link():
    """O default não inventa destino — tela que não declarou alvo não ganha
    âncora quebrada de brinde."""
    from apps.core.templatetags.core_tags import coletar_erros

    (item,) = coletar_erros('Falha genérica.')

    assert item['id'] == ''
