"""Testes diretos de components/item_form_row.html (sem DB, sem view)."""

from django.forms import BooleanField
from django.forms.formsets import DELETION_FIELD_NAME
from django.template.loader import render_to_string

from apps.requisicoes.forms import ItemRequisicaoFormSet


def _render(form_index=0):
    form = ItemRequisicaoFormSet.form(prefix=f'itens-{form_index}')
    form.fields[DELETION_FIELD_NAME] = BooleanField(label='Deletar', required=False)
    return render_to_string(
        'components/item_form_row.html',
        {
            'material_id_field': form['material_id'],
            'material_label_field': form['material_label'],
            'quantidade_field': form['quantidade_solicitada'],
            'quantidade_label': 'Quantidade',
            'autocomplete_url_name': 'requisicoes:buscar_materiais',
            'autocomplete_item_template': (
                'estoque/partials/_autocomplete_item_material.html'
            ),
            'delete_field': form[DELETION_FIELD_NAME],
            'form_index': form_index,
        },
    )


def test_linha_e_um_grupo_nomeado():
    """Sem grupo, N linhas viram 3N controles cujos nomes acessíveis se repetem.

    Uma requisição de 10 materiais entrega "Material / Quantidade / Remover"
    dez vezes seguidas, e nada diz em qual linha o foco está. É o mesmo padrão
    que requisicoes/atender_retirada.html já aplica por item.
    """
    html = _render(form_index=2)
    assert 'role="group"' in html
    assert 'aria-label="Item 3"' in html


def test_botao_remover_e_nomeado_pela_posicao_da_linha():
    """Todo botão de remover tinha o mesmo nome acessível ("Remover item").

    Depois de remover uma linha o foco vai para o botão vizinho — que anunciava
    exatamente o mesmo texto do botão anterior, sem nada indicando que a
    remoção aconteceu nem onde o foco parou.
    """
    html = _render(form_index=4)
    assert 'aria-label="Remover item 5"' in html
    assert 'aria-label="Remover item"' not in html


def test_botao_remover_tem_hook_estavel_para_o_js():
    """O JS move o foco para o botão da linha vizinha.

    Ele selecionava por `button[aria-label="Remover item"]`, o que deixou de
    funcionar quando o rótulo passou a ser posicional. O hook de dados é o
    contrato entre o template e item_form_row.js.
    """
    assert 'data-remover-item' in _render()
