from django import template

from apps.requisicoes.presentation import MODAL_COPY
from apps.requisicoes.presentation import cancelamento_copy as _cancelamento_copy

register = template.Library()


@register.simple_tag
def cancelamento_copy(info, estado):
    """Lookup de copy do modal de cancelamento por (variante, estado) — presentation-only.

    `info` é `CancelamentoInfo | None`; `estado` é `requisicao.estado`. A fonte
    é `apps.requisicoes.presentation` (#135) — mesmo dicionário que o re-render
    422 usa via `render_modal_erro`; este tag só expõe ao template.
    """
    return _cancelamento_copy(info, estado)


@register.simple_tag
def modal_copy(nome):
    """Copy (`titulo`/`descricao`/`confirm_label`/`icon_variant`) de um modal estático.

    Fonte única com o re-render 422 (#135): mesmo dicionário dos dois lados,
    para que o modal reaberto com erro não possa dizer algo diferente do que
    disse ao abrir.
    """
    return MODAL_COPY[nome]


@register.filter
def get_choice_label(field, value):
    """Retorna o label de uma choice pelo value (para restaurar autocomplete)."""
    if not value:
        return ''
    str_value = str(value)
    for opt_value, opt_label in field.field.choices:
        if str(opt_value) == str_value:
            return opt_label
    return ''


@register.filter
def get_item(dictionary, key):
    """Retorna dictionary[key]; compatível com chaves string e int."""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(str(key))
