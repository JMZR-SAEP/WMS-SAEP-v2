"""Contrato HTTP das URLs que aparecem como `action_url` de um modal.

`components/modal.html` sempre emite `hx-post` com
`hx-target="[data-modal-body='<id>']"` e `hx-swap="outerHTML"`. Isso significa
que **qualquer** resposta que não seja 204 + `HX-Redirect` ou 422 + fragment do
corpo é injetada dentro da caixa do modal — uma página completa ali produz app
bar e navegação empilhados no diálogo, com a URL inalterada e o conteúdo de
fundo ainda clicável.

Este módulo é a metade estática do guarda: descobre quais rotas estão nessa
posição hoje e oferece a asserção que os testes HTTP de cada app usam. A metade
dinâmica vive em `apps/<app>/tests/test_contrato_modal_http.py`, onde as
fixtures do app existem.

Não é coletado como teste (nome sem prefixo `test_`), como `marcacao.py`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

RAIZ = Path(__file__).resolve().parents[3]


class CenarioModal(NamedTuple):
    """O que uma rota de modal precisa para ser exercitada nos três eixos.

    A construtora de cada rota devolve isto. `ler_estado` é o campo que o eixo
    anônimo consome: função sem argumentos que relê do banco e devolve algo
    comparável por `==` — tipicamente uma tupla dos campos que a rota mutaria.
    Quem sabe o que cada rota escreve é a construtora, então é ela que decide o
    recorte; o teste só chama antes e depois e compara.

    `ler_estado` **nunca pode presumir que a linha sobreviveu**: o descarte de
    rascunho sem número público apaga a `Requisicao`
    (`services/cancelamento.py`), e um `objects.get(pk=…)` estouraria
    `DoesNotExist` em vez de comparar. A forma é
    `filter(pk=…).values_list(…).first()`, que devolve `None` quando o registro
    deixou de existir.
    """

    url: str
    payload: dict[str, Any]
    destino_esperado: str | None
    ler_estado: Callable[[], Any]
    ator: Any


COMPONENTE_MODAL = 'components/modal.html'
RELAY_CONFIRMACAO = 'requisicoes/partials/_confirmacao_acao.html'

# Rota → app dono do teste HTTP. Fechado de propósito: um modal novo apontando
# para rota fora desta tabela quebra `test_contrato_modal.py`, e uma rota
# registrada sem cenário quebra o teste HTTP do app. As duas pontas juntas são
# o que faz um modal novo não conseguir nascer fora do contrato.
REGISTRO_CONTRATO_MODAL: dict[str, str] = {
    'requisicoes:autorizar': 'requisicoes',
    'requisicoes:cancelar': 'requisicoes',
    'requisicoes:confirmar_importacao_scpi': 'requisicoes',
    'requisicoes:enviar_rascunho': 'requisicoes',
    'requisicoes:estornar': 'requisicoes',
    'requisicoes:recusar': 'requisicoes',
    'requisicoes:registrar_devolucao': 'requisicoes',
    'requisicoes:retornar_rascunho': 'requisicoes',
    'requisicoes:separar_retirada': 'requisicoes',
    'estoque:estornar_saida_excepcional': 'estoque',
}

# `{% url 'app:nome' ... as variavel %}` — a única forma como uma `action_url`
# nasce hoje, e o que torna a varredura possível.
_URL_COMO = re.compile(
    r"""\{%\s*url\s+['"](?P<rota>[\w.:-]+)['"][^%]*?\bas\s+(?P<var>\w+)\s*%\}"""
)
_INCLUDE = re.compile(
    r'\{%\s*include\s+["\'](?P<alvo>[^"\']+)["\'](?P<args>.*?)%\}', re.S
)
_ACTION_URL = re.compile(r'\baction_url\s*=\s*(?P<valor>\S+)')
_SUBMIT_FORM_ID = re.compile(r'\bsubmit_form_id\s*=')
_COMENTARIO = re.compile(r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}', re.S)


def _templates() -> list[Path]:
    return sorted(RAIZ.glob('apps/*/templates/**/*.html'))


def rotas_de_modal() -> set[str]:
    """Nomes de rota usados como `action_url` de modal em todos os templates.

    Enumera **nomes de rota**, não URLs concretas: `requisicoes:cancelar`
    aparece em dois pontos de `detalhe.html` com `pk` diferente por requisição,
    e o nome é a unidade que identifica a view responsável pela resposta — que é
    o que o contrato governa. A URL concreta reaparece nos testes HTTP, onde
    cada cenário faz o `reverse()` com o objeto que criou.
    """
    rotas: set[str] = set()
    for caminho in _templates():
        # `_confirmacao_acao.html` é ignorado como origem: lá `action_url` é
        # repasse (`action_url=action_url`), e a origem real é quem o inclui.
        if caminho.as_posix().endswith(RELAY_CONFIRMACAO):
            continue
        texto = caminho.read_text(encoding='utf-8')
        rotas |= rotas_do_texto(texto, origem=str(caminho.relative_to(RAIZ)))
    return rotas


def rotas_do_texto(texto: str, *, origem: str) -> set[str]:
    """Rotas de `action_url` de modal num único template.

    Separada de `rotas_de_modal` para que os modos de falha da varredura sejam
    testáveis sem escrever template no disco. Um guarda cujo caminho de recusa
    nunca roda é um guarda que não se sabe se recusa.
    """
    # `{% comment %}` sai antes de tudo: o próprio `modal.html` documenta o uso
    # do componente com um `{% include %}` de exemplo, e um exemplo de
    # documentação não é um ponto de chamada. Sem esta linha a varredura
    # reprovaria o componente por causa da própria bula.
    texto = _COMENTARIO.sub('', texto)
    variaveis = {
        encontro.group('var'): encontro.group('rota')
        for encontro in _URL_COMO.finditer(texto)
    }
    rotas: set[str] = set()
    for include in _INCLUDE.finditer(texto):
        if include.group('alvo') not in (COMPONENTE_MODAL, RELAY_CONFIRMACAO):
            continue
        args = include.group('args')
        achado = _ACTION_URL.search(args)
        if achado is None:
            # Modo "confirmação de form externo": o <dialog> não emite `hx-post`
            # nenhum, então fica fora do contrato por construção.
            if _SUBMIT_FORM_ID.search(args):
                continue
            raise AssertionError(
                f'{origem}: include de {include.group("alvo")} sem action_url nem '
                'submit_form_id — validar_contrato_modal exige exatamente um dos dois.'
            )
        valor = achado.group('valor')
        rota = variaveis.get(valor)
        if rota is None:
            raise AssertionError(
                f'{origem}: action_url={valor} não vem de um '
                f"{{% url 'app:nome' ... as {valor} %}} no mesmo template. URL "
                'literal deixa esta varredura cega — e é assim que um modal '
                'escaparia do contrato HTTP sem ninguém notar.'
            )
        rotas.add(rota)
    return rotas


def assert_contrato_modal(resposta, *, destino_esperado: str | None = None) -> None:
    """Assere que a resposta cabe dentro da caixa do modal.

    Só duas formas cabem: 204 + `HX-Redirect` (o PRG do projeto, ver
    `apps/core/http.py`) ou 422 + fragment com `[data-modal-body]`. 200 de
    página inteira e 302 são as duas que a issue #130 encontrou em produção.

    `destino_esperado` é obrigatório sempre que o cenário puder terminar em 204:
    aceitar qualquer `HX-Redirect` deixaria passar cabeçalho vazio e rota
    errada, e a segunda é o sintoma que esta issue trata — a pessoa termina numa
    tela que não responde se gravou. Com `None`, o cenário tem de terminar em
    422.
    """
    status = resposta.status_code
    if status == 204:
        assert destino_esperado is not None, (
            'Cenário declarado como só-erro respondeu 204. Ou o cenário deixou '
            'de exercitar o ramo de erro, ou falta declarar destino_esperado.'
        )
        assert resposta.get('HX-Redirect') == destino_esperado, (
            f'204 com HX-Redirect={resposta.get("HX-Redirect")!r}, '
            f'esperado {destino_esperado!r}.'
        )
        return

    assert status == 422, (
        f'Resposta {status} a um POST HTMX de modal. O corpo desta resposta vai '
        f'ser injetado dentro de [data-modal-body] pelo hx-swap="outerHTML" do '
        f'componente — só 204+HX-Redirect ou 422+fragment cabem ali.'
    )
    assert b'data-modal-body' in resposta.content, (
        '422 sem [data-modal-body] no corpo: o swap trocaria o corpo do modal '
        'por um fragment que não é um corpo de modal.'
    )


def assert_fallback_sem_htmx(resposta) -> None:
    """Assere o que é uniforme no fallback sem HTMX: nunca 204, nunca HX-Redirect.

    O contrato positivo não é uniforme entre as rotas — umas redirecionam,
    outras renderizam página de erro, e isso é decisão de cada tela. Uma
    asserção genérica que aceitasse os dois casos aceitaria quase tudo.

    O que é uniforme é o negativo: um cliente sem JS não age sobre nenhum dos
    dois — 204 deixa a página parada e o cabeçalho é lido por ninguém. É a
    regressão que uma view ganharia ao trocar o `if request.htmx:` por um
    `htmx_redirect()` incondicional.
    """
    assert resposta.status_code != 204, (
        'Resposta 204 a um POST sem HTMX: um cliente sem JS fica com a página '
        'parada, sem sinal de que a ação aconteceu.'
    )
    assert 'HX-Redirect' not in resposta, (
        'HX-Redirect numa resposta sem HTMX: o cabeçalho não é lido por '
        'ninguém, e o redirecionamento simplesmente não acontece.'
    )
