"""Título do cartão de notificação: o evento que aconteceu, mais o estado de hoje.

O cartão dizia `Autorização`, `Recusa`, `Atendimento` — o **tipo do evento**,
nunca o desfecho. Depois passou a dizer o desfecho, mas no presente do
indicativo: "Uma requisição aguarda sua autorização" continuava afirmando, em
2026, uma requisição autorizada em maio. O tipo é congelado na criação e o
usuário lê o título como afirmação sobre o presente (issue #175).

O título passa então a ter duas metades: o **evento**, no passado, que é o que a
notificação de fato registra, e o **estado atual** da requisição, que só o
domínio sabe. A segunda metade chega pronta de quem consultou — este módulo é
copy, não decide nada (ADR-0011).
"""

from apps.notificacoes.models import TipoNotificacao

#: Chave `str` e não `TipoNotificacao`: quem consulta é a view, com
#: `notificacao.tipo` — que o Django devolve como a string crua do banco, não
#: como membro do enum. Anotar o mapa com o enum faria o `mypy` recusar
#: exatamente a chamada real.
#:
#: Todas as frases estão no passado: é o registro do evento, e quem diz como as
#: coisas estão agora é a metade seguinte do título.
EVENTO_POR_TIPO: dict[str, str] = {
    TipoNotificacao.AUTORIZACAO: 'Sua requisição foi autorizada',
    TipoNotificacao.RECUSA: 'Sua requisição foi recusada',
    TipoNotificacao.ATENDIMENTO: 'Sua requisição foi atendida',
    TipoNotificacao.SEPARACAO_RETIRADA: 'Sua requisição foi separada para retirada',
    TipoNotificacao.ENVIO_AUTORIZACAO: 'Aguardava sua autorização',
    TipoNotificacao.DIVERGENCIA_ESTOQUE: 'Divergência de estoque em uma requisição sua',
}

#: Frase enquanto a chamada à ação do aviso **ainda se aplica** ao estado
#: corrente. Só tipo que convoca alguma operação aparece aqui: no presente do
#: indicativo o título é uma cobrança, e cobrar por trabalho já feito foi o
#: defeito que a #175 nomeia.
EVENTO_PENDENTE_POR_TIPO: dict[str, str] = {
    TipoNotificacao.ENVIO_AUTORIZACAO: 'Uma requisição aguarda sua autorização',
}


def evento_da_notificacao(tipo: str, *, pede_acao: bool = False) -> str:
    """Metade do evento, ou string vazia quando o tipo é desconhecido.

    Vazia, e não um texto inventado: quem chama cai de volta no
    `get_tipo_display` do próprio model, que é a fonte do rótulo. Um aviso sem
    título seria pior que um aviso genérico, e o caso só existe se alguém
    adicionar um `TipoNotificacao` sem passar por aqui.
    """
    if pede_acao and tipo in EVENTO_PENDENTE_POR_TIPO:
        return EVENTO_PENDENTE_POR_TIPO[tipo]
    return EVENTO_POR_TIPO.get(tipo, '')


def titulo_da_notificacao(
    *,
    tipo: str,
    rotulo_do_tipo: str,
    pede_acao: bool = False,
    estado_label: str = '',
) -> str:
    """Evento + estado atual, separados por `·`, no formato `Aguardava sua autorização · Atendida`.

    `estado_label` vem de `get_estado_display()` da requisição referenciada e é
    vazio quando não há requisição para consultar (aviso sem link, id órfão) —
    aí o título é só o evento, sem afirmar estado nenhum.
    """
    evento = evento_da_notificacao(tipo, pede_acao=pede_acao) or rotulo_do_tipo
    if not estado_label:
        return evento
    return f'{evento} · {estado_label}'
