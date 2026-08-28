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
        'descricao': ('Todos os itens serão devolvidos ao saldo físico do estoque.'),
        # Separada da `descricao` (#138): a frase de irreversibilidade abria a
        # descrição, em `text-text-secondary`, e o corpo do modal a renderiza
        # com ênfase. Ver `consequencia` em `components/_modal_body.html`.
        'consequencia': 'Esta ação é irreversível.',
        'confirm_label': 'Confirmar estorno',
        # 'return', não 'danger': o estorno é reversão operacional, e a Regra da
        # Reversão Não é Erro reserva o vermelho para negação, falha e
        # divergência. O estado resultante já saía em teal — o bloco "Dados do
        # estorno" de `detalhe_saida_excepcional.html` usa `text-return-*` — e a
        # ação que o produz saía em vermelho: a mesma operação com dois sistemas
        # de cor na mesma tela. O estorno de requisição fez este caminho na #136;
        # a saída excepcional é a outra reversão e ficou para trás.
        'icon_variant': 'return',
    },
    'confirmar_importacao_scpi': {
        'titulo': 'Confirmar importação do SCPI?',
        # A descrição manda conferir; a consequência diz que não há volta. Antes
        # as duas eram a mesma frase, e ela era a mais apagada do modal: as três
        # contagens logo abaixo saíam em `text-base font-semibold` (#138).
        'descricao': 'Confira os números abaixo antes de gravar.',
        'consequencia': 'A gravação não pode ser desfeita.',
        'confirm_label': 'Confirmar importação',
        # 'danger', não 'warning' (#136): é a única escrita irreversível
        # declarada do sistema — grava direto, sem passar por aprovação humana
        # depois.
        'icon_variant': 'danger',
    },
}


def registro_saida_excepcional(saida) -> dict[str, str]:
    """Linha de identidade da saída no cabeçalho do modal de estorno (#138).

    `identificador` é o número público, com "Sem número" no lugar do `__str__`
    do model (`Saída #<pk>`) pela mesma regra que vale na requisição —
    `docs/CONVENTIONS.md` §Identificadores na interface: PK interno não vaza para UI.
    O cabeçalho da própria tela já resolve a ausência como "—"; aqui a linha é
    lida fora de contexto de tabela, então diz a palavra.

    `contexto` é o estoque e quem registrou: o estorno devolve todos os itens
    ao saldo físico, e as duas perguntas que a pessoa faz antes de confirmar
    são "de qual estoque?" e "de quem é este documento?". Ambas as relações
    vêm no `select_related` de `buscar_detalhe_saida_excepcional`.
    """
    return {
        'rotulo': 'Saída excepcional',
        'identificador': saida.numero_publico or 'Sem número',
        'contexto': f'{saida.estoque.nome} · registrada por {saida.registrado_por.nome}',
    }


def registro_arquivo_scpi(nome_arquivo: str) -> dict[str, str]:
    """Linha de identidade do modal de confirmação da importação SCPI (#138).

    Aqui o registro não é um documento do sistema — é o arquivo que a pessoa
    acabou de subir, e confirmar o arquivo errado grava saldo errado no estoque
    inteiro. Sem `contexto`: as contagens do preview já são o corpo do modal
    (`_modal_corpo_confirmar_importacao.html`), e repeti-las na linha de
    identidade seria a segunda grafia do mesmo número.
    """
    return {
        'rotulo': 'Arquivo',
        'identificador': nome_arquivo,
        'contexto': '',
    }
