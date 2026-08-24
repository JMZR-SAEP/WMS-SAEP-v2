"""Resposta de erro do modal: fragment do corpo com status 422.

`components/modal.html` emite `hx-post` com
`hx-target="[data-modal-body='<id>']"` e `hx-swap="outerHTML"` sempre que recebe
`action_url` — que é o modo de todos os modais, menos o de confirmação de form
externo (`submit_form_id`), onde o `<dialog>` não emite nada.

Nesse modo, uma resposta **2xx** que não seja o 204 do PRG é trocada **dentro
da caixa do modal** — uma página completa ali produz app bar e navegação
empilhados no diálogo, com a URL inalterada e o conteúdo de fundo ainda
clicável. O 422 também é trocado, mas por opt-in explícito do `modal.js` em
`htmx:beforeSwap`, e é justamente por isso que ele serve de superfície de erro.

Camada de infraestrutura HTTP, como `apps.core.http`: renderiza template e
monta resposta. Não importa models nem services de domínio (ADR-0011). Fica
fora de `apps.core.presentation`, que é declaradamente independente de
Django/templates.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.forms import BaseForm, BaseFormSet
from django.utils.functional import Promise
from django.http import HttpResponse
from django.shortcuts import render


def render_modal_erro(
    request,
    *,
    modal_id: str,
    titulo: str,
    erro: str | Promise | BaseForm | BaseFormSet,
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

    O tipo é fechado nessas três formas porque `coletar_erros` (`core_tags.py`)
    despacha por `isinstance(str, Promise)` / `non_form_errors` / `errors` e **não tem
    `else`**: uma fonte que ela não reconhece é descartada em silêncio, e o 422
    volta com a caixa de erro vazia. `erro=exc` em vez de `erro=str(exc)` é o
    engano de uma letra que produz exatamente isso.

    `icon_variant` não tem default de severidade de propósito. Um default
    `'danger'` reclassificaria como perigo qualquer modal `info` ou `warning`
    que passasse por aqui; quem sabe a severidade é a tela que abriu o modal, e
    o 422 tem de devolver o mesmo modal, não um parente.

    Os parâmetros restantes espelham `components/modal.html` e
    `components/_modal_body.html` (de onde vem `acao_erro`), porque o fragment
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
        # `contexto_form` traz o que o `form_body_template` precisa, não o que
        # o modal já decidiu. Sobrescrever `id` daqui trocaria o
        # `data-modal-body` do fragment: o swap acontece, mas o corpo trocado
        # passa a responder por outro seletor, e o 422 seguinte erra o alvo.
        colisao = contexto_form.keys() & contexto.keys()
        if colisao:
            raise ImproperlyConfigured(
                f'contexto_form sobrescreve chave do modal: {sorted(colisao)}. '
                'Passe o valor pelo parâmetro nomeado correspondente.'
            )
        contexto.update(contexto_form)

    response = render(request, 'components/_modal_body.html', contexto)
    response.status_code = 422
    return response
