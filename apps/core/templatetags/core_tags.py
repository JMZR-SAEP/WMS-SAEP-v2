from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured
from django import template
from django.forms import BoundField
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from apps.core import quantidades

register = template.Library()


@register.filter
def minutos_totais(delta: object) -> int | None:
    """Converte um `timedelta` em minutos inteiros (piso), pra copy de prazo.

    Usado com `cooloff_timedelta` do django-axes, pra que a página de
    bloqueio de login nunca minta o prazo se `AXES_COOLOFF_TIME` mudar.

    Testa o tipo, não `is None`. No permalock (`AXES_COOLOFF_TIME = None`) o
    axes monta o contexto com `if cool_off:` e simplesmente não inclui a chave
    (`axes.helpers`); o Django resolve a variável ausente como
    `string_if_invalid`, que é `''` por padrão. O guarda anterior deixava essa
    string passar e estourava em `''.total_seconds()` — ou seja, a tela de
    bloqueio devolvia 500 exatamente na configuração que o comentário de
    `accounts/login_bloqueado.html` diz suportar com "mensagem sem prazo".

    Nenhum valor faz esta tela quebrar: quem a vê já está bloqueado e sem outra
    saída na interface.
    """
    if not isinstance(delta, timedelta):
        return None
    return int(delta.total_seconds() // 60)


ICONES_CATALOGO = frozenset(
    {
        'voltar',
        'lixeira',
        'remover',
        'spinner',
        'adicionar',
        'enviar',
        'copiar',
        'editar',
        'confirmar',
        'confirmar_check',
        'estornar',
    }
)


@register.simple_tag
def icon(name: str, size: int = 20, **kwargs: str) -> str:
    """Renderiza um ícone do catálogo vendorizado (aria-hidden sempre)."""
    if not isinstance(name, str) or name not in ICONES_CATALOGO:
        raise ImproperlyConfigured(
            f'Ícone "{name}" não está no catálogo (components/icons/). '
            f'Nomes válidos: {sorted(ICONES_CATALOGO)}.'
        )
    css_class = kwargs.get('class', '')
    return mark_safe(
        render_to_string(
            f'components/icons/{name}.svg',
            {'size': size, 'class': css_class},
        )
    )


@register.filter
def formatar_quantidade(qtd, unidade: str) -> str:
    """Formata quantidade conforme a unidade de medida do material.

    - 'un' → inteiro
    - 'kg', 'l', 'm' → 1 casa decimal
    - demais → strip trailing zeros (casas significativas)

    A regra em si vive em `apps.core.quantidades`, junto do `step` do campo e do
    valor inicial que o preenche: são três faces da mesma política, e views
    também precisam dela — templatetag não é lugar de onde uma view importa.
    """
    return quantidades.formatar(qtd, unidade)


_FORMA_BOTAO = 'inline-flex items-center justify-center min-h-11 rounded-md font-medium'
_FORMA_LINK = 'inline-flex items-center rounded font-medium'
_FOCO_BOTAO = (
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1'
)
# `aria-disabled` acompanha `disabled` porque a ação de workflow bloqueada com
# motivo declarado usa o primeiro para continuar focável (ver button.html).
_ESTADOS_BOTAO = (
    'disabled:cursor-not-allowed disabled:opacity-60 '
    'aria-disabled:cursor-not-allowed aria-disabled:opacity-60'
)
_VARIANTES_BOTAO: dict[str, str] = {
    'primary': (
        'bg-primary text-text-on-primary hover:bg-primary-hover '
        'active:bg-primary-active focus-visible:ring-border-focus'
    ),
    'secondary': (
        'bg-surface text-text-secondary border border-border-control '
        'hover:bg-bg-page hover:text-text-primary focus-visible:ring-border-focus'
    ),
    'neutral': (
        'bg-text-secondary text-text-on-primary hover:bg-text-primary '
        'focus-visible:ring-text-tertiary'
    ),
    'danger': (
        'bg-danger text-text-on-primary hover:bg-danger-hover '
        'active:bg-danger-active focus-visible:ring-danger-accent'
    ),
    'danger-outline': (
        'bg-surface text-danger-text border border-danger-border-strong '
        'hover:bg-danger-subtle focus-visible:ring-danger-accent'
    ),
    'warning-outline': (
        'bg-surface text-warning-text-strong border border-warning-border-strong '
        'hover:bg-warning-muted focus-visible:ring-warning'
    ),
    'return-outline': (
        'bg-surface text-return-text-strong border border-return-border '
        'hover:bg-return-subtle focus-visible:ring-return'
    ),
    'ghost': (
        'bg-transparent text-text-secondary hover:bg-bg-subtle '
        'focus-visible:ring-border-focus'
    ),
    'link': (
        'bg-transparent text-primary-text hover:underline focus-visible:ring-border-focus'
    ),
}
_TAMANHOS_BOTAO = {'sm': 'px-3 py-2 text-xs', 'md': 'px-3 py-2 text-sm'}


@register.simple_tag
def classes_botao(
    *,
    variant: str = '',
    size: str = '',
    tag: str = 'button',
    full_width_mobile: Any = False,
    extra: Any = '',
) -> str:
    """Monta a classe de components/button.html — uma vez, para os dois ramos.

    A expressão de nove variantes vivia duplicada por inteiro entre o ramo `<a>`
    e o ramo `<button>` do template, ~900 caracteres cada. As duas cópias já
    tinham divergido: `cursor-pointer` e os estados `disabled:` existiam só na
    segunda. Toda variante nova precisava ser escrita em dois lugares, e nada
    comparava os dois.

    A diferença real entre os ramos é pequena e está explícita aqui: um link não
    tem estado desabilitado nem cursor de ponteiro a declarar.

    `variant` e `size` chegam vazios quando o chamador não os passa (o Django
    resolve variável ausente como string vazia), e caem no default.
    """
    forma = _FORMA_LINK if variant == 'link' else _FORMA_BOTAO
    partes = [forma]
    if tag == 'button':
        partes.append('cursor-pointer')
    partes.append(_FOCO_BOTAO)
    if tag == 'button':
        partes.append(_ESTADOS_BOTAO)
    partes.append(
        _VARIANTES_BOTAO.get(variant or 'primary', _VARIANTES_BOTAO['primary'])
    )
    partes.append(_TAMANHOS_BOTAO.get(size or 'md', _TAMANHOS_BOTAO['md']))
    if full_width_mobile:
        partes.append('w-full sm:w-auto')
    if extra:
        partes.append(str(extra))
    return ' '.join(partes)


@register.simple_tag
def validar_contrato_modal(action_url, submit_form_id):
    """Exige exatamente um entre action_url e submit_form_id em components/modal.html."""
    if bool(action_url) == bool(submit_form_id):
        raise ImproperlyConfigured(
            'components/modal.html exige exatamente um entre action_url e '
            'submit_form_id (recebido: '
            f'action_url={action_url!r}, submit_form_id={submit_form_id!r}).'
        )
    return ''


@register.simple_tag
def renderizar_campo_com_aria(
    field: BoundField,
    tem_ajuda: object = False,
    tem_erro: object = False,
    attrs_extra: Mapping[str, Any] | None = None,
    describedby_extra: str = '',
) -> SafeString:
    """Renderiza o BoundField injetando aria-invalid/aria-describedby.

    Único mecanismo do projeto pra passar attrs extras a `{{ field }}` —
    Django não permite isso via linguagem de template pura (chamada de
    método sem argumentos). Usado por components/form_field.html. `field.as_widget`
    mescla os attrs recebidos com os automáticos do widget (`required`,
    `class`, `placeholder` etc. definidos em forms.py não são removidos) —
    mas *substitui* attrs com a mesma chave, então um `aria-describedby` já
    definido no widget é preservado explicitamente aqui (concatenado antes
    dos ids de ajuda/erro) em vez de ser sobrescrito.

    `attrs_extra` existe para o que só a linha sabe: numa linha de formset, o
    `max` vem da quantidade autorizada daquele item e o `x-model` amarra o campo
    ao escopo Alpine daquela linha. Sem isso, a tela é empurrada a escrever o
    `<input>` na mão e perde justamente a fiação ARIA que este tag entrega.

    `describedby_extra` acrescenta ids de texto de apoio que vivem fora do
    componente (ex. um aviso condicional renderizado pela tela).
    """
    attrs: dict[str, Any] = dict(attrs_extra or {})
    describedby_ids: list[str] = []
    describedby_existente = field.field.widget.attrs.get('aria-describedby')
    if describedby_existente:
        describedby_ids.append(str(describedby_existente))
    if describedby_extra:
        describedby_ids.append(str(describedby_extra))
    if tem_ajuda:
        describedby_ids.append(f'{field.id_for_label}-ajuda')
    if tem_erro:
        describedby_ids.append(f'{field.id_for_label}-erro')
        attrs['aria-invalid'] = 'true'
    if describedby_ids:
        attrs['aria-describedby'] = ' '.join(describedby_ids)
    return field.as_widget(attrs=attrs)


@register.simple_tag
def attrs_widget(**kwargs: Any) -> dict[str, Any]:
    """Monta o dict de `attrs_extra` de components/form_field.html.

    A linguagem de template não constrói dicionários, e sem isso uma linha de
    formset não tem como passar ao componente o que só ela sabe. Convenção de
    nomes: `x_bind_required` vira `x-bind:required` (binding Alpine), qualquer
    outro underscore vira hífen (`aria_label` -> `aria-label`).
    """
    convertidos: dict[str, Any] = {}
    for chave, valor in kwargs.items():
        if chave.startswith('x_bind_'):
            atributo = chave.removeprefix('x_bind_').replace('_', '-')
            convertidos[f'x-bind:{atributo}'] = valor
        else:
            convertidos[chave.replace('_', '-')] = valor
    return convertidos


@register.filter
def step_por_unidade(unidade: str) -> str:
    """Passo do <input type="number"> conforme a unidade de medida.

    Espelha a política de precisão de `formatar_quantidade`: se a tela formata
    'un' como inteiro, o campo não pode aceitar 0,001 unidade. Antes as duas
    funções eram mantidas lado a lado na esperança de não divergirem; hoje leem
    a mesma tabela em `apps.core.quantidades`, e divergir deixou de ser possível.
    """
    return quantidades.step(unidade)


@register.simple_tag
def coletar_erros(*fontes: Any) -> list[dict[str, str]]:
    """Achata Forms e FormSets numa lista para `components/error_summary.html`.

    Cada item é `{'id', 'rotulo', 'mensagem'}`; `id` é o `id_for_label` do campo,
    para o sumário poder linkar direto ao controle inválido. Erros que não
    pertencem a um campo (`__all__`, `non_form_errors`) entram sem `id` e o
    sumário os renderiza como texto.

    Apresentação pura: não conhece domínio nem decide o que é erro — só lê o que
    o Form já validou.
    """
    coletados: list[dict[str, str]] = []

    def _do_form(form: Any) -> None:
        for campo, mensagens in form.errors.items():
            if campo == NON_FIELD_ERRORS:
                for mensagem in mensagens:
                    coletados.append({'id': '', 'rotulo': '', 'mensagem': mensagem})
                continue
            bound = form[campo]
            for mensagem in mensagens:
                coletados.append(
                    {
                        'id': bound.id_for_label or '',
                        'rotulo': str(bound.label or campo),
                        'mensagem': mensagem,
                    }
                )

    for fonte in fontes:
        if fonte is None:
            continue
        if hasattr(fonte, 'non_form_errors'):
            for mensagem in fonte.non_form_errors():
                coletados.append({'id': '', 'rotulo': '', 'mensagem': mensagem})
            for form in fonte.forms:
                _do_form(form)
        elif hasattr(fonte, 'errors'):
            _do_form(fonte)

    return coletados


NAVEGACAO: list[dict[str, Any]] = [
    {
        'titulo': 'Navegação',
        'aria_label': 'Navegação',
        'itens': [
            {
                'url_name': 'core:home',
                'rotulo': 'Início',
                'icone': 'inicio',
                'flag': None,
            },
        ],
    },
    {
        'titulo': 'Requisições',
        'aria_label': 'Requisições',
        'itens': [
            {
                'url_name': 'requisicoes:nova_requisicao',
                'rotulo': 'Nova requisição',
                'icone': 'criar',
                'flag': None,
            },
            {
                'url_name': 'requisicoes:minhas',
                'rotulo': 'Minhas requisições',
                'icone': 'lista',
                'flag': None,
            },
            {
                'url_name': 'requisicoes:autorizacoes',
                'rotulo': 'Fila de autorizações',
                'icone': 'autorizacao',
                'flag': 'pode_ver_fila_autorizacao',
            },
            {
                'url_name': 'requisicoes:historico',
                'rotulo': 'Histórico de requisições',
                'icone': 'historico',
                'flag': 'pode_consultar_historico_requisicoes',
            },
        ],
    },
    {
        'titulo': 'Almoxarifado',
        'aria_label': 'Almoxarifado',
        'itens': [
            {
                'url_name': 'requisicoes:atendimentos',
                'rotulo': 'Atendimento',
                'icone': 'atendimento',
                'flag': 'pode_ver_fila_atendimento',
            },
            {
                'url_name': 'estoque:listar_saidas_excepcionais',
                'rotulo': 'Saídas excepcionais',
                'icone': 'saida',
                'flag': 'pode_consultar_saidas_excepcionais',
            },
            {
                'url_name': 'estoque:lista_materiais',
                'rotulo': 'Catálogo de materiais',
                'icone': 'catalogo',
                'flag': 'pode_consultar_catalogo_estoque',
            },
            {
                'url_name': 'estoque:historico_movimentacoes',
                'rotulo': 'Movimentações',
                'icone': 'movimentacao',
                'flag': 'pode_consultar_movimentacoes_estoque',
            },
            {
                'url_name': 'estoque:preview_importacao_scpi',
                'rotulo': 'Importar SCPI',
                'icone': 'importar',
                'flag': 'pode_visualizar_preview_scpi',
                'url_names_ativos': [
                    'estoque:preview_importacao_scpi',
                    'requisicoes:confirmar_importacao_scpi',
                    'estoque:sucesso_importacao_scpi',
                ],
            },
            {
                'url_name': 'estoque:historico_importacoes_scpi',
                'rotulo': 'Histórico de importações SCPI',
                'icone': 'historico',
                'flag': 'pode_consultar_historico_scpi',
            },
        ],
    },
]

ICONES: dict[str, str] = {
    'inicio': 'M12 3 2 11h3v8h6v-6h2v6h6v-8h3L12 3z',
    'criar': 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
    'lista': 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
    'autorizacao': (
        'M12 2 4 5v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V5l-8-3zm-1 14'
        '-4-4 1.41-1.41L11 13.17l5.59-5.59L18 9l-7 7z'
    ),
    'historico': 'M13 3a9 9 0 1 0 9 9h-2a7 7 0 1 1-7-7v4l5-5-5-5v4z',
    'atendimento': (
        'M20 8h-3V6c0-1.1-.9-2-2-2H9c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v9c0 1.1'
        '.9 2 2 2h16c1.1 0 2-.9 2-2v-9c0-1.1-.9-2-2-2zM9 6h6v2H9V6zm11 13H4v-2h16'
        'v2zm0-4H4v-5h3v2h2v-2h6v2h2v-2h3v5z'
    ),
    'saida': (
        'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2'
        '-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l7.59-7.59L21 8l-9 9z'
    ),
    'catalogo': (
        'M20 3H4v2h16V3zm1 5H3l1 13h16l1-13zm-5 7h-3v3h-2v-3H8v-2h3V10h2v3h3v2z'
    ),
    'movimentacao': (
        'M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7'
        'v2zM7 7v2h14V7H7z'
    ),
    'importar': 'M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z',
}


@register.simple_tag(takes_context=True)
def secoes_navegacao(context: Any) -> list[dict[str, Any]]:
    """Devolve as seções de nav visíveis, lidas de NAVEGACAO/ICONES.

    Filtra itens pela flag de permissão já presente no contexto (sem
    reimplementar policy) e descarta seções sem nenhum item visível.
    Constrói dicts/listas novos a cada chamada — nunca muta NAVEGACAO/ICONES.
    """
    secoes: list[dict[str, Any]] = []
    for secao in NAVEGACAO:
        itens: list[dict[str, Any]] = []
        for item in secao['itens']:
            flag = item.get('flag')
            if flag is not None and not context.get(flag):
                continue
            itens.append(
                {
                    'url_name': item['url_name'],
                    'rotulo': item['rotulo'],
                    'icone_path': ICONES[item['icone']],
                    'url_names_ativos': list(
                        item.get('url_names_ativos', [item['url_name']])
                    ),
                }
            )
        if itens:
            secoes.append(
                {
                    'titulo': secao['titulo'],
                    'aria_label': secao['aria_label'],
                    'itens': itens,
                }
            )
    return secoes
