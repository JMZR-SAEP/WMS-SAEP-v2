"""Testes diretos de components/item_form_row.html (sem DB, sem view)."""

import re
from decimal import Decimal

from django.forms import BooleanField
from django.forms.formsets import DELETION_FIELD_NAME
from django.template.loader import render_to_string

from apps.requisicoes.forms import ItemRequisicaoFormSet


def _render(form_index=0, **extra):
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
            **extra,
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


def test_botao_remover_e_controlado_pela_contagem_reativa():
    """Regra é mínimo 1 item (issue #198): o servidor não sabe quantas linhas
    o formset terá no cliente, então quem decide se o botão aparece é
    `totalVisiveis`, contado em tempo de execução por `itensFormset`
    (`item_form_row.js`)."""
    html = _render()
    assert 'x-show="totalVisiveis > 1"' in html


def test_a_linha_nomeia_o_evento_que_o_autocomplete_emite():
    """O nome do evento é de quem instancia, não do componente genérico.

    `autocomplete` atende as buscas de beneficiário E de material. Enquanto ele
    emitia `material-selecionado` em toda seleção, um combobox de pessoa
    despachava um evento de material — e um listener acima receberia o objeto
    errado sem erro nenhum no console.
    """
    html = _render()
    assert "eventoSelecao: 'material-selecionado'" in html
    assert '@material-selecionado=' in html


def test_saldo_exibe_a_unidade_e_a_precisao_da_unidade():
    """Quantidade sem unidade não é informação.

    "Saldo disponível: 12,5" não diz se sobram 12 quilos ou 12 caixas, e a
    decisão logo abaixo é quanto pedir. `floatformat:"-3"` ainda escrevia três
    casas decimais para material contado em caixa.

    O painel de saldo não vive mais no componente global (issue #174): o
    componente só inclui o `saldo_slot_template` que a tela escolhe, e o
    partial de domínio (aqui, o de requisições) é quem lê `saldo_item` — o
    mesmo dict de antes, agora chegando por herança de contexto em vez de
    parâmetro do componente.
    """
    html = _render(
        saldo_item={
            'elegivel': True,
            'saldo_disponivel': Decimal('12.5'),
            'motivo': '',
            'unidade': 'kg',
        },
        saldo_slot_template='requisicoes/partials/_item_saldo_painel.html',
    )
    assert 'Saldo disponível: 12,5 kg' in html


def test_saldo_de_material_inelegivel_tambem_leva_unidade():
    html = _render(
        saldo_item={
            'elegivel': False,
            'saldo_disponivel': Decimal('0'),
            'motivo': 'Sem saldo disponível',
            'unidade': 'cx',
        },
        saldo_slot_template='requisicoes/partials/_item_saldo_painel.html',
    )
    assert 'saldo atual: 0 cx' in html


def test_sem_saldo_slot_template_a_linha_nao_mostra_painel_de_saldo():
    """O componente global não decide mais sozinho se mostra saldo (issue #174).

    Sem `saldo_slot_template`, a linha não sabe renderizar nada de saldo —
    nem o painel estático nem o reativo — porque deixou de conhecer
    `saldo_item`.
    """
    html = _render(
        saldo_item={
            'elegivel': False,
            'saldo_disponivel': Decimal('0'),
            'motivo': 'Sem saldo disponível',
            'unidade': 'cx',
        }
    )
    assert 'saldo atual' not in html
    assert 'Saldo disponível' not in html


def test_borda_alerta_liga_a_classe_de_destaque_ambar():
    """A borda âmbar é um flag de apresentação (`borda_alerta`), não mais uma
    leitura de `saldo_item.elegivel` dentro do componente global (issue #174)."""
    html = _render(borda_alerta=True)
    assert 'border-warning-border-strong' in html
    assert 'bg-warning-subtle/40' in html


def test_sem_borda_alerta_a_linha_usa_a_borda_neutra():
    html = _render()
    assert 'border-warning-border-strong' not in html
    assert 'border-border bg-surface' in html


def test_copy_dos_avisos_nao_vive_no_javascript():
    """Texto que a pessoa lê é conteúdo da tela, não do script.

    Em `.js` a frase escapa do `{% trans %}`, da revisão de copy e da chance de
    cada formulário dizer o que faz sentido nele — "ao menos um material" é a
    frase da requisição, não uma verdade sobre formsets.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    fonte = (raiz / 'apps/core/static/core/js/item_form_row.js').read_text()
    # Só literais de string; os comentários explicam o código e podem ter prosa.
    literais = re.findall(r"'([^'\n]*)'|`([^`\n]*)`", fonte)
    frases = [
        texto
        for par in literais
        for texto in par
        if texto and ' ' in texto and texto.rstrip().endswith('.')
    ]
    assert not frases, f'copy de interface hardcoded no JS: {frases}'


def test_templates_declaram_a_copy_dos_avisos():
    """O JS lê a copy do `data-*` da live region; sem ela, não anuncia nada."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    for caminho in (
        'apps/requisicoes/templates/requisicoes/rascunho_form.html',
        'apps/estoque/templates/estoque/nova_saida_excepcional.html',
    ):
        texto = (raiz / caminho).read_text()
        for atributo in (
            'data-aviso-minimo',
            'data-aviso-adicionado',
            'data-aviso-removido',
        ):
            assert atributo in texto, f'{caminho} não declara {atributo}'
