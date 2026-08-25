from django import template

from apps.estoque.presentation import MODAL_COPY

register = template.Library()


@register.simple_tag
def modal_copy(nome):
    """Copy (`titulo`/`descricao`/`confirm_label`/`icon_variant`) de um modal estático.

    Fonte única com o re-render 422 (#135): mesmo dicionário dos dois lados,
    para que o modal reaberto com erro não possa dizer algo diferente do que
    disse ao abrir.
    """
    return MODAL_COPY[nome]
