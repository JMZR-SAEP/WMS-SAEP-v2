"""Views de requisições — finas por definição (ADR-0004).

Fluxo: ler input → chamar service com IDs → traduzir exceção → renderizar/redirect.
Nenhuma regra de domínio, query de escopo ou decisão de autorização própria.
"""

from decimal import Decimal

from apps.accounts.papeis import PapelEfetivo, papel_efetivo
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
    Sum,
)
from django.forms import BooleanField
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.exceptions import (
    ConflitoDominio,
    DadosInvalidos,
    ErroDominio,
    EstadoInvalido,
    PermissaoNegada,
)
from apps.core.filtros import montar_chip, montar_presets_periodo
from apps.core.http import htmx_redirect, parse_data_iso, voltar_url_seguro
from apps.core.listagem import contar_filtros_ativos, paginar, paginar_com_filtros
from apps.core.modal import render_modal_erro
from apps.core.presentation import traduz_erro_dominio
from apps.core.querystring import caminho_canonico
from apps.requisicoes.presentation import MODAL_COPY
from apps.requisicoes.presentation import cancelamento_copy, registro_requisicao
from apps.core.quantidades import formatar as formatar_quantidade
from apps.core.templatetags.core_tags import coletar_erros
from apps.core.quantidades import normalizar
from apps.estoque.models import SaldoEstoque
from apps.estoque.selectors import entregue_liquida_por_requisicao
from apps.requisicoes.forms import (
    ItemAtendimentoFormSet,
    ItemRequisicaoFormSet,
    RegistrarAtendimentoCabecalhoForm,
    EstornarRequisicaoForm,
    RegistrarDevolucaoForm,
    RequisicaoCriacaoForm,
    RequisicaoForm,
)
from apps.requisicoes.models import (
    EstadoRequisicao,
    ItemRequisicao,
    Operacao,
    Requisicao,
)
from apps.requisicoes.policies import (
    exigir_pode_consultar_historico_requisicoes,
    exigir_pode_editar_rascunho,
    exigir_pode_ver_fila_atendimento,
    exigir_pode_ver_fila_autorizacao,
    pode_atender_retirada,
    pode_copiar_requisicao,
    pode_ver_fila_autorizacao,
    resolver_escopo_criacao_requisicao,
)
from apps.requisicoes.selectors import (
    acoes_disponiveis,
    fila_atendimento,
    fila_autorizacao,
    filtrar_historico_requisicoes,
    historico_requisicoes_visiveis_para,
    materiais_para_requisicao,
    minhas_requisicoes,
    pode_filtrar_historico_por_setor,
    requisicoes_visiveis_para,
    saldos_por_materiais,
    setores_do_historico,
)
from apps.requisicoes.services import (
    ESTADOS_COPIAVEIS,
    autorizar_requisicao,
    copiar_requisicao,
    criar_e_enviar_requisicao,
    criar_requisicao,
    cancelar_requisicao,
    editar_rascunho,
    enviar_para_autorizacao,
    recusar_requisicao,
    registrar_atendimento,
    estornar_requisicao,
    registrar_devolucao,
    retornar_para_rascunho,
    separar_para_retirada,
)
from apps.requisicoes.transitions import (
    ESTADOS_COM_QUANTIDADE_AUTORIZADA,
    ESTADOS_COM_QUANTIDADE_ENTREGUE,
    cancelamento_info,
)


def _voltar_url(request, default: str = '') -> str:
    return voltar_url_seguro(request, default=default or reverse('requisicoes:minhas'))


def _pode_copiar_agora(papel: PapelEfetivo, requisicao: Requisicao) -> bool:
    """Estado copiável + permissão do ator.

    Mesma pergunta que o detalhe faz para mostrar o botão e que a confirmação de
    cópia faz para existir — uma função só, para a tela nunca oferecer o que o
    service vai recusar.
    """
    return requisicao.estado in ESTADOS_COPIAVEIS and pode_copiar_requisicao(
        papel, requisicao
    )


def _detalhe_context(
    request,
    requisicao: Requisicao,
    *,
    recusa_erro: str = '',
    motivo_recusa: str = '',
    cancelacao_erro: str = '',
    justificativa_cancelamento: str = '',
    cancelamento_modal_aberto: bool = False,
):
    from apps.estoque.policies import pode_consultar_saidas_excepcionais

    papel = papel_efetivo(request.user)
    acoes = acoes_disponiveis(papel, requisicao)
    itens = list(requisicao.itens.select_related('material').all())
    itens_devolviveis: list[ItemRequisicao] = []
    # A entregue líquida serve às duas operações e é uma consulta só: a
    # devolução para dizer quanto ainda dá para devolver, o estorno para nomear
    # no modal o que vai voltar ao saldo físico (#138). Ficava dentro do ramo da
    # devolução, e o modal de estorno — que reverte exatamente estes números —
    # não tinha acesso a nenhum deles.
    # A entregue líquida é LEITURA, não privilégio. Ela vivia só dentro do ramo
    # das duas operações de escrita, então o beneficiário — dono do pedido — via
    # `ENTREGUE 6` e nunca sabia que 2 tinham voltado ao estoque. O PRODUCT.md a
    # declara derivada das movimentações; derivar e esconder é o pior dos dois
    # mundos. A consulta é uma só e já era feita aqui.
    algum_entregue = any(i.quantidade_entregue is not None for i in itens)
    precisa_liquida = algum_entregue or bool(
        {Operacao.REGISTRAR_DEVOLUCAO, Operacao.ESTORNAR} & set(acoes)
    )
    if precisa_liquida:
        entregues = entregue_liquida_por_requisicao(requisicao_id=requisicao.pk)
        for item in itens:
            item.entregue_liquida = entregues.get(item.material_id, Decimal('0'))
            item.modal_devolver_id = f'devolver-{item.pk}'
            # Só aparece quando diverge do entregue bruto: se nada voltou, uma
            # segunda linha com o mesmo número é ruído numa tela já densa.
            bruto = item.quantidade_entregue
            if bruto is not None and item.entregue_liquida != bruto:
                item.entregue_liquida_exibida = item.entregue_liquida
                devolvido = bruto - item.entregue_liquida
                item.rotulo_devolucao = (
                    f'{formatar_quantidade(devolvido, item.material.unidade)} '
                    f'{item.material.get_unidade_display()} de volta ao estoque'
                )
            if item.entregue_liquida > 0 and Operacao.REGISTRAR_DEVOLUCAO in acoes:
                itens_devolviveis.append(item)
    # A operação estar disponível não basta: com tudo já devolvido a seção não
    # teria linha nenhuma. A lista é que decide se o bloco existe.
    pode_devolver = Operacao.REGISTRAR_DEVOLUCAO in acoes and bool(itens_devolviveis)
    eventos = list(
        requisicao.eventos.select_related('ator').order_by('-criado_em', '-id')
    )
    enviada_em = None
    if requisicao.estado != EstadoRequisicao.RASCUNHO:
        enviada_em = next(
            (e.criado_em for e in eventos if e.evento == 'envio_autorizacao'),
            None,
        )
    cancelavel = Operacao.CANCELAR in acoes
    info_cancelamento = cancelamento_info(requisicao) if cancelavel else None

    pode_copiar = _pode_copiar_agora(papel, requisicao)

    # Saldo por item quando a decisão é autorizar. Autorizar RESERVA estoque, e
    # esta era a única escrita do produto confirmada com zero números na tela: o
    # modal dizia "reserva o saldo necessário para todos os itens" sem dizer
    # quanto, de quê, nem se existe. O chefe descobria o problema depois de
    # confirmar. Uma consulta só, e só no estado em que ela decide algo.
    if Operacao.AUTORIZAR in acoes:
        saldos = saldos_por_materiais([i.material_id for i in itens])
        for item in itens:
            info = saldos.get(item.material_id)
            if info is None:
                continue
            item.saldo_disponivel_exibido = info['saldo_disponivel']
            item.saldo_insuficiente = (
                info['saldo_disponivel'] < item.quantidade_solicitada
            )
            item.saldo_motivo = info['motivo']

    # `item_erro` chega da querystring quando uma tentativa de autorização
    # barrou por saldo: o service diz qual material, a view repassa, e a lista
    # marca a linha. Nada além de marcar — a mensagem já está na faixa.
    item_erro_bruto = request.GET.get('item_erro', '')
    item_erro_id = int(item_erro_bruto) if item_erro_bruto.isdigit() else None
    for item in itens:
        item.tem_erro = item.material_id == item_erro_id

    return {
        'requisicao': requisicao,
        'itens': itens,
        'eventos': eventos,
        # A timeline linka o número da saída excepcional que causou a
        # divergência EST-07 — mas só para quem pode abrir a tela de destino.
        # `detalhe_saida_excepcional_view` exige
        # `pode_consultar_saidas_excepcionais`, então um link incondicional
        # levaria o solicitante da requisição direto a um 403. Sem a permissão,
        # o número continua em texto, que é o que ele já era.
        'pode_consultar_saidas_excepcionais': pode_consultar_saidas_excepcionais(papel),
        # Linha de identidade dos seis modais desta tela (#138). Uma chave só
        # no contexto, passada explicitamente por cada `{% include %}` — a tela
        # não escreve "qual requisição é esta" seis vezes.
        'registro': registro_requisicao(requisicao),
        'voltar_url': _voltar_url(request),
        'pode_enviar': Operacao.ENVIAR_PARA_AUTORIZACAO in acoes,
        'pode_editar': Operacao.EDITAR_RASCUNHO in acoes,
        'pode_retornar': Operacao.RETORNAR_PARA_RASCUNHO in acoes,
        'pode_autorizar': Operacao.AUTORIZAR in acoes,
        'pode_recusar': Operacao.RECUSAR in acoes,
        'pode_separar_retirada': Operacao.SEPARAR_PARA_RETIRADA in acoes,
        'pode_atender_retirada': Operacao.REGISTRAR_ATENDIMENTO in acoes,
        'pode_cancelar': cancelavel,
        # Cancelar convive com editar/enviar no bloco de rascunho; nos demais
        # estados vira banner próprio. É decisão de layout, por isso mora aqui
        # e não em `cancelamento_info`, que descreve efeitos de domínio.
        'cancelamento_inline': requisicao.estado == EstadoRequisicao.RASCUNHO,
        'pode_copiar': pode_copiar,
        'cancelamento_info': info_cancelamento,
        'cancelamento_requer_justificativa': (
            info_cancelamento.requer_justificativa if info_cancelamento else False
        ),
        'cancelamento_erro': cancelacao_erro,
        'justificativa_cancelamento': justificativa_cancelamento,
        'cancelamento_modal_aberto': cancelamento_modal_aberto or bool(cancelacao_erro),
        'recusa_erro': recusa_erro,
        'motivo_recusa': motivo_recusa,
        'cancelamento_hidden_inputs': {'next': _voltar_url(request)},
        'recusar_hidden_inputs': {'next': _voltar_url(request)},
        'retornar_hidden_inputs': {'next': _voltar_url(request)},
        'autorizar_hidden_inputs': {'next': _voltar_url(request)},
        'enviar_hidden_inputs': {'next': _voltar_url(request)},
        'separar_hidden_inputs': {'next': _voltar_url(request)},
        'enviada_em': enviada_em,
        'mostrar_quantidade_autorizada': (
            requisicao.estado in ESTADOS_COM_QUANTIDADE_AUTORIZADA
        ),
        'mostrar_quantidade_entregue': (
            requisicao.estado in ESTADOS_COM_QUANTIDADE_ENTREGUE
        ),
        'pode_devolver': pode_devolver,
        'itens_devolviveis': itens_devolviveis,
        'devolucao_form': RegistrarDevolucaoForm(),
        'pode_estornar': Operacao.ESTORNAR in acoes,
        'estorno_form': EstornarRequisicaoForm(),
        # Mesma lista da devolução: item com entregue líquida > 0. É o conjunto
        # exato que o estorno devolve ao saldo físico, e o corpo do modal o
        # repete item a item (#138).
        'itens_a_estornar': itens_devolviveis,
    }


def _render_detalhe(request, requisicao: Requisicao, **contexto_extra):
    return render(
        request,
        'requisicoes/detalhe.html',
        _detalhe_context(request, requisicao, **contexto_extra),
    )


def _texto_dos_erros(form) -> str:
    """Junta as mensagens do Form numa frase, para o fallback sem HTMX.

    Substitui `form.errors.as_text()`, cujo dump (`* justificativa\\n  * Este
    campo é obrigatório.`) chegava à tela com o asterisco de formatação de log.
    O caminho com HTMX não passa por aqui: lá o Form vai inteiro para
    `{% erros_do_formulario %}`, que preserva a âncora por campo.

    Sai por `coletar_erros`, a mesma porta que a tag usa, e **mantém o rótulo
    do campo**. Tirar o asterisco estava certo; tirar o rótulo não estaria:
    esta frase chega por `messages.error` na tela de detalhe, depois do
    redirect, onde não há formulário nenhum — "Este campo é obrigatório." numa
    página sem campos não diz o que fazer. Hoje os dois forms têm um campo só
    que pode errar, então a ambiguidade não aparece; ela apareceria calada no
    dia em que ganhassem o segundo.
    """
    partes = [
        f'{item["rotulo"]}: {item["mensagem"]}' if item['rotulo'] else item['mensagem']
        for item in coletar_erros(form)
    ]
    return ' '.join(partes)


# ---------------------------------------------------------------------------
# Home do módulo
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Nova requisição — TR-001
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['GET', 'POST'])
def nova_requisicao(request):
    papel = papel_efetivo(request.user)
    try:
        escopo = resolver_escopo_criacao_requisicao(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    if request.method == 'POST':
        form = RequisicaoCriacaoForm(
            request.POST,
            modo_beneficiario=escopo.modo_beneficiario,
            beneficiarios=escopo.beneficiarios,
        )
        formset = ItemRequisicaoFormSet(request.POST, prefix='itens')

        if form.is_valid() and formset.is_valid():
            if escopo.modo_beneficiario == 'proprio':
                beneficiario_id = request.user.pk
            else:
                modo = form.cleaned_data.get('modo_criacao')
                if modo == 'proprio':
                    beneficiario_id = request.user.pk
                else:
                    beneficiario_id = int(form.cleaned_data['beneficiario_id'])

            itens = formset.linhas_validas()
            acao = request.POST.get('acao', 'rascunho')

            try:
                if acao == 'enviar':
                    req = criar_e_enviar_requisicao(
                        ator_id=request.user.pk,
                        beneficiario_id=beneficiario_id,
                        itens=itens,
                        observacao_geral=form.cleaned_data.get('observacao_geral', ''),
                    )
                else:
                    req = criar_requisicao(
                        ator_id=request.user.pk,
                        beneficiario_id=beneficiario_id,
                        itens=itens,
                        observacao_geral=form.cleaned_data.get('observacao_geral', ''),
                    )
            except (PermissaoNegada, DadosInvalidos) as exc:
                messages.error(request, str(exc))
            except (EstadoInvalido, ConflitoDominio) as exc:
                messages.warning(request, str(exc))
            else:
                if acao == 'enviar':
                    messages.success(
                        request,
                        f'Requisição enviada para autorização. Número {req.numero_publico}.',
                    )
                    return redirect('requisicoes:detalhe', pk=req.pk)
                messages.success(
                    request,
                    'Rascunho criado com sucesso. Revise os itens antes de enviar para autorização.',
                )
                return redirect('requisicoes:detalhe', pk=req.pk)

        return render(
            request,
            'requisicoes/rascunho_form.html',
            {
                'form': form,
                'formset': formset,
                'modo': 'criar',
                'escopo': escopo,
            },
        )

    # GET
    form = RequisicaoCriacaoForm(
        modo_beneficiario=escopo.modo_beneficiario,
        beneficiarios=escopo.beneficiarios,
    )
    formset = ItemRequisicaoFormSet(prefix='itens', initial=[{}])
    return render(
        request,
        'requisicoes/rascunho_form.html',
        {
            'form': form,
            'formset': formset,
            'modo': 'criar',
            'escopo': escopo,
        },
    )


# ---------------------------------------------------------------------------
# Editar rascunho — TR-002
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['GET', 'POST'])
def editar_rascunho_view(request, pk: int):
    """Edita os itens e a observação geral de um rascunho.

    Escopo de visibilidade unificado por ``requisicoes_visiveis_para``; objetos
    fora do escopo retornam 404 (ADR-0010) para não revelar existência. Os 403
    seguintes são de ação proibida em objeto visível: ator não-criador e estado
    diferente de rascunho.
    """
    requisicao = get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_editar_rascunho(papel, requisicao)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    # Estado precisa ser RASCUNHO — 403 é mais correto que 404 aqui
    if requisicao.estado != 'rascunho':
        raise PermissionDenied('Esta requisição não está em rascunho.')

    if request.method == 'POST':
        form = RequisicaoForm(request.POST)
        formset = ItemRequisicaoFormSet(request.POST, prefix='itens')

        if form.is_valid() and formset.is_valid():
            itens = formset.linhas_validas()
            try:
                editar_rascunho(
                    ator_id=request.user.pk,
                    requisicao_id=requisicao.pk,
                    itens=itens,
                    observacao_geral=form.cleaned_data.get('observacao_geral', ''),
                )
            except PermissaoNegada as exc:
                raise PermissionDenied(str(exc))
            except ErroDominio as exc:
                pres = traduz_erro_dominio(exc)
                getattr(messages, pres.severity)(request, str(exc))
            else:
                messages.success(request, 'Rascunho salvo com sucesso.')
                return redirect('requisicoes:detalhe', pk=requisicao.pk)

        return render(
            request,
            'requisicoes/rascunho_form.html',
            {
                'form': form,
                'formset': formset,
                'modo': 'editar',
                'requisicao': requisicao,
            },
        )

    # GET — preencher com itens existentes
    itens_existentes = list(requisicao.itens.select_related('material').all())
    material_ids = [item.material_id for item in itens_existentes]
    saldo_info = saldos_por_materiais(material_ids)
    tem_item_inelegivel = any(not v['elegivel'] for v in saldo_info.values())

    initial = [
        {
            'material_id': item.material_id,
            'material_label': str(item.material),
            'quantidade_solicitada': int(item.quantidade_solicitada)
            if item.quantidade_solicitada
            else '',
        }
        for item in itens_existentes
    ]
    form = RequisicaoForm(initial={'observacao_geral': requisicao.observacao_geral})
    formset = ItemRequisicaoFormSet(prefix='itens', initial=initial or [{}])

    # saldo_info keyed by str(material_id) for template dict lookup
    saldo_info_str = {str(k): v for k, v in saldo_info.items()}

    return render(
        request,
        'requisicoes/rascunho_form.html',
        {
            'form': form,
            'formset': formset,
            'modo': 'editar',
            'requisicao': requisicao,
            'saldo_info': saldo_info_str,
            'tem_item_inelegivel': tem_item_inelegivel,
        },
    )


# ---------------------------------------------------------------------------
# HTMX: nova linha de item
# ---------------------------------------------------------------------------


@login_required
@require_GET
def nova_linha_item(request):
    """Retorna partial HTML com nova linha vazia do formset."""
    try:
        index = int(request.GET.get('index', 0))
    except (ValueError, TypeError):
        index = 0

    form = ItemRequisicaoFormSet.form(prefix=f'itens-{index}')
    form.fields[DELETION_FIELD_NAME] = BooleanField(label='Deletar', required=False)
    return render(
        request,
        'components/item_form_row.html',
        {
            'material_id_field': form['material_id'],
            'material_label_field': form['material_label'],
            'quantidade_field': form['quantidade_solicitada'],
            'quantidade_label': 'Quantidade',
            'autocomplete_url_name': 'requisicoes:buscar_materiais',
            'autocomplete_item_template': 'estoque/partials/_autocomplete_item_material.html',
            'delete_field': form[DELETION_FIELD_NAME],
            'form_index': index,
        },
    )


# ---------------------------------------------------------------------------
# JSON: autocomplete de materiais
# ---------------------------------------------------------------------------


@login_required
@require_GET
def buscar_materiais(request):
    """Retorna materiais elegíveis para autocomplete (JSON)."""
    papel = papel_efetivo(request.user)
    try:
        resolver_escopo_criacao_requisicao(papel)
    except PermissaoNegada:
        return JsonResponse(
            {'error': 'Sem permissão para buscar materiais.'}, status=403
        )

    q = request.GET.get('q', '').strip()
    materiais = list(materiais_para_requisicao(q=q, limite=20))
    material_ids = [m.pk for m in materiais]

    saldo_por_material: dict = {}
    if material_ids:
        for row in (
            SaldoEstoque.objects.filter(material_id__in=material_ids)
            .values('material_id')
            .annotate(
                disponivel=Sum(
                    ExpressionWrapper(
                        F('saldo_fisico') - F('saldo_reservado'),
                        output_field=DecimalField(),
                    )
                )
            )
        ):
            saldo_por_material[row['material_id']] = row['disponivel']

    resultado = [
        {
            'id': m.pk,
            'codigo': m.codigo,
            'nome': m.nome,
            'unidade': m.unidade,
            'label': f'{m.codigo} — {m.nome}',
            'saldo_disponivel': formatar_quantidade(
                saldo_por_material.get(m.pk, 0), m.unidade
            ),
            # O mesmo saldo em notação de máquina. `saldo_disponivel` já vem
            # formatado em pt-BR, com vírgula, e `Number()` não lê vírgula — sem
            # este par o aviso de "acima do saldo" compararia contra NaN e nunca
            # dispararia. Formatado para ler, cru para comparar.
            'saldo_bruto': str(saldo_por_material.get(m.pk, 0)),
        }
        for m in materiais
    ]

    return JsonResponse({'resultados': resultado})


@login_required
@require_GET
def buscar_beneficiarios(request):
    """Retorna beneficiários elegíveis para autocomplete (JSON).

    Restrição de escopo idêntica à de criação de requisição.
    """
    papel = papel_efetivo(request.user)
    try:
        escopo = resolver_escopo_criacao_requisicao(papel)
    except PermissaoNegada:
        return JsonResponse(
            {'error': 'Sem permissão para buscar beneficiários.'}, status=403
        )

    q = request.GET.get('q', '').strip()
    qs = escopo.beneficiarios
    if q:
        qs = qs.filter(nome__icontains=q) | qs.filter(matricula__icontains=q)

    resultado = [
        {
            'id': u.pk,
            'nome': u.nome,
            'matricula': u.matricula,
            'setor': u.setor.nome if u.setor else '',
            'label': f'{u.nome} ({u.matricula})',
        }
        for u in qs[:20]
    ]

    return JsonResponse({'resultados': resultado})


# ---------------------------------------------------------------------------
# Minhas requisições — lista
# ---------------------------------------------------------------------------


PAGINA_MINHAS_REQUISICOES_TAMANHO = 25
PAGINA_FILA_TAMANHO = 25


@login_required
@require_GET
def minhas_requisicoes_view(request):
    """Lista as requisições onde o usuário é criador ou beneficiário.

    Rascunhos de terceiros são filtrados pelo selector. Paginado: a lista
    cresce monotonicamente ao longo da vida do usuário e não tem filtro.
    """
    # O cartão precisa nomear o material: esta é a tela do solicitante e a
    # única que o produto declara operada no celular (PRODUCT.md), e ela era a
    # única das sete listagens que não dizia o que a requisição pede. Subquery
    # pelo mesmo motivo do histórico e das duas filas — um
    # `prefetch_related('itens__material')` carregaria as N linhas de toda
    # requisição da página para exibir, no máximo, um nome por cartão.
    primeiro_material_sq = Subquery(
        ItemRequisicao.objects.filter(requisicao=OuterRef('pk'))
        .order_by('pk')
        .values('material__nome')[:1]
    )
    requisicoes = minhas_requisicoes(request.user.pk).annotate(
        quantidade_itens=Count('itens'),
        primeiro_material_nome=primeiro_material_sq,
    )
    page_obj = paginar(request, requisicoes, per_page=PAGINA_MINHAS_REQUISICOES_TAMANHO)
    return render(
        request,
        'requisicoes/lista_minhas.html',
        {'page_obj': page_obj, 'requisicoes': page_obj.object_list},
    )


# ---------------------------------------------------------------------------
# Fila de autorização — lista
# ---------------------------------------------------------------------------


@login_required
@require_GET
def fila_autorizacao_view(request):
    """Lista requisições aguardando autorização no escopo da chefia."""
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_ver_fila_autorizacao(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    requisicoes = fila_autorizacao(request.user.pk)
    page_obj = paginar(request, requisicoes, per_page=PAGINA_FILA_TAMANHO)
    return render(
        request,
        'requisicoes/fila_autorizacao.html',
        {'page_obj': page_obj, 'requisicoes': page_obj.object_list},
    )


# ---------------------------------------------------------------------------
# Autorizar requisição — TR-008
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['POST'])
def autorizar_requisicao_view(request, pk: int):
    """Autoriza integralmente uma requisição e reserva saldo."""
    get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)
    try:
        requisicao = autorizar_requisicao(
            ator_id=request.user.pk,
            requisicao_id=pk,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except ConflitoDominio as exc:
        messages.warning(request, str(exc))
        # O material que barrou a reserva volta na querystring para o detalhe
        # marcar o item. A faixa no topo diz o que aconteceu; sem isto o
        # operador ainda precisa varrer a lista de itens com o olho para achar
        # qual deles a mensagem nomeia.
        destino = reverse('requisicoes:detalhe', args=[pk])
        material_id = exc.detalhes.get('material_id')
        if material_id:
            destino = f'{destino}?item_erro={material_id}'
        return htmx_redirect(request, destino)
    except DadosInvalidos as exc:
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    messages.success(
        request,
        f'Requisição {requisicao.numero_publico} autorizada com sucesso.',
    )
    detalhe_url = reverse('requisicoes:detalhe', args=[requisicao.pk])
    return htmx_redirect(request, _voltar_url(request, default=detalhe_url))


@login_required
@require_GET
def fila_atendimento_view(request):
    """Lista requisições autorizadas/prontas para almoxarifado."""
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_ver_fila_atendimento(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    requisicoes = fila_atendimento(request.user.pk)
    page_obj = paginar(request, requisicoes, per_page=PAGINA_FILA_TAMANHO)
    return render(
        request,
        'requisicoes/fila_atendimento.html',
        {'page_obj': page_obj, 'requisicoes': page_obj.object_list},
    )


@login_required
@require_http_methods(['POST'])
def separar_retirada_view(request, pk: int):
    """Aplica TR-015 (autorizada -> pronta_para_retirada)."""
    get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)
    try:
        requisicao = separar_para_retirada(
            ator_id=request.user.pk,
            requisicao_id=pk,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except DadosInvalidos as exc:
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    numero = requisicao.numero_publico or f'#{requisicao.pk}'
    messages.success(
        request,
        f'Requisição {numero} pronta para retirada.',
    )
    detalhe_url = reverse('requisicoes:detalhe', args=[requisicao.pk])
    return htmx_redirect(request, _voltar_url(request, default=detalhe_url))


@login_required
@require_http_methods(['GET', 'POST'])
def registrar_atendimento_view(request, pk: int):
    """Aplica TR-016/017 (pronta_para_retirada -> atendida) com total ou parcial."""
    requisicao = get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)

    if requisicao.estado != EstadoRequisicao.PRONTA_PARA_RETIRADA:
        messages.warning(request, 'Esta requisição não está pronta para retirada.')
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    papel = papel_efetivo(request.user)
    if not pode_atender_retirada(papel, requisicao):
        raise PermissionDenied(
            'Você não tem permissão para registrar o atendimento desta requisição.'
        )

    itens_autorizados = list(
        requisicao.itens.select_related('material')
        .filter(quantidade_autorizada__gt=0)
        .order_by('id')
    )

    def _render(cabecalho_form, formset_form, *, status=200):
        linhas = list(zip(itens_autorizados, formset_form.forms))
        return render(
            request,
            'requisicoes/atender_retirada.html',
            {
                'requisicao': requisicao,
                'itens': itens_autorizados,
                'cabecalho': cabecalho_form,
                'formset': formset_form,
                'linhas': linhas,
                'registro': registro_requisicao(requisicao),
                'voltar_url': _voltar_url(
                    request, default=reverse('requisicoes:detalhe', args=[pk])
                ),
            },
            status=status,
        )

    item_ids_permitidos = [item.id for item in itens_autorizados]

    if request.method == 'GET':
        cabecalho = RegistrarAtendimentoCabecalhoForm()
        formset = ItemAtendimentoFormSet(
            # A quantidade autorizada vem do banco com as 3 casas do
            # DecimalField (`1.000`), e o navegador exibe isso em pt-BR como
            # `1,000` — mil, num campo que dá baixa em estoque. `normalizar`
            # tira só os zeros à direita, sem arredondar: um campo que reescreve
            # o número recebido faria a pessoa confirmar valor diferente do
            # autorizado sem perceber.
            initial=[
                {
                    'item_id': item.id,
                    'quantidade_entregue': normalizar(item.quantidade_autorizada),
                    'justificativa': '',
                }
                for item in itens_autorizados
            ],
            prefix='itens',
            item_ids_permitidos=item_ids_permitidos,
        )
        return _render(cabecalho, formset)

    cabecalho = RegistrarAtendimentoCabecalhoForm(request.POST)
    formset = ItemAtendimentoFormSet(
        request.POST,
        prefix='itens',
        item_ids_permitidos=item_ids_permitidos,
    )

    cabecalho_valido = cabecalho.is_valid()
    formset_valido = formset.is_valid()
    if not (cabecalho_valido and formset_valido):
        messages.error(request, 'Corrija os campos destacados.')
        return _render(cabecalho, formset, status=400)

    try:
        requisicao = registrar_atendimento(
            ator_id=request.user.pk,
            requisicao_id=pk,
            itens=formset.linhas_atendimento(),
            retirante_nome=cabecalho.cleaned_data['retirante_nome'],
            observacao=cabecalho.cleaned_data.get('observacao', ''),
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except ConflitoDominio as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except DadosInvalidos as exc:
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    numero = requisicao.numero_publico or f'#{requisicao.pk}'
    messages.success(
        request,
        f'Retirada da requisição {numero} registrada com sucesso.',
    )
    detalhe_url = reverse('requisicoes:detalhe', args=[requisicao.pk])
    return htmx_redirect(request, _voltar_url(request, default=detalhe_url))


# ---------------------------------------------------------------------------
# Detalhe da requisição
# ---------------------------------------------------------------------------


@login_required
@require_GET
def detalhe_requisicao_view(request, pk: int):
    """Renderiza cabeçalho, itens e timeline da requisição.

    Escopo de visibilidade unificado por ``requisicoes_visiveis_para``;
    objetos fora do escopo retornam 404 (ADR-0010) para não revelar
    existência.
    """
    requisicao = get_object_or_404(
        requisicoes_visiveis_para(request.user.pk),
        pk=pk,
    )
    return _render_detalhe(request, requisicao)


# ---------------------------------------------------------------------------
# Enviar rascunho para autorização — TR-005
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['POST'])
def enviar_rascunho_view(request, pk: int):
    """Envia rascunho para autorização e redireciona para o detalhe.

    A view não verifica estado nem ator: o service revalida sob lock
    (ADR-0005) e lança PermissaoNegada / EstadoInvalido / ConflitoDominio /
    DadosInvalidos.
    """
    try:
        requisicao = enviar_para_autorizacao(
            ator_id=request.user.pk,
            requisicao_id=pk,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except (EstadoInvalido, ConflitoDominio) as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except DadosInvalidos as exc:
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    messages.success(
        request,
        f'Requisição enviada para autorização. Número {requisicao.numero_publico}.',
    )
    detalhe_url = reverse('requisicoes:detalhe', args=[requisicao.pk])
    return htmx_redirect(request, _voltar_url(request, default=detalhe_url))


# ---------------------------------------------------------------------------
# Retornar para rascunho / recusar — TR-006 / TR-011
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(['POST'])
def retornar_rascunho_view(request, pk: int):
    """Retorna requisição aguardando autorização para rascunho."""
    try:
        requisicao = retornar_para_rascunho(
            ator_id=request.user.pk,
            requisicao_id=pk,
            observacao=request.POST.get('observacao', ''),
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except DadosInvalidos as exc:
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    messages.success(
        request,
        f'Requisição {requisicao.numero_publico} retornada para rascunho.',
    )
    return htmx_redirect(
        request,
        _voltar_url(
            request, default=reverse('requisicoes:detalhe', args=[requisicao.pk])
        ),
    )


@login_required
@require_http_methods(['POST'])
def cancelar_requisicao_view(request, pk: int):
    """Cancela ou descarta requisição antes da retirada final."""
    requisicao = get_object_or_404(
        requisicoes_visiveis_para(request.user.pk),
        pk=pk,
    )
    estado_origem = requisicao.estado
    numero_publico = requisicao.numero_publico
    justificativa = request.POST.get('justificativa', '')

    try:
        resultado_cancelamento = cancelar_requisicao(
            ator_id=request.user.pk,
            requisicao_id=pk,
            justificativa=justificativa,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except DadosInvalidos as exc:
        if exc.code == 'justificativa_cancelamento_obrigatoria':
            if request.htmx:
                copy = cancelamento_copy(cancelamento_info(requisicao), estado_origem)
                return render_modal_erro(
                    request,
                    modal_id='confirmar-cancelar',
                    titulo=copy['titulo'],
                    descricao=copy['descricao'],
                    registro=registro_requisicao(requisicao),
                    erro=str(exc),
                    form_body_template=(
                        'requisicoes/partials/_modal_form_cancelar.html'
                    ),
                    confirm_label=copy['confirmar'],
                    confirm_variant='danger',
                    icon_variant=copy['icon_variant'],
                    loading_label='Cancelando…',
                    # Este ramo é o da justificativa obrigatória, ou seja, o
                    # corpo trocado tem `<textarea>`.
                    corpo_com_campo_focavel=True,
                    contexto_form={
                        'justificativa_cancelamento': justificativa,
                        'cancelamento_requer_justificativa': True,
                    },
                )
            return _render_detalhe(
                request,
                requisicao,
                cancelacao_erro=str(exc),
                justificativa_cancelamento=justificativa,
                cancelamento_modal_aberto=True,
            )
        messages.error(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))
    except ConflitoDominio as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    numero = numero_publico or f'#{pk}'
    if resultado_cancelamento.pk is None:
        messages.success(request, f'Rascunho {numero} descartado com sucesso.')
        return htmx_redirect(
            request,
            _voltar_url(request, default=reverse('requisicoes:minhas')),
        )

    if estado_origem == EstadoRequisicao.RASCUNHO:
        messages.success(request, f'Rascunho {numero} cancelado com sucesso.')
    elif estado_origem == EstadoRequisicao.AGUARDANDO_AUTORIZACAO:
        messages.success(request, f'Requisição {numero} cancelada.')
    else:
        messages.success(
            request,
            f'Requisição {numero} cancelada. Reservas liberadas.',
        )

    return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))


@login_required
@require_http_methods(['POST'])
def recusar_requisicao_view(request, pk: int):
    """Recusa requisição aguardando autorização com motivo obrigatório."""
    motivo = request.POST.get('motivo', '')
    try:
        requisicao = recusar_requisicao(
            ator_id=request.user.pk,
            requisicao_id=pk,
            motivo=motivo,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except DadosInvalidos as exc:
        requisicao = get_object_or_404(
            requisicoes_visiveis_para(request.user.pk),
            pk=pk,
        )
        if request.htmx:
            copy = MODAL_COPY['recusar']
            return render_modal_erro(
                request,
                modal_id='confirmar-recusar',
                titulo=copy['titulo'],
                descricao=copy['descricao'],
                registro=registro_requisicao(requisicao),
                erro=str(exc),
                form_body_template='requisicoes/partials/_modal_form_recusar.html',
                confirm_label=copy['confirm_label'],
                confirm_variant='danger',
                icon_variant=copy['icon_variant'],
                loading_label='Recusando…',
                corpo_com_campo_focavel=True,
                contexto_form={'motivo_recusa': motivo},
            )
        return _render_detalhe(
            request,
            requisicao,
            recusa_erro=str(exc),
            motivo_recusa=motivo,
        )
    except EstadoInvalido as exc:
        messages.warning(request, str(exc))
        return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))

    messages.success(request, f'Requisição {requisicao.numero_publico} recusada.')
    return htmx_redirect(
        request,
        _voltar_url(
            request, default=reverse('requisicoes:detalhe', args=[requisicao.pk])
        ),
    )


@login_required
@require_http_methods(['GET', 'POST'])
def copiar_requisicao_view(request, pk: int):
    """Copia requisição atendida ou recusada para novo rascunho (REQ-09).

    GET mostra confirmação; POST executa a cópia e redireciona para editar.
    """
    requisicao = get_object_or_404(
        requisicoes_visiveis_para(request.user.pk),
        pk=pk,
    )

    if request.method == 'GET':
        # A confirmação não pode prometer o que o POST recusaria: sem estado
        # copiável ou sem permissão, o usuário volta ao detalhe com o motivo.
        if not _pode_copiar_agora(papel_efetivo(request.user), requisicao):
            messages.warning(
                request,
                'Só é possível copiar requisições atendidas ou recusadas '
                'para as quais você pode criar rascunho.',
            )
            return redirect('requisicoes:detalhe', pk=requisicao.pk)
        return render(
            request,
            'requisicoes/copiar_confirmacao.html',
            {
                'requisicao': requisicao,
                'itens': list(requisicao.itens.select_related('material').all()),
            },
        )

    try:
        novo = copiar_requisicao(
            ator_id=request.user.pk,
            requisicao_id=requisicao.pk,
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except ErroDominio as exc:
        pres = traduz_erro_dominio(exc)
        getattr(messages, pres.severity)(request, str(exc))
        return _render_detalhe(request, requisicao)

    messages.success(
        request,
        'Rascunho criado. Verifique os itens marcados antes de enviar para autorização.',
    )
    return redirect('requisicoes:editar_rascunho', pk=novo.pk)


@login_required
@require_http_methods(['POST'])
def registrar_devolucao_view(request, pk: int, item_pk: int) -> HttpResponse:
    """Registra devolução de item de requisição atendida (TR-020)."""
    requisicao = get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)
    form = RegistrarDevolucaoForm(request.POST)
    if not form.is_valid():
        if request.htmx:
            # O item só é buscado aqui, e não no topo da view: fora deste ramo
            # ele mudaria o código de resposta de um POST que hoje vai direto ao
            # service sem olhar o item.
            #
            # `.first()` e não `get_object_or_404`: um 404 aqui devolveria
            # página inteira a um `hx-post` que faz `outerHTML` em
            # `[data-modal-body]` — o defeito que esta issue existe para matar,
            # reintroduzido pelo próprio conserto. Pior, seria assimétrico: com
            # o form válido, o mesmo `item_pk` obsoleto vira `DadosInvalidos`
            # do service e a pessoa é informada; com o form inválido, ela veria
            # a página de erro dentro do diálogo. O item obsoleto cai no mesmo
            # 422, dizendo a mesma frase que o service diria.
            item = (
                requisicao.itens.select_related('material').filter(pk=item_pk).first()
            )
            copy = MODAL_COPY['devolucao']
            if item is None:
                return render_modal_erro(
                    request,
                    modal_id=f'devolver-{item_pk}',
                    titulo=copy['titulo'],
                    registro=registro_requisicao(requisicao),
                    erro='Item não pertence à requisição informada.',
                    confirm_label=copy['confirm_label'],
                    confirm_variant='return',
                    icon_variant=copy['icon_variant'],
                    acao_erro='registrar a devolução',
                    loading_label='Registrando…',
                )
            entregues = entregue_liquida_por_requisicao(requisicao_id=pk)
            return render_modal_erro(
                request,
                modal_id=f'devolver-{item_pk}',
                titulo=copy['titulo'],
                descricao=copy['descricao'],
                registro=registro_requisicao(requisicao),
                # O Form, e não um texto pré-formatado: `erros_do_formulario`
                # achata as mensagens dele com âncora por campo, sem o asterisco
                # de log que `form.errors.as_text()` produzia.
                erro=form,
                form_body_template=('requisicoes/partials/_modal_form_devolucao.html'),
                confirm_label=copy['confirm_label'],
                # `return` e não o default `primary` do helper: o render inicial
                # (detalhe.html) usa teal, e a Regra da Reversão Não é Erro não
                # pode cair justamente no caminho de erro.
                confirm_variant='return',
                icon_variant=copy['icon_variant'],
                acao_erro='registrar a devolução',
                loading_label='Registrando…',
                corpo_com_campo_focavel=True,
                contexto_form={
                    'form': form,
                    'item': item,
                    'entregue_liquida': entregues.get(item.material_id, Decimal('0')),
                },
            )
        messages.error(request, _texto_dos_erros(form))
        return redirect('requisicoes:detalhe', pk=pk)
    try:
        registrar_devolucao(
            ator_id=request.user.pk,
            requisicao_id=pk,
            item_id=item_pk,
            quantidade=form.cleaned_data['quantidade'],
            observacao=form.cleaned_data.get('observacao', ''),
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except ErroDominio as exc:
        pres = traduz_erro_dominio(exc)
        getattr(messages, pres.severity)(request, str(exc))
    else:
        messages.success(request, 'Devolução registrada com sucesso.')
    return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))


@login_required
@require_http_methods(['POST'])
def estornar_requisicao_view(request, pk: int) -> HttpResponse:
    """Estorna requisição atendida (TR-021)."""
    requisicao = get_object_or_404(requisicoes_visiveis_para(request.user.pk), pk=pk)
    form = EstornarRequisicaoForm(request.POST)
    if not form.is_valid():
        if request.htmx:
            # Espelha detalhe.html:327 (via _confirmacao_acao.html).
            copy = MODAL_COPY['estornar']
            # A lista de itens é parte do corpo (#138), e o 422 troca o corpo
            # inteiro: sem recalculá-la aqui, o modal reaberto com erro perderia
            # exatamente os números que o modal aberto mostrava. É o mesmo
            # cálculo de `_detalhe_context`.
            entregues = entregue_liquida_por_requisicao(requisicao_id=pk)
            itens_a_estornar = []
            for item in requisicao.itens.select_related('material').all():
                item.entregue_liquida = entregues.get(item.material_id, Decimal('0'))
                if item.entregue_liquida > 0:
                    itens_a_estornar.append(item)
            return render_modal_erro(
                request,
                modal_id='estornar-modal',
                titulo=copy['titulo'],
                descricao=copy['descricao'],
                consequencia=copy['consequencia'],
                registro=registro_requisicao(requisicao),
                erro=form,
                form_body_template='requisicoes/partials/_modal_form_estorno.html',
                confirm_label=copy['confirm_label'],
                # `return` e não `danger`: mesma razão pela qual a devolução
                # passa a sua própria variante aqui — o 422 devolve o mesmo
                # modal, e a cor da ação é parte dele.
                confirm_variant='return',
                icon_variant=copy['icon_variant'],
                acao_erro='estornar a requisição',
                loading_label='Estornando…',
                corpo_com_campo_focavel=True,
                contexto_form={
                    'estorno_form': form,
                    'itens_a_estornar': itens_a_estornar,
                },
            )
        messages.error(request, _texto_dos_erros(form))
        return redirect('requisicoes:detalhe', pk=pk)
    try:
        estornar_requisicao(
            ator_id=request.user.pk,
            requisicao_id=pk,
            justificativa=form.cleaned_data['justificativa'],
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))
    except ErroDominio as exc:
        pres = traduz_erro_dominio(exc)
        getattr(messages, pres.severity)(request, str(exc))
    else:
        messages.success(request, 'Requisição estornada com sucesso.')
    return htmx_redirect(request, reverse('requisicoes:detalhe', args=[pk]))


@login_required
@require_http_methods(['POST'])
def confirmar_importacao_scpi_view(request):
    import base64

    from django.urls import reverse as _reverse

    from apps.core.exceptions import ConflitoDominio, DadosInvalidos, PermissaoNegada
    from apps.estoque.models import Estoque
    from apps.estoque.policies import exigir_pode_confirmar_importacao_scpi
    from apps.estoque.services import confirmar_importacao_scpi
    from apps.requisicoes.services.ciclo_vida import (
        registrar_timeline_divergencia_importacao,
    )

    def _erro(mensagem: str):
        """Erro da confirmação: fragment 422 no modal, página completa sem HTMX.

        O 422 vai **sem** `form_body_template`. O corpo do modal é
        `_modal_corpo_confirmar_importacao.html`, a recapitulação de
        novos/divergências/total do preview — e no ramo mais comum de erro a
        sessão do preview já foi consumida. Repetir a contagem de uma
        pré-visualização que não existe mais seria a segunda evidência
        contraditória, justamente o que esta porta existe para evitar.
        """
        if request.htmx:
            # Espelha preview_importacao_scpi.html:313.
            from apps.estoque.presentation import MODAL_COPY as ESTOQUE_MODAL_COPY
            from apps.estoque.presentation import registro_arquivo_scpi

            copy = ESTOQUE_MODAL_COPY['confirmar_importacao_scpi']
            return render_modal_erro(
                request,
                modal_id='confirmar-importacao-scpi',
                titulo=copy['titulo'],
                descricao=copy['descricao'],
                consequencia=copy['consequencia'],
                registro=registro_arquivo_scpi(arquivo_nome),
                erro=mensagem,
                confirm_label=copy['confirm_label'],
                icon_variant=copy['icon_variant'],
                acao_erro='confirmar a importação',
            )
        return render(
            request,
            'estoque/confirmar_importacao_scpi.html',
            {'erro': mensagem},
        )

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_confirmar_importacao_scpi(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    conteudo_b64 = request.session.get('scpi_preview_bytes')
    arquivo_nome = request.session.get('scpi_preview_nome', 'importacao.csv')

    if not conteudo_b64:
        return _erro(
            'Nenhuma pré-visualização ativa. Faça o upload do arquivo novamente.'
        )

    estoque = Estoque.objects.filter(ativo=True).first()
    if estoque is None:
        return _erro('Não há estoque ativo configurado.')

    try:
        conteudo = base64.b64decode(conteudo_b64)
        importacao = confirmar_importacao_scpi(
            ator_id=request.user.id,
            conteudo_bytes=conteudo,
            arquivo_nome=arquivo_nome,
            estoque_id=estoque.pk,
            _pos_importacao_hook=registrar_timeline_divergencia_importacao,
        )
    except (ConflitoDominio, DadosInvalidos) as exc:
        return _erro(str(exc))

    request.session.pop('scpi_preview_bytes', None)
    request.session.pop('scpi_preview_nome', None)

    return htmx_redirect(
        request,
        _reverse('estoque:sucesso_importacao_scpi', kwargs={'pk': importacao.pk}),
    )


PAGINA_HISTORICO_REQUISICOES_TAMANHO = 25

# Ordem canônica da querystring do histórico (issue #152). Multi-valor: `estados`.
ORDEM_QUERYSTRING_HISTORICO_REQUISICOES = (
    'texto',
    'estados',
    'data_ini',
    'data_fim',
    'setor',
    'ordem',
    'page',
)


@login_required
@require_GET
def historico_requisicoes_view(request):
    """Histórico system-wide de requisições visível ao ator (RBAC no selector),
    filtrável e paginado. Espelha ``estoque.historico_movimentacoes_view``.

    Filtros vivem na querystring (recorte compartilhável). Em requisições HTMX
    devolve apenas o partial da tabela+paginação; caso contrário, a página
    completa. A view chama os selectors por ID (`request.user.pk`) e traduz a
    exceção de domínio em resposta HTTP, conforme ADR-0011/CONVENTIONS.md.
    """
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_historico_requisicoes(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    # A URL é a fonte de verdade do recorte (issue #152). Caminho nativo: 302
    # para a forma canônica; caminho HTMX: canônica no header HX-Push-Url, sem
    # roundtrip extra. `caminho_canonico` é idempotente — sem loop de 302.
    url_canonica = caminho_canonico(
        request,
        ordem_chaves=ORDEM_QUERYSTRING_HISTORICO_REQUISICOES,
        chaves_multivalor=('estados',),
    )
    if not request.htmx and request.get_full_path() != url_canonica:
        return redirect(url_canonica)

    texto = request.GET.get('texto', '').strip()
    estados_brutos = request.GET.getlist('estados')
    estados = [e for e in estados_brutos if e in EstadoRequisicao.values]
    data_ini = parse_data_iso(request.GET.get('data_ini'))
    data_fim = parse_data_iso(request.GET.get('data_fim'))

    mostrar_filtro_setor = pode_filtrar_historico_por_setor(request.user.pk)
    setor = None
    if mostrar_filtro_setor:
        setor_bruto = request.GET.get('setor', '')
        if setor_bruto.isdigit():
            setor = int(setor_bruto)

    eh_chefe_de_setor = (
        papel.setor_chefiado_ativo_id is not None and not papel.eh_chefe_de_almoxarifado
    )
    # SETOR só é redundante no cartão quando o recorte fixa o setor do item:
    # filtro de setor ativo, ou papel de chefe restrito ao setor chefiado. Uma
    # requisição que o chefe criou fora do setor chefiado continua exibindo o
    # campo — o selector inclui a cláusula de criador. Ver issue #158.
    if setor is not None:
        setor_fixo_id = setor
    elif eh_chefe_de_setor:
        setor_fixo_id = papel.setor_chefiado_ativo_id
    else:
        setor_fixo_id = None

    visiveis = historico_requisicoes_visiveis_para(request.user.pk)
    requisicoes = filtrar_historico_requisicoes(
        visiveis,
        texto=texto or None,
        estados=estados,
        data_ini=data_ini,
        data_fim=data_fim,
        setor=setor,
    )
    # O card/linha só exibe o nome do material quando a requisição tem um item
    # único; um `prefetch_related('itens__material')` carregaria as N linhas de
    # toda requisição para exibir, no máximo, uma.
    primeiro_material_sq = Subquery(
        ItemRequisicao.objects.filter(requisicao=OuterRef('pk'))
        .order_by('pk')
        .values('material__nome')[:1]
    )
    requisicoes = requisicoes.annotate(
        quantidade_itens=Count('itens'),
        primeiro_material_nome=primeiro_material_sq,
    )

    resultado = paginar_com_filtros(
        request, requisicoes, per_page=PAGINA_HISTORICO_REQUISICOES_TAMANHO
    )

    setores_disponiveis = []
    if mostrar_filtro_setor:
        setores_disponiveis = setores_do_historico(visiveis)

    qtd_filtros_ativos = contar_filtros_ativos(
        bool(texto),
        data_ini is not None,
        data_fim is not None,
        setor is not None,
        listas=(estados,),
    )
    tem_filtro_ativo = qtd_filtros_ativos > 0

    # Atalhos de recorte (issue #153) — chips por papel e presets de período
    # resolvem para a URL canônica (#152) via apps.core.filtros; ninguém
    # remonta querystring à mão. Teto de 3 chips por tela; papel sem direito ao
    # recorte não vê o chip.
    chips_filtro = []
    if eh_chefe_de_setor:
        chips_filtro.append(
            montar_chip(
                request,
                id='aguardando-autorizacao',
                rotulo='Aguardando minha autorização',
                glifo='⏳',
                chave='estados',
                valores=[EstadoRequisicao.AGUARDANDO_AUTORIZACAO.value],
                ordem_chaves=ORDEM_QUERYSTRING_HISTORICO_REQUISICOES,
                chaves_multivalor=('estados',),
            )
        )
    if papel.eh_almoxarifado or papel.eh_superusuario:
        chips_filtro.append(
            montar_chip(
                request,
                id='excecoes',
                rotulo='Exceções',
                glifo='⚠',
                chave='estados',
                valores=[
                    EstadoRequisicao.ESTORNADA.value,
                    EstadoRequisicao.RECUSADA.value,
                ],
                ordem_chaves=ORDEM_QUERYSTRING_HISTORICO_REQUISICOES,
                chaves_multivalor=('estados',),
            )
        )
    chips_filtro = chips_filtro[:3]
    presets_periodo = montar_presets_periodo(
        request,
        ordem_chaves=ORDEM_QUERYSTRING_HISTORICO_REQUISICOES,
        chaves_multivalor=('estados',),
    )

    contexto = {
        'page_obj': resultado.page_obj,
        'is_htmx': resultado.is_htmx,
        'mostrar_filtro_setor': mostrar_filtro_setor,
        'setor_fixo_id': setor_fixo_id,
        'setores_disponiveis': setores_disponiveis,
        'chips_filtro': chips_filtro,
        'presets_periodo': presets_periodo,
        'estados_opcoes': EstadoRequisicao.choices,
        'filtros': {
            'texto': texto,
            'estados': estados,
            'data_ini': request.GET.get('data_ini', ''),
            'data_fim': request.GET.get('data_fim', ''),
            'setor': setor,
        },
        'ordem': resultado.ordem,
        'url_ordenacao': resultado.url_ordenacao,
        'tem_filtro_ativo': tem_filtro_ativo,
        'qtd_filtros_ativos': qtd_filtros_ativos,
        'querystring_filtros': resultado.querystring_filtros,
    }

    if resultado.is_htmx:
        template = 'requisicoes/historico_requisicoes.html#resultados'
    else:
        template = 'requisicoes/historico_requisicoes.html'
    resposta = render(request, template, contexto)
    if request.htmx:
        # Empurra a canônica em vez de deixar o HTMX serializar o form.
        resposta['HX-Push-Url'] = url_canonica
    return resposta
