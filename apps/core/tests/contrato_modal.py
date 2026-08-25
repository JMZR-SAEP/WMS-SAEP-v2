"""Contrato HTTP das URLs que aparecem como `action_url` de um modal.

`components/modal.html` emite `hx-post` com
`hx-target="[data-modal-body='<id>']"` e `hx-swap="outerHTML"` sempre que recebe
`action_url` — que é o modo de todos os modais, menos o de confirmação de form
externo (`submit_form_id`), onde o `<dialog>` não emite nada.

Nesse modo, uma resposta **2xx** que não seja o 204 do PRG é trocada dentro da
caixa do modal — uma página completa ali produz app bar e navegação empilhados
no diálogo, com a URL inalterada e o conteúdo de fundo ainda clicável. O 422 é
trocado por opt-in do `modal.js` (`htmx:beforeSwap`), e é por isso que ele serve
de superfície de erro.

Este módulo é a metade estática do guarda: descobre quais rotas estão nessa
posição hoje e oferece a asserção que os testes HTTP de cada app usam. A metade
dinâmica vive em `apps/<app>/tests/test_contrato_modal_http.py`, onde as
fixtures do app existem.

Não é coletado como teste (nome sem prefixo `test_`), como `marcacao.py`.

## O que este guarda NÃO cobre

**Sessão expirada com HTMX.** Um POST de modal sem sessão válida recebe 302 do
`@login_required` — sem `HX-Redirect`. O XHR segue o 302 sozinho, recebe 200 com
a página de login inteira, e o `responseHandling` default do htmx troca 2xx: a
página de login vai parar dentro de `[data-modal-body]`. É a mesma imagem que a
issue #130 descreve, disparada por expiração de sessão em vez de por código de
view — e é o caso realista, porque o modal fica aberto na tela enquanto a sessão
morre.

O eixo anônimo daqui faz o POST **sem** o cabeçalho HTMX, então não vê isso. Não
é descuido: fechar esse buraco exige converter o redirect de login em 204 +
`HX-Redirect` para toda requisição HTMX do sistema — middleware ou
`login_required` próprio —, o que muda o comportamento de todo endpoint HTMX e
não só dos modais. Fica para issue própria; o eixo anônimo com HTMX entra junto
com a correção, porque hoje ele falharia por um defeito que não é destas rotas.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html.parser import HTMLParser
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
    `DoesNotExist` em vez de comparar. Use o helper `snapshot` desta módulo.

    `muta` separa o cenário que **deve** gravar do que não deve. Sem ele, um
    cenário de transição recusada e um de caminho feliz asseveram exatamente a
    mesma coisa — 204 para o detalhe —, e o de erro continuaria verde se a view
    regredisse e passasse a executar a transição que devia recusar.

    `modal_id` é o `id` do modal que abriu a ação. O 422 tem de devolver o
    corpo **daquele** modal: `[data-modal-body]` sem id passaria por um
    fragment que o `outerHTML` colocaria no lugar errado.
    """

    url: str
    payload: dict[str, Any]
    destino_esperado: str | None
    ler_estado: Callable[[], Any]
    ator: Any
    modal_id: str
    muta: bool = False
    # GET que mostra o mesmo modal em render inicial — usado por
    # `assert_copy_nao_diverge` (#135) para comparar título/descrição contra o
    # 422. `None` pula a checagem: nem todo cenário tem um GET barato que
    # reproduza o mesmo modal (ex.: sessão de preview que o próprio cenário
    # esvazia de propósito).
    url_render_inicial: str | None = None


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


def snapshot(queryset, pk: int, *campos: str):
    """Tupla dos campos da linha, ou `None` se ela não existe mais.

    Existe para que a forma correta seja o caminho mais curto: `get(pk=…)`
    estouraria `DoesNotExist` no cenário de `cancelar`, onde o descarte de
    rascunho sem número público apaga a `Requisicao`.
    """
    return queryset.filter(pk=pk).values_list(*campos).first()


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


def assert_contrato_modal(
    resposta, *, destino_esperado: str | None = None, modal_id: str | None = None
) -> None:
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
        f'Resposta {status} a um POST HTMX de modal — só 204+HX-Redirect ou '
        f'422+fragment cumprem o contrato. Um 2xx aqui é trocado dentro de '
        f'[data-modal-body] pelo hx-swap="outerHTML" do componente, e uma '
        f'página inteira empilha app bar e navegação no diálogo; um 4xx/5xx '
        f'não é trocado por padrão no htmx 2, e vira no-op silencioso — o '
        f'diálogo fica idêntico e a pessoa aperta de novo. Nenhum dos dois '
        f'responde se gravou ou não.'
    )
    # A outra direção da união. Sem isto, um cenário que declara destino e
    # regride para 422 continua verde — 422+fragment é forma válida —, e a
    # declaração de destino vira decoração.
    assert destino_esperado is None, (
        f'Cenário declarou destino_esperado={destino_esperado!r} e respondeu 422. '
        'Ou a rota regrediu para o ramo de erro, ou o cenário deve declarar None.'
    )
    assert b'data-modal-body' in resposta.content, (
        '422 sem [data-modal-body] no corpo: o swap trocaria o corpo do modal '
        'por um fragment que não é um corpo de modal.'
    )
    if modal_id is not None:
        # O id importa: `hx-target` é `[data-modal-body='<id>']`. Um fragment
        # com o id de outro modal é trocado no lugar errado, e o `modal_id` é
        # string literal repetida à mão em quatro views.
        assert f'data-modal-body="{modal_id}"'.encode() in resposta.content, (
            f'422 devolveu o corpo de outro modal — esperado id {modal_id!r}.'
        )
    # O 422 tem de *dizer* o que falhou. `coletar_erros` (`core_tags.py`)
    # despacha a fonte por `isinstance(str)` / `non_form_errors` / `errors` e
    # não tem `else`: uma fonte que ela não reconhece — `erro=exc` em vez de
    # `erro=str(exc)` — é descartada em silêncio, e o modal reabre com a caixa
    # de erro vazia. Que é o sintoma da issue, com outro nome.
    assert b'data-error-summary' in resposta.content, (
        '422 com [data-modal-erro] vazio: o modal reabriu sem dizer o que '
        'falhou. Fonte de erro que a tag não reconhece some assim, sem barulho.'
    )


class _TextoPorId(HTMLParser):
    """Texto (concatenado) de cada elemento com `id`, indexado pelo id."""

    def __init__(self):
        super().__init__()
        self.textos: dict[str, str] = {}
        self._pilha: list[str | None] = []

    def handle_starttag(self, tag, attrs):
        id_ = dict(attrs).get('id')
        self._pilha.append(id_)
        if id_ is not None:
            self.textos.setdefault(id_, '')

    def handle_endtag(self, tag):
        if self._pilha:
            self._pilha.pop()

    def handle_data(self, data):
        for id_ in self._pilha:
            if id_ is not None:
                self.textos[id_] += data


def _texto_por_id(html: str, elemento_id: str) -> str:
    parser = _TextoPorId()
    parser.feed(html)
    return ' '.join(parser.textos.get(elemento_id, '').split())


def assert_copy_nao_diverge(resposta_422, *, html_inicial: str, modal_id: str) -> None:
    """Título e descrição do 422 não podem divergir do render inicial (#135).

    O 422 e o render inicial são o mesmo modal, só que reaberto com erro —
    `components/_modal_body.html` é a fonte HTML dos dois. Duas fontes de
    copy independentes (template × view) já divergiram no passado sem que
    nada acusasse; esta asserção lê o texto renderizado dos dois lados em vez
    de comparar string contra string, então pega divergência tanto de copy
    hardcoded quanto de lookup errado no dicionário de apresentação.
    """
    html_422 = resposta_422.content.decode('utf-8')
    for sufixo in ('titulo', 'descricao'):
        elemento_id = f'{modal_id}-{sufixo}'
        texto_inicial = _texto_por_id(html_inicial, elemento_id)
        texto_422 = _texto_por_id(html_422, elemento_id)
        assert texto_422 == texto_inicial, (
            f'{modal_id}: {sufixo} do 422 diverge do render inicial — '
            f'{texto_422!r} != {texto_inicial!r}.'
        )


def assert_fallback_sem_htmx(resposta) -> None:
    """Assere o que é uniforme no fallback sem HTMX: nunca 204, nunca HX-Redirect.

    O contrato positivo não é uniforme entre as rotas — umas redirecionam,
    outras renderizam página de erro, e isso é decisão de cada tela. Uma
    asserção genérica que aceitasse os dois casos aceitaria quase tudo.

    O que é uniforme é o negativo: um cliente sem JS não age sobre nenhum dos
    dois — 204 deixa a página parada e o cabeçalho é lido por ninguém.

    Note o que isto **não** pega: `htmx_redirect` incondicional passa, porque o
    helper já ramifica por dentro e devolve 302 fora do HTMX. A regressão que
    esta asserção pega é o 204 montado à mão — `HttpResponse(status=204)` com o
    cabeçalho posto na resposta —, ou o `HttpResponseClientRedirect` do
    django_htmx, que responde 200 e emite o cabeçalho sempre.
    """
    assert resposta.status_code != 204, (
        'Resposta 204 a um POST sem HTMX: um cliente sem JS fica com a página '
        'parada, sem sinal de que a ação aconteceu.'
    )
    assert 'HX-Redirect' not in resposta, (
        'HX-Redirect numa resposta sem HTMX: o cabeçalho não é lido por '
        'ninguém, e o redirecionamento simplesmente não acontece.'
    )
