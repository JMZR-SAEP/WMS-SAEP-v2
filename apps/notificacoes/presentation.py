"""Tradução de tipo de notificação para desfecho legível.

O cartão dizia `Autorização`, `Recusa`, `Atendimento` — o **tipo do evento**,
nunca o desfecho. "Autorização" não diz se foi autorizada; é a categoria do
aviso, não a notícia. Quem abre esta tela abriu para saber o que aconteceu com
o pedido dela.

Mora aqui, e não no template, pela mesma razão de `estoque/presentation.py`: é
copy de domínio traduzida uma vez, testável sozinha, e um `{% if %}` de seis
ramos dentro do `<li>` seria a segunda fonte da mesma frase.
"""

from apps.notificacoes.models import TipoNotificacao


#: Chave `str` e não `TipoNotificacao`: quem consulta é a view, com
#: `notificacao.tipo` — que o Django devolve como a string crua do banco, não
#: como membro do enum. Anotar o mapa com o enum faria o `mypy` recusar
#: exatamente a chamada real.
DESFECHO_POR_TIPO: dict[str, str] = {
    TipoNotificacao.AUTORIZACAO: 'Sua requisição foi autorizada',
    TipoNotificacao.RECUSA: 'Sua requisição foi recusada',
    TipoNotificacao.ATENDIMENTO: 'Sua requisição foi atendida',
    TipoNotificacao.SEPARACAO_RETIRADA: 'Sua requisição está pronta para retirada',
    TipoNotificacao.ENVIO_AUTORIZACAO: 'Uma requisição aguarda sua autorização',
    TipoNotificacao.DIVERGENCIA_ESTOQUE: 'Divergência de estoque em uma requisição sua',
}


def desfecho_da_notificacao(tipo: str) -> str:
    """Frase do desfecho, ou string vazia quando o tipo é desconhecido.

    Vazia, e não um texto inventado: quem chama cai de volta no
    `get_tipo_display` do próprio model, que é a fonte do rótulo. Um aviso sem
    título seria pior que um aviso genérico, e o caso só existe se alguém
    adicionar um `TipoNotificacao` sem passar por aqui.
    """
    return DESFECHO_POR_TIPO.get(tipo, '')
