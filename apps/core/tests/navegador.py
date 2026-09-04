"""Utilidades da camada Navegador (ADR-0019), compartilhadas entre apps.

Mesmo lugar e mesmo papel de `marcacao.py` e `contrato_modal.py`: módulo de
teste em `apps/core/tests/` importado pelos testes dos apps de domínio. Não é
`conftest.py` porque `conftest.py` só alcança o próprio diretório, e a camada
tem casos em `core` e em `requisicoes`.
"""

import pathlib
from typing import NamedTuple


def autenticar(live_server, context, usuario):
    """Transplanta uma sessão logada do `Client` do Django para o navegador.

    Preencher o formulário de login em cada teste gastaria um round-trip e
    acoplaria toda a camada à marcação da tela de login — que tem testes
    próprios, na lane certa.
    """
    from django.test import Client

    cliente = Client()
    cliente.force_login(usuario)
    context.add_cookies(
        [
            {
                'name': 'sessionid',
                'value': cliente.cookies['sessionid'].value,
                'url': live_server.url,
            }
        ]
    )


_JS_CONTRASTE = (pathlib.Path(__file__).parent / 'navegador_contraste.js').read_text()


class Medicao(NamedTuple):
    """Resultado de `medir_contraste`.

    As três listas precisam estar vazias para a tela passar, e cada uma falha
    por um motivo diferente: `violacoes` é defeito de contraste; as outras duas
    são a varredura avisando que **não sabe** medir aquele ponto. Um guarda que
    fica cego em silêncio deixa de ser guarda.
    """

    violacoes: list[dict]
    """Texto abaixo do piso WCAG, com a razão medida e o limiar aplicável."""

    nao_convertidas: list[dict]
    """Cor CSS que o canvas recusou. Sem isso viraria preto e passaria calada."""

    nao_suportados: list[dict]
    """Efeito de CSS fora do que a varredura mede: `background-image`,
    `mix-blend-mode`, `opacity` de ancestral, texto em pseudo-elemento."""


def medir_contraste(page) -> Medicao:
    """Mede o contraste texto/fundo efetivo de cada nó de texto visível.

    Complementa `test_nenhum_elemento_combina_par_de_cor_reprovado`
    (`test_tokens_semanticos.py`), que só vê par de cor no mesmo elemento: aqui
    o fundo é resolvido subindo a árvore, com composição de alpha, o que exige
    cascade e pipeline de cor reais — daí a lane Navegador (ADR-0019).

    Cada violação carrega o número medido e o limiar aplicável: a #166 exige o
    valor na mensagem de falha, não só "reprovou".
    """
    resultado = page.evaluate(_JS_CONTRASTE)
    return Medicao(
        violacoes=resultado['violacoes'],
        nao_convertidas=resultado['naoConvertidas'],
        nao_suportados=resultado['naoSuportados'],
    )
