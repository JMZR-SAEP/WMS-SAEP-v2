"""Paridade entre o banner de aviso e a faixa de flash message (issue #124).

`components/alert.html` (layout `stack`) e `core/partials/_message_item.html`
renderizam os mesmos quatro níveis de severidade e seguem separados de
propósito: os contratos ARIA são incompatíveis. A separação foi aprovada com
uma condição — paridade documentada **e verificada**. Este módulo é a
verificação.

Três lados, não dois. `PARIDADE_ESPERADA` é a expectativa aprovada e vive aqui,
fora do alcance de quem edita template ou documentação; a tabela de
`docs/design-system.md` é conferida contra ela, e o HTML renderizado dos dois
caminhos também. Um teste que só comparasse os dois templates entre si passaria
se alguém mudasse os dois para o mesmo valor errado — detectaria divergência,
não valor aprovado.

Os dois caminhos são renderizados pelo engine do Django, e não lidos como texto:
100% do estado visual dos dois arquivos vive dentro de `{% if %}`, então parser
de HTML estático não enxerga nada.
"""

import pathlib
import re

import pytest
from django.template.loader import render_to_string

from apps.core.tests.marcacao import atributo, classes, elementos

BASE_DIR = pathlib.Path(__file__).resolve().parents[3]
DESIGN_SYSTEM = BASE_DIR / 'docs' / 'design-system.md'

# Nível canônico -> (variante do alert.html, nível do Django messages).
# `danger` e `error` são o mesmo nível com dois nomes: o componente segue o
# vocabulário de `button.html`, a faixa recebe o que o Django emite.
NOMES = {
    'info': ('info', 'info'),
    'success': ('success', 'success'),
    'warning': ('warning', 'warning'),
    'danger': ('danger', 'error'),
}

# A expectativa aprovada. Mudar um valor aqui é uma decisão de design explícita
# no diff — que é o ponto de a constante não ser derivada da tabela nem do
# template.
PARIDADE_ESPERADA = {
    'info': {
        'raio': 'rounded-lg',
        'padding': 'px-4 py-3',
        'fundo': 'bg-primary-subtle',
        'borda': 'border-primary-border',
        'texto': 'text-primary-text-emphasis',
        'icone': 'currentColor',
        'role': 'status',
    },
    'success': {
        'raio': 'rounded-lg',
        'padding': 'px-4 py-3',
        'fundo': 'bg-success-subtle',
        'borda': 'border-success-border',
        'texto': 'text-success-text-emphasis',
        'icone': 'currentColor',
        'role': 'status',
    },
    'warning': {
        'raio': 'rounded-lg',
        'padding': 'px-4 py-3',
        'fundo': 'bg-warning-subtle',
        'borda': 'border-warning-border',
        'texto': 'text-warning-text',
        'icone': 'currentColor',
        'role': 'alert',
    },
    'danger': {
        'raio': 'rounded-lg',
        'padding': 'px-4 py-3',
        'fundo': 'bg-danger-subtle',
        'borda': 'border-danger-border',
        'texto': 'text-danger-text-emphasis',
        'icone': 'currentColor',
        'role': 'alert',
    },
}

PROPRIEDADES = ('raio', 'padding', 'fundo', 'borda', 'texto', 'icone', 'role')

NIVEIS = tuple(PARIDADE_ESPERADA)

# `rounded-md` é 0.375rem, o raio de **controle** da Regra do Raio Crescente
# (docs/design-system.md, §Espaçamento e forma). Nenhuma das duas superfícies é
# um controle.
RAIO_DE_CONTROLE = 'rounded-md'


# ─── Renderização dos dois caminhos ───────────────────────────────────────


def _render_banner(nivel):
    variante, _ = NOMES[nivel]
    return render_to_string(
        'components/alert.html',
        {'variant': variante, 'message': f'Mensagem {nivel}'},
    )


def _render_faixa(nivel):
    from django.contrib import messages as django_messages
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.test import RequestFactory

    _, nivel_django = NOMES[nivel]
    request = RequestFactory().get('/')
    request.session = {}
    request._messages = FallbackStorage(request)
    getattr(django_messages, nivel_django)(request, f'Mensagem {nivel}')
    return render_to_string('core/partials/_messages.html', request=request)


def _caixa_do_banner(html):
    """O `<div>` externo do layout `stack` — o primeiro elemento renderizado."""
    tag, atributos, _ = next(elementos(html, 'div'))
    assert tag == 'div'
    return atributos


def _caixa_da_faixa(html):
    """A faixa é o `<div>` que carrega o `x-data` do dismiss."""
    (atributos,) = [
        atributos
        for _, atributos, _ in elementos(html, 'div')
        if atributo(atributos, 'x-data')
    ]
    return atributos


# ─── Extração de cada propriedade a partir do HTML renderizado ────────────


def _uma_classe(atributos, padrao):
    encontradas = sorted(c for c in classes(atributos) if re.fullmatch(padrao, c))
    assert len(encontradas) == 1, (
        f'esperava exatamente uma classe casando com {padrao!r}, achei {encontradas}'
    )
    return encontradas[0]


def _raio(atributos):
    return _uma_classe(atributos, r'rounded(-.+)?')


def _padding(atributos):
    px = _uma_classe(atributos, r'px-.+')
    py = _uma_classe(atributos, r'py-.+')
    return f'{px} {py}'


def _fundo(atributos):
    return _uma_classe(atributos, r'bg-.+')


def _borda(atributos):
    return _uma_classe(atributos, r'border-.+')


def _texto(atributos):
    """O token de cor de texto — `text-sm` é tamanho, não cor."""
    return _uma_classe(atributos, r'text-(?!sm$|xs$|base$|lg$)\S+')


def _subarvore_do_icone(html):
    """Do `<svg>` de nível até o `</svg>` que o fecha.

    Na faixa há um segundo `<svg>`, o "×" do botão de fechar; ele não sinaliza
    nível e fica de fora da paridade. Nenhum dos dois ícones aninha `<svg>`.
    """
    inicio = html.index('<svg')
    fim = html.index('</svg>', inicio) + len('</svg>')
    return html[inicio:fim]


def _elementos_quaisquer(trecho):
    """Todo elemento do trecho, sem lista fixa de tags.

    `elementos` exige os nomes de tag; aqui os nomes são descobertos primeiro,
    para que um `<circle>` ou `<use>` colado amanhã também caia na varredura em
    vez de passar por baixo dela.
    """
    nomes = {
        encontro.group(1)
        for encontro in re.finditer(r'<([a-zA-Z][\w-]*)(?=[\s/>])', trecho)
    }
    for nome in sorted(nomes):
        yield from elementos(trecho, nome)


#: Valores de pintura que não fixam cor — deixam a herança de pé.
PINTURA_HERDADA = frozenset({'currentcolor', 'inherit', 'unset', 'revert', 'none'})

#: Propriedades CSS que decidem a cor do ícone. `fill-opacity` e `stroke-width`
#: ficam de fora de propósito: mudam a pintura, não a cor herdada. Tupla, e não
#: conjunto, para que a propriedade acusada seja sempre a mesma.
PROPRIEDADES_DE_COR = ('color', 'fill', 'stroke')


def _vencedoras_do_style(valor):
    """A declaração vencedora de cada propriedade de cor, pela cascata real.

    Dentro de um mesmo bloco, `!important` ganha de quem não é, independente da
    ordem; entre declarações de mesma importância, ganha a última. Ignorar isso
    faria `fill:red;fill:currentColor` ser lido como cor fixada, quando o que
    vale ali é o `currentColor`.
    """
    vencedoras = {}
    for declaracao in valor.split(';'):
        propriedade, separador, conteudo = declaracao.partition(':')
        propriedade = propriedade.strip().lower()
        if not separador or propriedade not in PROPRIEDADES_DE_COR:
            continue

        conteudo = conteudo.strip()
        sem_bang = re.sub(r'!\s*important\s*$', '', conteudo, flags=re.I).strip()
        importante = sem_bang != conteudo
        if not sem_bang:
            continue

        anterior = vencedoras.get(propriedade)
        if anterior is None or importante >= anterior[0]:
            vencedoras[propriedade] = (importante, sem_bang)
    return {propriedade: par[1] for propriedade, par in vencedoras.items()}


def _cor_fixada_por_style(valor):
    """A declaração do `style` que sequestra a cor, ou `None` se nenhuma.

    Um `style` qualquer não basta para condenar o elemento: `opacity` ou
    `transform` inline não têm nada a ver com herança de cor, e tratá-los como
    violação faria o guarda falhar por engano — o que manda a próxima pessoa
    consertar o teste em vez do código.
    """
    if not valor:
        return None
    vencedoras = _vencedoras_do_style(valor)
    for propriedade in PROPRIEDADES_DE_COR:
        conteudo = vencedoras.get(propriedade)
        if conteudo is not None and conteudo.lower() not in PINTURA_HERDADA:
            return f'style {propriedade}:{conteudo}'
    return None


def _icone_de_nivel(html):
    """A cor efetiva do ícone de nível — `currentColor` se nada a fixar.

    `fill="currentColor"` no `<svg>` sozinho não prova herança, e olhar só o
    `<svg>` também não basta: `color` pode ser redefinido por uma classe
    `text-*` nele, e o preenchimento pode ser sequestrado mais abaixo, por um
    `fill` cru, um `style` inline ou uma classe de cor num `<path>`. A varredura
    cobre o `<svg>` e todos os seus descendentes, e devolve o primeiro
    responsável por fixar a cor — ou o `fill` do `<svg>`, quando ninguém fixa.

    `fill-rule` não é confundido com `fill`: a busca de atributo casa o nome
    inteiro, e no `style` a propriedade é comparada depois do `partition(':')`.
    """
    subarvore = _subarvore_do_icone(html)
    _, raiz, _ = next(elementos(subarvore, 'svg'))
    for _, atributos, _ in _elementos_quaisquer(subarvore):
        pelo_style = _cor_fixada_por_style(atributo(atributos, 'style'))
        if pelo_style:
            return pelo_style
        cores = sorted(
            c for c in classes(atributos) if re.fullmatch(r'(text|fill|stroke)-\S+', c)
        )
        if cores:
            return ' '.join(cores)
        for pintura in ('fill', 'stroke'):
            valor = atributo(atributos, pintura)
            if valor is not None and valor.lower() not in PINTURA_HERDADA:
                return f'{pintura}="{valor}"'
    return atributo(raiz, 'fill') or 'sem fill'


def _role_do_banner(html):
    return atributo(_caixa_do_banner(html), 'role')


def _role_da_faixa(html):
    """Na faixa o `role` vive no nó que contém só o texto, não na caixa."""
    (papel,) = [
        papel
        for _, atributos, _ in elementos(html, 'div')
        if (papel := atributo(atributos, 'role')) in {'alert', 'status'}
    ]
    return papel


def _propriedades_do_banner(nivel):
    html = _render_banner(nivel)
    caixa = _caixa_do_banner(html)
    return {
        'raio': _raio(caixa),
        'padding': _padding(caixa),
        'fundo': _fundo(caixa),
        'borda': _borda(caixa),
        'texto': _texto(caixa),
        'icone': _icone_de_nivel(html),
        'role': _role_do_banner(html),
    }


def _propriedades_da_faixa(nivel):
    html = _render_faixa(nivel)
    caixa = _caixa_da_faixa(html)
    return {
        'raio': _raio(caixa),
        'padding': _padding(caixa),
        'fundo': _fundo(caixa),
        'borda': _borda(caixa),
        'texto': _texto(caixa),
        'icone': _icone_de_nivel(html),
        'role': _role_da_faixa(html),
    }


CAMINHOS = {'banner': _propriedades_do_banner, 'faixa': _propriedades_da_faixa}


# ─── O HTML renderizado bate com a expectativa aprovada ───────────────────


@pytest.mark.parametrize('caminho', sorted(CAMINHOS))
@pytest.mark.parametrize('propriedade', PROPRIEDADES)
@pytest.mark.parametrize('nivel', NIVEIS)
def test_caminho_bate_com_a_paridade_aprovada(nivel, propriedade, caminho):
    obtido = CAMINHOS[caminho](nivel)[propriedade]
    assert obtido == PARIDADE_ESPERADA[nivel][propriedade]


# ─── A tabela do design system bate com a expectativa aprovada ────────────

TITULO_DA_SECAO = '### Paridade entre o banner e a faixa de flash'

# Cabeçalho da tabela -> chave de PARIDADE_ESPERADA.
COLUNAS = {
    'raio': 'raio',
    'padding': 'padding',
    'fundo': 'fundo',
    'borda': 'borda',
    'texto': 'texto',
    'ícone': 'icone',
    'role': 'role',
}


def _celulas(linha):
    return [c.strip().strip('`') for c in linha.strip().strip('|').split('|')]


def _tabela_de_paridade():
    """A tabela da seção, como {nível: {propriedade: valor}}.

    Falha alto em vez de devolver vazio: seção apagada ou tabela reescrita com
    outra forma precisa quebrar o teste, não fazê-lo passar vacuamente — é o
    buraco de `test_nenhum_controle_abaixo_do_piso_de_44px`, corrigido na #120.
    """
    texto = DESIGN_SYSTEM.read_text(encoding='utf-8')
    assert TITULO_DA_SECAO in texto, (
        f'seção {TITULO_DA_SECAO!r} sumiu de {DESIGN_SYSTEM.name}'
    )

    depois = texto[texto.index(TITULO_DA_SECAO) :]
    linhas = [linha for linha in depois.splitlines() if linha.startswith('|')]
    assert len(linhas) >= 3, 'a seção de paridade não tem tabela'

    cabecalho = _celulas(linhas[0])
    assert cabecalho[0].lower() == 'nível', (
        f'a primeira coluna deveria ser o nível, é {cabecalho[0]!r}'
    )
    propriedades = [COLUNAS.get(c.lower()) for c in cabecalho[1:]]
    assert None not in propriedades, (
        f'coluna desconhecida no cabeçalho da tabela: {cabecalho[1:]}'
    )
    assert sorted(propriedades) == sorted(PROPRIEDADES), (
        f'a tabela declara {sorted(propriedades)}, '
        f'e as propriedades de paridade são {sorted(PROPRIEDADES)}'
    )

    tabela = {}
    for linha in linhas[2:]:
        celulas = _celulas(linha)
        if len(celulas) != len(cabecalho):
            break
        tabela[celulas[0]] = dict(zip(propriedades, celulas[1:], strict=True))
    return tabela


def test_a_tabela_de_paridade_cobre_os_quatro_niveis():
    assert sorted(_tabela_de_paridade()) == sorted(NIVEIS)


@pytest.mark.parametrize('propriedade', PROPRIEDADES)
@pytest.mark.parametrize('nivel', NIVEIS)
def test_a_tabela_declara_a_paridade_aprovada(nivel, propriedade):
    """Documentação que mente quebra o teste tanto quanto template que mente."""
    declarado = _tabela_de_paridade()[nivel][propriedade]
    assert declarado == PARIDADE_ESPERADA[nivel][propriedade]


def test_a_secao_registra_por_que_os_dois_arquivos_seguem_separados():
    """Sem a razão escrita, a próxima pessoa "unifica" os dois e perde o ARIA."""
    texto = DESIGN_SYSTEM.read_text(encoding='utf-8')
    secao = texto[texto.index(TITULO_DA_SECAO) :]
    secao = secao[: secao.index('## Contrato de componente novo')]
    for termo in ('ARIA', 'dismiss', 'assertividade', 'body_template'):
        assert termo in secao, f'a seção de paridade não menciona {termo!r}'


# ─── Invariantes de regra, independentes da tabela ────────────────────────


@pytest.mark.parametrize('caminho', sorted(CAMINHOS))
@pytest.mark.parametrize('nivel', NIVEIS)
def test_nenhuma_das_duas_superficies_usa_raio_de_controle(nivel, caminho):
    """Vale mesmo que alguém reescreva tabela, constante e templates juntos.

    `rounded-md` é 0.375rem — raio de controle. Nenhuma das duas superfícies é
    acionável como unidade, então nenhuma delas pode usá-lo.
    """
    assert CAMINHOS[caminho](nivel)['raio'] != RAIO_DE_CONTROLE


@pytest.mark.parametrize('caminho', sorted(CAMINHOS))
@pytest.mark.parametrize('nivel', NIVEIS)
def test_o_icone_de_nivel_herda_a_cor_da_caixa(nivel, caminho):
    """`fill="currentColor"` presente **e** nada dentro do `<svg>` fixando cor.

    Só a ausência de classe não prova herança: o preenchimento poderia vir de
    um `fill` fixo ou de um `style` inline. Só o `fill` também não prova: uma
    classe `text-*` redefine `color` e sequestra o `currentColor`.
    """
    assert CAMINHOS[caminho](nivel)['icone'] == 'currentColor'


def test_o_alert_nao_tem_mais_excecao_interna_de_raio():
    """O `layout="row"` era a única superfície de papel dentro do `alert.html`,
    e por isso a única exceção à Regra do Raio Crescente aqui dentro.

    Ele virou `requisicoes/partials/_painel_decisao.html` na #127, e a cobrança
    do raio de papel foi junto: está em
    `apps/requisicoes/tests/test_painel_decisao.py`. Deste lado sobra a regra
    sem exceção — o alert é campo, e um `rounded-xl` reaparecendo aqui é drift.
    """
    alert = (BASE_DIR / 'apps/core/templates/components/alert.html').read_text(
        encoding='utf-8'
    )

    for nivel in NIVEIS:
        html = render_to_string(
            'components/alert.html', {'variant': nivel, 'message': 'Mensagem'}
        )
        _, atributos, _ = next(elementos(html, 'div'))
        assert _raio(atributos) == 'rounded-lg'

    assert 'rounded-xl' not in alert
    assert 'Regra do Raio Crescente' in alert


@pytest.mark.parametrize(
    'style,esperado',
    [
        (None, None),
        ('', None),
        # Não têm nada a ver com herança de cor.
        ('opacity:.5', None),
        ('transform:rotate(90deg)', None),
        # Parecidas com as de cor, mas não são: mudam a pintura, não a cor.
        ('fill-opacity:.5', None),
        ('stroke-width:2', None),
        # Fixam a propriedade, mas no valor que mantém a herança.
        ('fill:currentColor', None),
        ('color:inherit', None),
        ('fill:none', None),
        # Sequestram de fato.
        ('fill:#b45309', 'style fill:#b45309'),
        ('opacity:.5;stroke:red', 'style stroke:red'),
        ('COLOR: Red', 'style color:Red'),
        # Cascata dentro do mesmo bloco: a última de mesma importância vence.
        ('fill:red;fill:currentColor', None),
        ('fill:currentColor;fill:red', 'style fill:red'),
        # `!important` vence quem não é, independente da ordem.
        ('fill:currentColor !important', None),
        ('fill:red !important;fill:currentColor', 'style fill:red'),
        ('fill:currentColor !important;fill:red', None),
        # Declaração truncada não decide nada e não apaga a anterior.
        ('fill:red;fill:', 'style fill:red'),
        ('fill', None),
    ],
)
def test_cor_fixada_por_style_so_acusa_declaracao_de_cor(style, esperado):
    """O guarda do ícone precisa acusar cor fixada — e só isso.

    Tratar qualquer `style` como violação faria o guarda falhar por engano, e
    guarda que falha por engano manda a próxima pessoa consertar o teste em vez
    do código.
    """
    assert _cor_fixada_por_style(style) == esperado
