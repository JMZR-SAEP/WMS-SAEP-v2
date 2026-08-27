from collections.abc import Iterable, Mapping
from datetime import timedelta
from typing import Any

from django.core.exceptions import NON_FIELD_ERRORS, ImproperlyConfigured
from django import template
from django.forms import BoundField
from django.template.loader import render_to_string
from django.utils.functional import Promise
from django.utils.safestring import SafeString, mark_safe

from apps.core import quantidades

register = template.Library()


@register.filter
def minutos_totais(delta: object) -> int | None:
    """Converte um `timedelta` em minutos inteiros (piso), pra copy de prazo.

    Usado com `cooloff_timedelta` do django-axes, pra que a página de
    bloqueio de login nunca minta o prazo se `AXES_COOLOFF_TIME` mudar.

    Testa o tipo, não `is None`. No permalock (`AXES_COOLOFF_TIME = None`) o
    axes monta o contexto com `if cool_off:` e simplesmente não inclui a chave
    (`axes.helpers`); o Django resolve a variável ausente como
    `string_if_invalid`, que é `''` por padrão. O guarda anterior deixava essa
    string passar e estourava em `''.total_seconds()` — ou seja, a tela de
    bloqueio devolvia 500 exatamente na configuração que o comentário de
    `accounts/login_bloqueado.html` diz suportar com "mensagem sem prazo".

    Nenhum valor faz esta tela quebrar: quem a vê já está bloqueado e sem outra
    saída na interface.
    """
    if not isinstance(delta, timedelta):
        return None
    return int(delta.total_seconds() // 60)


@register.simple_tag
def titulo_com_termo(termo: str, prefixo: str, sufixo_generico: str = '') -> str:
    """Monta o título do estado vazio filtrado: prefixo + termo entre aspas.

    Existe pra manter a composição na tela chamadora — e não em
    `components/empty_state.html` — sem repetir, em cada tela, o
    `{% templatetag openblock %} with titulo_busca='...'|add:termo|add:'"'
    {% templatetag closeblock %}` que já causou dois problemas: o regex do
    guard de copy do estado vazio (`test_todo_chamador_do_estado_vazio_segue_a_copy`)
    só resolve `{% templatetag openblock %} with {% templatetag closeblock %}`
    até o primeiro filtro encadeado, então o título dinâmico passava como se
    fosse literal; e mover a decisão "eco o termo ou caio no genérico" para
    dentro de `empty_state.html` violava a Regra do Chrome Sem Parâmetro
    (DESIGN.md): componente de moldura não recebe parâmetro que descreve
    conteúdo — quem chama resolve o título por inteiro antes do include.

    Não marca o retorno como seguro: o autoescape do Django roda sobre a
    string inteira no `{{ titulo }}` de `empty_state.html`, igual rodava
    antes — se `termo` contiver `<`, `>`, `&` ou aspas, eles saem escapados.

    Uso:
      {% titulo_com_termo filtros.material 'Nenhum resultado para' 'este filtro' as titulo_busca %}
      {% include 'components/empty_state.html' with titulo=titulo_busca ... %}
    """
    if termo:
        return f'{prefixo} "{termo}"'
    return f'{prefixo} {sufixo_generico}'.rstrip()


ICONES_CATALOGO = frozenset(
    {
        'voltar',
        'lixeira',
        'remover',
        'spinner',
        'adicionar',
        'enviar',
        'copiar',
        'editar',
        'confirmar',
        'confirmar_check',
        'estornar',
        'informacao',
        'atencao',
        'alerta',
        'devolver',
    }
)


@register.simple_tag
def icon(name: str, size: int = 20, **kwargs: str) -> str:
    """Renderiza um ícone do catálogo vendorizado (aria-hidden sempre)."""
    if not isinstance(name, str) or name not in ICONES_CATALOGO:
        raise ImproperlyConfigured(
            f'Ícone "{name}" não está no catálogo (components/icons/). '
            f'Nomes válidos: {sorted(ICONES_CATALOGO)}.'
        )
    css_class = kwargs.get('class', '')
    return mark_safe(
        render_to_string(
            f'components/icons/{name}.svg',
            {'size': size, 'class': css_class},
        )
    )


@register.filter
def formatar_quantidade(qtd, unidade: str) -> str:
    """Formata quantidade conforme a unidade de medida do material.

    - 'un' → inteiro
    - 'kg', 'l', 'm' → 1 casa decimal
    - demais → strip trailing zeros (casas significativas)

    A regra em si vive em `apps.core.quantidades`, junto do `step` do campo e do
    valor inicial que o preenche: são três faces da mesma política, e views
    também precisam dela — templatetag não é lugar de onde uma view importa.
    """
    return quantidades.formatar(qtd, unidade)


# `debug` é nível de desenvolvimento: nunca teve texto escrito para o usuário
# final. O catch-all anterior do partial (`!= 'error' and != 'warning'`) o
# renderizava como info em produção.
_NIVEIS_OCULTOS = frozenset({'debug'})
_NIVEIS_ASSERTIVOS = frozenset({'error', 'warning'})


@register.filter
def mensagens_visiveis(mensagens: Any) -> list[Any]:
    """Mensagens que chegam ao usuário final, na ordem em que devem aparecer.

    Existe para que `core/partials/_messages.html` decida wrapper, ordem e
    visibilidade a partir de *uma* lista, em vez de iterar `messages` duas vezes.
    A versão com dois loops funcionava só porque o `BaseStorage` do Django é
    re-iterável depois do primeiro consumo — dependência num detalhe de framework
    que o arquivo não declarava —, e cobrava caro por isso: o segundo wrapper
    renderizava mesmo sem nenhuma mensagem polida para colocar dentro.

    Ordem: assertivo (`error`, `warning`) antes de polido, que é o que o
    comentário do topo do partial sempre prometeu — o leitor de tela recebe
    primeiro o que interrompe. Dentro de cada grupo, `sorted` estável preserva a
    ordem em que a view enfileirou, que é a ordem em que os fatos aconteceram.
    Não há prioridade entre `error` e `warning`, nem entre `success` e `info`:
    os `{% if %}/{% elif %}` do partial sempre foram condicionais por mensagem,
    e inventar uma aqui mudaria a ordem que a tela tem hoje.

    Nível desconhecido conta como polido: descartá-lo em silêncio esconderia a
    mensagem de quem a registrou de propósito, e tratá-lo como assertivo lhe daria
    prioridade que ninguém pediu.
    """
    visiveis = [
        mensagem
        for mensagem in mensagens
        if getattr(mensagem, 'level_tag', '') not in _NIVEIS_OCULTOS
    ]
    return sorted(
        visiveis,
        key=lambda m: 0 if getattr(m, 'level_tag', '') in _NIVEIS_ASSERTIVOS else 1,
    )


_FORMA_BOTAO = 'inline-flex items-center justify-center min-h-11 rounded-md font-medium'
_FORMA_LINK = 'inline-flex items-center rounded font-medium'
_FOCO_BOTAO = (
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1'
)
# `aria-disabled` acompanha `disabled` porque a ação de workflow bloqueada com
# motivo declarado usa o primeiro para continuar focável (ver button.html).
_ESTADOS_BOTAO = (
    'disabled:cursor-not-allowed disabled:opacity-60 '
    'aria-disabled:cursor-not-allowed aria-disabled:opacity-60'
)
_VARIANTES_BOTAO: dict[str, str] = {
    'primary': (
        'bg-primary text-text-on-primary hover:bg-primary-hover '
        'active:bg-primary-active focus-visible:ring-border-focus'
    ),
    'secondary': (
        'bg-surface text-text-secondary border border-border-control '
        'hover:bg-bg-page hover:text-text-primary focus-visible:ring-border-focus'
    ),
    'neutral': (
        'bg-text-secondary text-text-on-primary hover:bg-text-primary '
        'focus-visible:ring-text-tertiary'
    ),
    'danger': (
        'bg-danger text-text-on-primary hover:bg-danger-hover '
        'active:bg-danger-active focus-visible:ring-danger-accent'
    ),
    'danger-outline': (
        'bg-surface text-danger-text border border-danger-border-strong '
        'hover:bg-danger-subtle focus-visible:ring-danger-accent'
    ),
    'warning-outline': (
        'bg-surface text-warning-text-strong border border-warning-border-strong '
        'hover:bg-warning-muted focus-visible:ring-warning'
    ),
    'return-outline': (
        'bg-surface text-return-text-strong border border-return-border '
        'hover:bg-return-subtle focus-visible:ring-return'
    ),
    'return': (
        'bg-return text-text-on-primary hover:bg-return-hover '
        'active:bg-return-active focus-visible:ring-return'
    ),
    'ghost': (
        'bg-transparent text-text-secondary hover:bg-bg-subtle '
        'focus-visible:ring-border-focus'
    ),
    'link': (
        'bg-transparent text-primary-text hover:underline focus-visible:ring-border-focus'
    ),
}
_TAMANHOS_BOTAO = {'sm': 'px-3 py-2 text-xs', 'md': 'px-3 py-2 text-sm'}


@register.simple_tag
def classes_botao(
    *,
    variant: str = '',
    size: str = '',
    tag: str = 'button',
    full_width_mobile: Any = False,
    extra: Any = '',
) -> str:
    """Monta a classe de components/button.html — uma vez, para os dois ramos.

    A expressão de nove variantes vivia duplicada por inteiro entre o ramo `<a>`
    e o ramo `<button>` do template, ~900 caracteres cada. As duas cópias já
    tinham divergido: `cursor-pointer` e os estados `disabled:` existiam só na
    segunda. Toda variante nova precisava ser escrita em dois lugares, e nada
    comparava os dois.

    A diferença real entre os ramos é pequena e está explícita aqui: um link não
    tem estado desabilitado nem cursor de ponteiro a declarar.

    `variant` e `size` chegam vazios quando o chamador não os passa (o Django
    resolve variável ausente como string vazia), e caem no default.
    """
    forma = _FORMA_LINK if variant == 'link' else _FORMA_BOTAO
    partes = [forma]
    if tag == 'button':
        partes.append('cursor-pointer')
    partes.append(_FOCO_BOTAO)
    if tag == 'button':
        partes.append(_ESTADOS_BOTAO)
    partes.append(
        _VARIANTES_BOTAO.get(variant or 'primary', _VARIANTES_BOTAO['primary'])
    )
    partes.append(_TAMANHOS_BOTAO.get(size or 'md', _TAMANHOS_BOTAO['md']))
    if full_width_mobile:
        partes.append('w-full sm:w-auto')
    if extra:
        partes.append(str(extra))
    return ' '.join(partes)


_PAINEL_DECISAO = {
    'info': 'bg-primary-subtle border-primary-border text-primary-text-strong',
    'warning': 'bg-warning-subtle border-warning-border text-warning-text-strong',
    'danger': 'bg-danger-subtle border-danger-border text-danger-text-strong',
}
_PAINEL_DECISAO_FALLBACK = 'bg-danger border-danger-hover text-text-on-primary'


@register.simple_tag
def classes_painel_decisao(variant: str = '') -> dict[str, Any]:
    """Resolve a superfície do painel de decisão de workflow (#127).

    O mapa vivia reescrito em `_confirmacao_acao_corpo.html` e em
    `_confirmacao_acao_banner_corpo.html`, só para colorir o `<h2>`/`<h3>` —
    dois switches que precisavam concordar com o do `alert.html` sem nada
    garantindo isso. Aqui ele existe uma vez e é testável sozinho, como
    `classes_botao`.

    Uma classe de texto só para a caixa inteira: título, descrição e o glifo de
    `_icone_nivel.html` herdam por `currentColor`. É o mesmo arranjo que a #124
    fixou para o `alert.html`.

    A entrada é vocabulário de design system (`info`/`warning`/`danger`), nunca
    um enum de domínio — o partial de domínio resolve o estado antes de chamar.

    Variante fora do catálogo cai na Decisão A-1 (docs/design-system.md, falha
    alta): fundo `danger` preenchido em vez de `-subtle`, para que a caixa grite
    em vez de virar um painel plausível. `conhecida` e `variante` sustentam a
    linha "Aviso indisponível" e o `data-painel-variant` do chamador.
    """
    conhecida = variant in _PAINEL_DECISAO
    return {
        'conhecida': conhecida,
        'superficie': _PAINEL_DECISAO[variant]
        if conhecida
        else _PAINEL_DECISAO_FALLBACK,
        'variante': variant,
    }


_ABERTURA_MODAL_LITERAL = frozenset({'true', 'false', 'True', 'False'})


@register.simple_tag
def validar_contrato_modal(
    action_url,
    submit_form_id,
    abrir_ao_carregar=None,
    abrir_ao_carregar_expr=None,
    icon_variant=None,
    registro=None,
):
    """Valida o contrato de components/modal.html no render, não em produção.

    Quatro regras. A primeira é o XOR entre `action_url` e `submit_form_id`, que
    são os dois modos do componente.

    A segunda é sobre `abrir_ao_carregar` (#134). O parâmetro passou a emitir
    `open` no `<dialog>`, e a abertura é decidida por um `{% if %}` — para o
    qual a string "false" é verdadeira. Enquanto a abertura era só do Alpine, o
    idioma da casa era `erro|yesno:"true,false"`, porque o destino era uma
    expressão JavaScript; o mesmo filtro chegando aqui abriria **todo** modal,
    inclusive os que não deviam abrir, e sem quebrar nada visível no render.

    `abrir_ao_carregar_expr` era o nome desse parâmetro no partial de
    confirmação e deixou de existir na mesma issue. Um chamador que ressuscite o
    nome antigo — de um branch paralelo, de um copiar e colar — não abriria
    modal nenhum, e um modal que **não** abre é justamente o defeito que a #134
    fechou. O nome morto é recusado em vez de ignorado.

    A terceira é `icon_variant` obrigatório (#136). Antes ele era opcional e o
    resultado era ruído: a severidade de cada modal saía ao acaso de quem
    lembrou de passar o parâmetro, e três dos oito consumidores reais não
    passavam nada — o canal parava de informar bem na vez em que o aviso
    importava (estorno de requisição, estorno de saída excepcional, devolução).
    Uma variante *desconhecida* continua permitida e cai na Decisão A-1 dentro
    de `_modal_icon.html` (falha alta, plausível); o que este contrato recusa é
    a ausência — um `icon_variant` esquecido não pode virar "nenhum ícone" em
    silêncio.

    A quarta é `registro` obrigatório (#138): todo modal nomeia o registro que
    está confirmando. Nenhum dos oito consumidores carregava número público,
    e num bloco de decisão no desktop — a cena declarada do chefe de setor em
    `PRODUCT.md` — a pessoa abre várias requisições em sequência e confirma sem
    âncora nenhuma de qual está na frente. O sistema não tem desfazer.

    Obrigatório em **todo** modal, e não só nos que escrevem movimentação de
    estoque: um recorte por tipo de ação exigiria uma lista de ids "que
    movimentam" mantida em sincronia com o domínio à mão, e deixaria de fora o
    `confirmar-enviar`, que gera o número público. O que cada consumidor tem
    para dizer varia; que ele diga alguma coisa, não.

    A checagem exige `identificador` não vazio, e não só a presença do dict: o
    `{{ registro.identificador }}` do template resolve chave ausente como
    string vazia, então um dict incompleto renderizaria a linha de identidade
    sem identidade — exatamente o defeito, agora com moldura.
    """
    if abrir_ao_carregar_expr:
        raise ImproperlyConfigured(
            'components/modal.html não conhece abrir_ao_carregar_expr (recebido: '
            f'{abrir_ao_carregar_expr!r}). O parâmetro é abrir_ao_carregar, e '
            'espera o bool do contexto.'
        )
    if bool(action_url) == bool(submit_form_id):
        raise ImproperlyConfigured(
            'components/modal.html exige exatamente um entre action_url e '
            'submit_form_id (recebido: '
            f'action_url={action_url!r}, submit_form_id={submit_form_id!r}).'
        )
    if abrir_ao_carregar in _ABERTURA_MODAL_LITERAL:
        raise ImproperlyConfigured(
            'components/modal.html espera um bool em abrir_ao_carregar e '
            f'recebeu a string {abrir_ao_carregar!r} — provavelmente de um '
            '|yesno. Passe o valor do contexto direto: a string "false" é '
            'verdadeira para o template e abriria o modal sempre.'
        )
    if not icon_variant:
        raise ImproperlyConfigured(
            'components/modal.html exige icon_variant (recebido: '
            f'{icon_variant!r}). Toda tela precisa declarar a severidade do '
            'modal — ver a tabela de variantes no {% comment %} deste componente.'
        )
    validar_registro_modal(registro, origem='components/modal.html')
    return ''


def validar_registro_modal(registro: object, *, origem: str) -> None:
    """Exige o `registro` do modal (#138) — usado pelos dois pontos de render.

    `components/modal.html` passa por `validar_contrato_modal`; o fragment 422
    passa por `apps.core.modal.render_modal_erro`, que renderiza
    `_modal_body.html` direto e nunca vê a tag. As duas portas chamam esta
    função para que a mensagem de recusa seja a mesma, e para que o 422 não
    possa devolver um modal anônimo depois de a tela ter aberto um nomeado.
    """
    if not registro:
        raise ImproperlyConfigured(
            f'{origem} exige registro (recebido: {registro!r}). Todo modal '
            'nomeia o registro que está confirmando: passe um dict com '
            "'rotulo', 'identificador' e 'contexto' (opcional)."
        )
    if not isinstance(registro, Mapping):
        raise ImproperlyConfigured(
            f'{origem} espera um mapa em registro e recebeu {type(registro).__name__} '
            f'({registro!r}). As chaves lidas pelo template são "rotulo", '
            '"identificador" e "contexto".'
        )
    if not registro.get('identificador'):
        raise ImproperlyConfigured(
            f'{origem} exige registro["identificador"] não vazio (recebido: '
            f'{registro!r}). É ele que responde "qual documento?" — sem ele a '
            'linha de identidade renderiza vazia em vez de falhar.'
        )


@register.simple_tag
def renderizar_campo_com_aria(
    field: BoundField,
    tem_ajuda: object = False,
    tem_erro: object = False,
    attrs_extra: Mapping[str, Any] | None = None,
    describedby_extra: str = '',
) -> SafeString:
    """Renderiza o BoundField injetando aria-invalid/aria-describedby.

    Único mecanismo do projeto pra passar attrs extras a `{{ field }}` —
    Django não permite isso via linguagem de template pura (chamada de
    método sem argumentos). Usado por components/form_field.html. `field.as_widget`
    mescla os attrs recebidos com os automáticos do widget (`required`,
    `class`, `placeholder` etc. definidos em forms.py não são removidos) —
    mas *substitui* attrs com a mesma chave, então um `aria-describedby` já
    definido no widget é preservado explicitamente aqui (concatenado antes
    dos ids de ajuda/erro) em vez de ser sobrescrito.

    `attrs_extra` existe para o que só a linha sabe: numa linha de formset, o
    `max` vem da quantidade autorizada daquele item e o `x-model` amarra o campo
    ao escopo Alpine daquela linha. Sem isso, a tela é empurrada a escrever o
    `<input>` na mão e perde justamente a fiação ARIA que este tag entrega.

    `describedby_extra` acrescenta ids de texto de apoio que vivem fora do
    componente (ex. um aviso condicional renderizado pela tela).
    """
    attrs: dict[str, Any] = dict(attrs_extra or {})
    describedby_ids: list[str] = []
    describedby_existente = field.field.widget.attrs.get('aria-describedby')
    if describedby_existente:
        describedby_ids.append(str(describedby_existente))
    if describedby_extra:
        describedby_ids.append(str(describedby_extra))
    if tem_ajuda:
        describedby_ids.append(f'{field.id_for_label}-ajuda')
    if tem_erro:
        describedby_ids.append(f'{field.id_for_label}-erro')
        attrs['aria-invalid'] = 'true'
    if describedby_ids:
        attrs['aria-describedby'] = ' '.join(describedby_ids)
    return field.as_widget(attrs=attrs)


@register.simple_tag
def attrs_widget(**kwargs: Any) -> dict[str, Any]:
    """Monta o dict de `attrs_extra` de components/form_field.html.

    A linguagem de template não constrói dicionários, e sem isso uma linha de
    formset não tem como passar ao componente o que só ela sabe. Convenção de
    nomes: `x_bind_required` vira `x-bind:required` (binding Alpine), qualquer
    outro underscore vira hífen (`aria_label` -> `aria-label`).
    """
    convertidos: dict[str, Any] = {}
    for chave, valor in kwargs.items():
        if chave.startswith('x_bind_'):
            atributo = chave.removeprefix('x_bind_').replace('_', '-')
            convertidos[f'x-bind:{atributo}'] = valor
        else:
            convertidos[chave.replace('_', '-')] = valor
    return convertidos


@register.filter
def step_por_unidade(unidade: str) -> str:
    """Passo do <input type="number"> conforme a unidade de medida.

    Espelha a política de precisão de `formatar_quantidade`: se a tela formata
    'un' como inteiro, o campo não pode aceitar 0,001 unidade. Antes as duas
    funções eram mantidas lado a lado na esperança de não divergirem; hoje leem
    a mesma tabela em `apps.core.quantidades`, e divergir deixou de ser possível.
    """
    return quantidades.step(unidade)


def coletar_erros(*fontes: Any, ancora_geral: str = '') -> list[dict[str, str]]:
    """Reúne Forms, FormSets e mensagens soltas numa lista de itens de erro.

    Não é tag de template de propósito: a única porta do template para esta
    função é `{% erros_do_formulario %}`. Enquanto ela era `{% coletar_erros %}`,
    cada tela decidia sozinha o que coletar, em que ordem e onde incluir o
    componente — e três telas já divergiam. Aqui ela é peça interna.

    Cada item é `{'id', 'rotulo', 'mensagem'}` e representa **um alvo**, não uma
    mensagem: `id` é o `id_for_label` do campo, para o sumário poder linkar
    direto ao controle inválido, e `mensagem` traz todas as mensagens daquele
    campo. Um campo com dois erros é um lugar a visitar, não dois — antes ele
    virava duas âncoras para o mesmo `#id`, e a segunda não movia a tela.

    Erros que não pertencem a um campo (`__all__`, `non_form_errors`) entram sem
    `id`, um por mensagem: sem alvo não há chave para agrupar, e agrupá-los pela
    chave vazia colaria erros de origens diferentes numa linha só. Duas exceções,
    ambas contra o sumário repetir a si mesmo: mensagem sem alvo idêntica a outra
    já coletada não entra de novo, e mensagem sem alvo que também chega como erro
    de campo cede o lugar à versão com âncora, que leva ao controle. É o caso de
    um formset que faz `add_error(campo, msg)` **e** `raise ValidationError(msg)`
    — `BaseItemAtendimentoFormSet` faz —, em que a mesma frase chegaria por dois
    caminhos.

    Uma fonte também pode ser uma **string** — a falha que a view já traduziu de
    uma exceção de domínio e que não pertence a campo nenhum, como o erro que os
    modais devolvem no 422. Ela entra pelo mesmo caminho das mensagens sem alvo,
    e portanto herda as mesmas duas proteções contra repetição: uma frase que o
    Form também produziu não aparece duas vezes.

    `ancora_geral` é o destino dessas mensagens sem campo. Sem ele o sumário
    promete o que não cumpre: "A saída precisa ter ao menos um item." fica como
    texto morto no meio de uma lista de links, e quem clica em volta não entende
    por que aquele não leva a lugar nenhum. Ele **não** é chave de agrupamento —
    as mensagens sem campo continuam sendo um item cada, como sempre foram; só
    passam a apontar para o mesmo lugar. Duas âncoras para o mesmo elemento é
    HTML válido e honesto: são dois problemas resolvidos na mesma seção.

    A ordem é a de **primeira aparição** do alvo, e na colisão de `id` entre
    fontes o **primeiro rótulo** é o que fica — o item consolidado é o alvo que
    apareceu antes, e seu rótulo não pode mudar debaixo dele conforme fontes
    posteriores são lidas.

    Apresentação pura: não conhece domínio nem decide o que é erro — só lê o que
    o Form já validou.
    """
    coletados: list[dict[str, str]] = []
    por_alvo: dict[str, dict[str, str]] = {}
    sem_alvo: dict[str, dict[str, str]] = {}
    com_alvo: set[str] = set()

    def _registrar(id_alvo: str, rotulo: str, mensagem: str) -> None:
        if not id_alvo:
            # Perde para a versão com âncora, tenha ela chegado antes ou depois.
            if mensagem in sem_alvo or mensagem in com_alvo:
                return
            item = {'id': ancora_geral, 'rotulo': '', 'mensagem': mensagem}
            sem_alvo[mensagem] = item
            coletados.append(item)
            return

        com_alvo.add(mensagem)
        gemeo = sem_alvo.pop(mensagem, None)
        if gemeo is not None:
            coletados.remove(gemeo)

        alvo = por_alvo.get(id_alvo)
        if alvo is None:
            alvo = {'id': id_alvo, 'rotulo': rotulo, 'mensagem': mensagem}
            por_alvo[id_alvo] = alvo
            coletados.append(alvo)
            return
        alvo['mensagem'] = f'{alvo["mensagem"]} {mensagem}'.strip()

    def _do_form(form: Any) -> None:
        for campo, mensagens in form.errors.items():
            if campo == NON_FIELD_ERRORS:
                for mensagem in mensagens:
                    _registrar('', '', mensagem)
                continue
            bound = form[campo]
            for mensagem in mensagens:
                _registrar(
                    bound.id_for_label or '',
                    str(bound.label or campo),
                    mensagem,
                )

    for fonte in fontes:
        if fonte is None:
            continue
        if isinstance(fonte, (str, Promise)):
            texto = str(fonte).strip()
            if texto:
                _registrar('', '', texto)
        elif hasattr(fonte, 'non_form_errors'):
            for mensagem in fonte.non_form_errors():
                _registrar('', '', mensagem)
            for form in fonte.forms:
                _do_form(form)
        elif hasattr(fonte, 'errors'):
            _do_form(fonte)

    return coletados


@register.inclusion_tag('components/error_summary.html')
def erros_do_formulario(
    *fontes: Any,
    acao: str = 'salvar',
    id: str = 'sumario-erros',
    focar: bool = True,
    ancora_geral: str = '',
) -> dict[str, Any]:
    """Superfície canônica de erro de um formulário. Uma linha por tela.

    É a única porta do template para a exibição de erro de formulário. Antes
    eram duas chamadas acopladas (`{% coletar_erros %}` guardando numa variável,
    `{% include %}` desenhando), o que fazia de cada tela um lugar onde a
    decisão podia sair diferente — e saía: o login montava a própria caixa de
    `non_field_errors` com `alert.html` e escrevia label, campo e erro à mão; as
    três telas de formset usavam o sumário; os modais desenhavam uma terceira
    caixa dentro de `_modal_body.html`. Três grafias para "o formulário falhou".

    O que a tag decide, e a tela não decide mais:
      - **o quê** entra — todo erro de todas as fontes, achatado por
        `coletar_erros`, sem repetição (ver o docstring dela);
      - **onde** aparece — sumário no topo do `<form>`, com âncora por campo, e
        `components/field_error.html` no campo, via `components/form_field.html`.
        As duas pontas não são redundância: o sumário anuncia e navega, o erro
        inline fica ao lado do controle enquanto a pessoa corrige. Quem escolhe
        é este par de componentes, não a tela;
      - **como é anunciado** — `role="alert"` e foco programático no mount.

    A tela só informa o que é seu: quais fontes, e o verbo da frase-líder.

    Parâmetros:
      *fontes  Forms, FormSets e/ou strings (falha que a view já traduziu de uma
               exceção de domínio). `None` é ignorado, o que permite passar um
               contexto opcional sem `{% if %}` na tela.
      acao     (default "salvar") verbo da frase-líder: acao="registrar o
               atendimento" produz "Não foi possível registrar o atendimento:
               2 problemas encontrados." A pluralização fica no componente.
      id       (default "sumario-erros") útil com dois formulários na mesma tela,
               ou quando algo aponta para a caixa via `aria-describedby`.
      focar    (default True) desliga o foco programático onde outro componente
               já governa o foco — hoje só o modal, cujo `modal.js` foca o campo
               inválido. Dois donos do foco brigam; um deles tem de ceder.
      ancora_geral
               id para onde apontam as mensagens que não pertencem a campo
               nenhum (`__all__`, `non_form_errors`, string da view). Sem ele
               esses itens ficam sem link, e o sumário deixa de cumprir a
               terceira coisa que promete: levar até o problema. O alvo certo é
               de cada tela — a seção que contém a falha, ou o campo por onde se
               começa a corrigi-la — e precisa ser focável (`tabindex="-1"`)
               para o foco realmente pousar, não só a rolagem.

    Uso:
      {% erros_do_formulario form formset ancora_geral="sec-materiais" %}
      {% erros_do_formulario cabecalho formset acao="registrar o atendimento" %}
      {% erros_do_formulario form erro_do_servico acao="entrar" id="login-error" %}
    """
    return {
        'erros': coletar_erros(*fontes, ancora_geral=ancora_geral),
        'acao': acao,
        'id': id,
        'focar': focar,
    }


NAVEGACAO: list[dict[str, Any]] = [
    {
        'titulo': 'Navegação',
        'aria_label': 'Navegação',
        'itens': [
            {
                'url_name': 'core:home',
                'rotulo': 'Início',
                'icone': 'inicio',
                'flag': None,
            },
        ],
    },
    {
        'titulo': 'Requisições',
        'aria_label': 'Requisições',
        'itens': [
            {
                'url_name': 'requisicoes:nova_requisicao',
                'rotulo': 'Nova requisição',
                'icone': 'criar',
                'flag': None,
            },
            {
                'url_name': 'requisicoes:minhas',
                'rotulo': 'Minhas requisições',
                'icone': 'lista',
                'flag': None,
            },
            {
                'url_name': 'requisicoes:autorizacoes',
                'rotulo': 'Fila de autorizações',
                'icone': 'autorizacao',
                'flag': 'pode_ver_fila_autorizacao',
            },
            {
                'url_name': 'requisicoes:historico',
                'rotulo': 'Histórico de requisições',
                'icone': 'historico',
                'flag': 'pode_consultar_historico_requisicoes',
            },
        ],
    },
    {
        'titulo': 'Almoxarifado',
        'aria_label': 'Almoxarifado',
        'itens': [
            {
                'url_name': 'requisicoes:atendimentos',
                'rotulo': 'Atendimento',
                'icone': 'atendimento',
                'flag': 'pode_ver_fila_atendimento',
            },
            {
                'url_name': 'estoque:listar_saidas_excepcionais',
                'rotulo': 'Saídas excepcionais',
                'icone': 'saida',
                'flag': 'pode_consultar_saidas_excepcionais',
            },
            {
                'url_name': 'estoque:lista_materiais',
                'rotulo': 'Catálogo de materiais',
                'icone': 'catalogo',
                'flag': 'pode_consultar_catalogo_estoque',
            },
            {
                'url_name': 'estoque:historico_movimentacoes',
                'rotulo': 'Movimentações',
                'icone': 'movimentacao',
                'flag': 'pode_consultar_movimentacoes_estoque',
            },
            {
                'url_name': 'estoque:preview_importacao_scpi',
                'rotulo': 'Importar SCPI',
                'icone': 'importar',
                'flag': 'pode_visualizar_preview_scpi',
                'url_names_ativos': [
                    'estoque:preview_importacao_scpi',
                    'requisicoes:confirmar_importacao_scpi',
                    'estoque:sucesso_importacao_scpi',
                ],
            },
            {
                'url_name': 'estoque:historico_importacoes_scpi',
                'rotulo': 'Histórico de importações SCPI',
                'icone': 'historico',
                'flag': 'pode_consultar_historico_scpi',
            },
        ],
    },
]

ICONES: dict[str, str] = {
    'inicio': 'M12 3 2 11h3v8h6v-6h2v6h6v-8h3L12 3z',
    'criar': 'M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z',
    'lista': 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
    'autorizacao': (
        'M12 2 4 5v6c0 5.55 3.84 10.74 8 12 4.16-1.26 8-6.45 8-12V5l-8-3zm-1 14'
        '-4-4 1.41-1.41L11 13.17l5.59-5.59L18 9l-7 7z'
    ),
    'historico': 'M13 3a9 9 0 1 0 9 9h-2a7 7 0 1 1-7-7v4l5-5-5-5v4z',
    'atendimento': (
        'M20 8h-3V6c0-1.1-.9-2-2-2H9c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v9c0 1.1'
        '.9 2 2 2h16c1.1 0 2-.9 2-2v-9c0-1.1-.9-2-2-2zM9 6h6v2H9V6zm11 13H4v-2h16'
        'v2zm0-4H4v-5h3v2h2v-2h6v2h2v-2h3v5z'
    ),
    'saida': (
        'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2'
        '-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l7.59-7.59L21 8l-9 9z'
    ),
    'catalogo': (
        'M20 3H4v2h16V3zm1 5H3l1 13h16l1-13zm-5 7h-3v3h-2v-3H8v-2h3V10h2v3h3v2z'
    ),
    'movimentacao': (
        'M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7'
        'v2zM7 7v2h14V7H7z'
    ),
    'importar': 'M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z',
}


@register.simple_tag(takes_context=True)
def secoes_navegacao(context: Any) -> list[dict[str, Any]]:
    """Devolve as seções de nav visíveis, lidas de NAVEGACAO/ICONES.

    Filtra itens pela flag de permissão já presente no contexto (sem
    reimplementar policy) e descarta seções sem nenhum item visível.
    Constrói dicts/listas novos a cada chamada — nunca muta NAVEGACAO/ICONES.
    """
    secoes: list[dict[str, Any]] = []
    for secao in NAVEGACAO:
        itens: list[dict[str, Any]] = []
        for item in secao['itens']:
            flag = item.get('flag')
            if flag is not None and not context.get(flag):
                continue
            itens.append(
                {
                    'url_name': item['url_name'],
                    'rotulo': item['rotulo'],
                    'icone_path': ICONES[item['icone']],
                    'url_names_ativos': list(
                        item.get('url_names_ativos', [item['url_name']])
                    ),
                }
            )
        if itens:
            secoes.append(
                {
                    'titulo': secao['titulo'],
                    'aria_label': secao['aria_label'],
                    'itens': itens,
                }
            )
    return secoes


@register.simple_tag
def agrupar_opcoes(
    opcoes: Iterable[tuple[Any, Any]],
    *especificacoes: str,
) -> list[tuple[str, list[tuple[Any, Any]]]]:
    """Reparte `opcoes` (pares valor/rótulo) em grupos rotulados, preservando
    os valores originais.

    Usado pelo filtro de estado do histórico de requisições (issue #154), que
    agrupa os 8 estados em "Em andamento" e "Encerradas" sem colapsar as caixas
    nem mudar a querystring — cada grupo vira um ``<fieldset>``/``<legend>`` em
    ``components/filter_checkbox_group.html``.

    ``especificacoes`` alterna legenda e os valores do grupo separados por
    espaço::

        {% agrupar_opcoes estados_opcoes
           "Em andamento" "rascunho aguardando_autorizacao autorizada pronta_para_retirada"
           "Encerradas" "recusada atendida cancelada estornada" as estados_grupos %}

    Erra alto (`ImproperlyConfigured`) se a partição não cobrir exatamente os
    valores de `opcoes` uma única vez — assim uma mudança em `EstadoRequisicao`
    não passa silenciosa pelo template.
    """
    if len(especificacoes) % 2 != 0:
        raise ImproperlyConfigured('agrupar_opcoes espera pares (legenda, valores).')
    rotulo_por_valor = {valor: rotulo for valor, rotulo in opcoes}
    grupos: list[tuple[str, list[tuple[Any, Any]]]] = []
    vistos: set[Any] = set()
    for legenda, valores_brutos in zip(especificacoes[::2], especificacoes[1::2]):
        pares: list[tuple[Any, Any]] = []
        for valor in valores_brutos.split():
            if valor not in rotulo_por_valor:
                raise ImproperlyConfigured(
                    f'agrupar_opcoes: valor desconhecido {valor!r}.'
                )
            if valor in vistos:
                raise ImproperlyConfigured(f'agrupar_opcoes: valor repetido {valor!r}.')
            vistos.add(valor)
            pares.append((valor, rotulo_por_valor[valor]))
        grupos.append((legenda, pares))
    faltando = set(rotulo_por_valor) - vistos
    if faltando:
        raise ImproperlyConfigured(
            f'agrupar_opcoes: valores não agrupados: {sorted(faltando)}.'
        )
    return grupos
