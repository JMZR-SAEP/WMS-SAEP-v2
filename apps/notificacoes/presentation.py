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
    # "devolvida para ajustes", não "recusada": desde a issue #170 a recusa é
    # uma variante de retornar para rascunho, não mais um encerramento
    # definitivo — o texto não pode continuar prometendo o que não acontece.
    TipoNotificacao.RECUSA: 'Sua requisição foi devolvida para ajustes',
    TipoNotificacao.ATENDIMENTO: 'Sua requisição foi atendida',
    TipoNotificacao.SEPARACAO_RETIRADA: 'Sua requisição foi separada para retirada',
    # Não "Aguardava sua autorização" (issue #197): essa metade só aparece
    # quando `pede_acao` já é falso, ou seja, o pedido de autorização não
    # cabe mais — mas o que aconteceu depois (autorizada por outro caminho,
    # devolvida, cancelada) este módulo não sabe, e "aguardava" lido ao lado
    # do estado atual soava como um processo ainda em curso. "Foi enviada
    # para autorização" é o único fato que este tipo sempre garante, verdadeiro
    # qualquer que tenha sido o desfecho — e lê como evento encerrado.
    TipoNotificacao.ENVIO_AUTORIZACAO: 'Sua requisição foi enviada para autorização',
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
    """Evento + estado atual como uma frase só, no formato
    `Sua requisição foi enviada para autorização — atendida`.

    `estado_label` vem de `get_estado_display()` da requisição referenciada e é
    vazio quando não há requisição para consultar (aviso sem link, id órfão) —
    aí o título é só o evento, sem afirmar estado nenhum. O travessão substitui
    o `·` (issue #197): duas frases separadas por um marcador de lista liam
    como dois rótulos desconexos, e não como o mesmo registro contando o que
    aconteceu e como as coisas estão agora. A segunda metade entra em
    minúscula porque continua a primeira, e não recomeça um rótulo novo.
    """
    evento = evento_da_notificacao(tipo, pede_acao=pede_acao) or rotulo_do_tipo
    if not estado_label:
        return evento
    estado_em_minuscula = estado_label[:1].lower() + estado_label[1:]
    return f'{evento} — {estado_em_minuscula}'
