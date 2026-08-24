"""Resposta de erro do modal: fragment do corpo com status 422.

`components/modal.html` sempre emite `hx-post` com
`hx-target="[data-modal-body='<id>']"` e `hx-swap="outerHTML"`. Toda resposta
que não seja 204 + `HX-Redirect` (sucesso) ou 422 + fragment do corpo (erro) é
injetada **dentro da caixa do modal** — e uma página completa ali produz app bar
e navegação empilhados no diálogo, com a URL inalterada e o conteúdo de fundo
ainda clicável.

Camada de infraestrutura HTTP, como `apps.core.http`: renderiza template e
monta resposta. Não importa models nem services de domínio (ADR-0011). Fica
fora de `apps.core.presentation`, que é declaradamente independente de
Django/templates.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpResponse
from django.shortcuts import render


def render_modal_erro(
    request,
    *,
    modal_id: str,
    titulo: str,
    erro: Any,
    descricao: str = '',
    form_body_template: str = '',
    confirm_label: str = 'Confirmar',
    confirm_variant: str = 'primary',
    cancel_label: str = 'Voltar',
    icon_variant: str | None = None,
    acao_erro: str = '',
    contexto_form: dict[str, Any] | None = None,
) -> HttpResponse:
    """Renderiza o corpo do modal com erro e devolve 422.

    O cliente HTMX troca apenas `[data-modal-body]`, então o diálogo continua
    aberto e no top layer — o que mantém a pergunta na tela em vez de trocá-la
    por uma imagem idêntica à do sucesso.

    `erro` aceita o que `{% erros_do_formulario %}` aceita como fonte: uma
    string que a view já traduziu de uma exceção de domínio, ou o próprio Form
    ligado. Passar o Form é o caminho para erro de formulário: o texto sai do
    Form, com âncora por campo, e não do `form.errors.as_text()`, cujo dump
    (`* justificativa\\n  * Este campo é obrigatório.`) chega à tela com o
    asterisco de formatação de log.

    `icon_variant` não tem default de severidade de propósito. Um default
    `'danger'` reclassificaria como perigo qualquer modal `info` ou `warning`
    que passasse por aqui; quem sabe a severidade é a tela que abriu o modal, e
    o 422 tem de devolver o mesmo modal, não um parente.

    Os parâmetros restantes espelham `components/modal.html`, porque o fragment
    devolvido tem de reconstruir o mesmo cabeçalho e o mesmo rodapé.
    """
    contexto: dict[str, Any] = {
        'id': modal_id,
        'titulo': titulo,
        'descricao': descricao,
        'erro': erro,
        'form_body_template': form_body_template,
        'confirm_label': confirm_label,
        'confirm_variant': confirm_variant,
        'cancel_label': cancel_label,
        'icon_variant': icon_variant,
    }
    if acao_erro:
        contexto['acao_erro'] = acao_erro
    if contexto_form:
        contexto.update(contexto_form)

    response = render(request, 'components/_modal_body.html', contexto)
    response.status_code = 422
    return response
