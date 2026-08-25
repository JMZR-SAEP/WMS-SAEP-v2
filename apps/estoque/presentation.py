"""Copy de apresentação dos modais de estoque — fonte única (#135).

Título, descrição e rótulos de cada modal vivem aqui uma vez só. O template e
a view — no re-render 422 via `apps.core.modal.render_modal_erro` — lêem o
mesmo dicionário, para que o modal reaberto com erro não possa dizer algo
diferente do que disse ao abrir.
"""

from __future__ import annotations

MODAL_COPY: dict[str, dict[str, str]] = {
    'estornar_saida': {
        'titulo': 'Estornar saída excepcional',
        'descricao': (
            'Esta ação é irreversível. Todos os itens serão devolvidos ao '
            'saldo físico do estoque.'
        ),
        'confirm_label': 'Confirmar estorno',
    },
    'confirmar_importacao_scpi': {
        'titulo': 'Confirmar importação do SCPI?',
        'descricao': 'A gravação não pode ser desfeita.',
        'confirm_label': 'Confirmar importação',
        'icon_variant': 'warning',
    },
}
