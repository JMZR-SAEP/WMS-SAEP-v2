from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.forms import BooleanField
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.papeis import papel_efetivo
from apps.core.exceptions import (
    ConflitoDominio,
    DadosInvalidos,
    ErroDominio,
    PermissaoNegada,
)
from apps.core.filtros import montar_chip, montar_presets_periodo
from apps.core.http import (
    htmx_redirect,
    parse_data_iso,
    querystring_sem_page,
    voltar_url_seguro,
)
from apps.core.listagem import contar_filtros_ativos, paginar, paginar_com_filtros
from apps.core.modal import render_modal_erro
from apps.core.presentation import traduz_erro_dominio
from apps.core.querystring import caminho_canonico
from apps.core.templatetags.core_tags import formatar_quantidade
from apps.estoque.forms import ItemSaidaExcepcionalFormSet, SaidaExcepcionalForm
from apps.estoque.presentation import (
    MODAL_COPY,
    registro_arquivo_scpi,
    registro_saida_excepcional,
)
from apps.estoque.models import Estoque, SaldoEstoque, TipoMovimentacaoEstoque
from apps.estoque.policies import (
    exigir_pode_consultar_movimentacoes_estoque,
    exigir_pode_consultar_saidas_excepcionais,
    exigir_pode_registrar_saida_excepcional,
    pode_registrar_saida_excepcional,
)
from apps.estoque.selectors import (
    buscar_materiais_saida_excepcional,
    filtrar_movimentacoes,
    listar_saidas_excepcionais,
    movimentacoes_visiveis_para,
    pode_filtrar_movimentacoes_por_setor,
)
from apps.estoque.services import registrar_saida_excepcional


PAGINA_SAIDAS_EXCEPCIONAIS_TAMANHO = 25


@login_required
@require_GET
def listar_saidas_excepcionais_view(request):
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_saidas_excepcionais(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    saidas = listar_saidas_excepcionais(request.user.pk)
    page_obj = paginar(request, saidas, per_page=PAGINA_SAIDAS_EXCEPCIONAIS_TAMANHO)
    return render(
        request,
        'estoque/lista_saidas_excepcionais.html',
        {
            'page_obj': page_obj,
            'saidas': page_obj.object_list,
            'pode_registrar': pode_registrar_saida_excepcional(papel),
        },
    )


PAGINA_MOVIMENTACOES_TAMANHO = 25

# Ordem canônica da querystring do ledger (issue #152). Multi-valor: `tipos`.
ORDEM_QUERYSTRING_MOVIMENTACOES = (
    'material',
    'tipos',
    'data_ini',
    'data_fim',
    'setor',
    'ordem',
    'page',
)

# Chip "só saídas": atalho que recorta o ledger nas saídas reais de material.
TIPOS_SO_SAIDAS = [
    TipoMovimentacaoEstoque.CONSUMO,
    TipoMovimentacaoEstoque.SAIDA_EXCEPCIONAL,
]


def _setores_beneficiarios_do_ledger(visiveis):
    """Setores beneficiários presentes no ledger visível (opções do filtro de
    setor, exibido apenas para almoxarifado)."""
    from apps.accounts.models import Setor

    ids = (
        visiveis.exclude(requisicao__isnull=True)
        .values_list('requisicao__setor_beneficiario_id', flat=True)
        .distinct()
    )
    return Setor.objects.filter(pk__in=ids).order_by('nome')


@login_required
@require_GET
def historico_movimentacoes_view(request):
    """Ledger de movimentações visível ao ator (RBAC no selector), filtrável.

    Filtros vivem na querystring (recorte compartilhável). Em requisições HTMX
    devolve apenas o partial da tabela+paginação; caso contrário, a página
    completa. A view chama os selectors por ID (`request.user.pk`) e traduz a
    exceção de domínio em resposta HTTP, conforme ADR-0011/CONVENTIONS.md.
    """
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_movimentacoes_estoque(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    # A URL é a fonte de verdade do recorte (issue #152). No caminho nativo
    # (submit do form, que sempre emite as chaves vazias) redireciona 302 para
    # a forma canônica; no caminho HTMX a canônica volta no header HX-Push-Url,
    # sem roundtrip extra. `caminho_canonico` é idempotente — sem loop de 302.
    url_canonica = caminho_canonico(
        request,
        ordem_chaves=ORDEM_QUERYSTRING_MOVIMENTACOES,
        chaves_multivalor=('tipos',),
    )
    if not request.htmx and request.get_full_path() != url_canonica:
        return redirect(url_canonica)

    material = request.GET.get('material', '').strip()
    tipos_brutos = request.GET.getlist('tipos')
    tipos = [t for t in tipos_brutos if t in TipoMovimentacaoEstoque.values]
    data_ini = parse_data_iso(request.GET.get('data_ini'))
    data_fim = parse_data_iso(request.GET.get('data_fim'))

    mostrar_filtro_setor = pode_filtrar_movimentacoes_por_setor(request.user.pk)
    setor = None
    if mostrar_filtro_setor:
        setor_bruto = request.GET.get('setor', '')
        if setor_bruto.isdigit():
            setor = int(setor_bruto)

    visiveis = movimentacoes_visiveis_para(request.user.pk)
    movimentacoes = filtrar_movimentacoes(
        visiveis,
        material=material or None,
        tipos=tipos,
        data_ini=data_ini,
        data_fim=data_fim,
        setor=setor,
    )

    resultado = paginar_com_filtros(
        request, movimentacoes, per_page=PAGINA_MOVIMENTACOES_TAMANHO
    )

    setores_disponiveis = []
    if mostrar_filtro_setor:
        setores_disponiveis = _setores_beneficiarios_do_ledger(visiveis)

    qtd_filtros_ativos = contar_filtros_ativos(
        bool(material),
        data_ini is not None,
        data_fim is not None,
        setor is not None,
        listas=(tipos,),
    )
    tem_filtro_ativo = qtd_filtros_ativos > 0

    # Atalhos de recorte (issue #153) — chips e presets resolvem para a URL
    # canônica (#152) via apps.core.filtros; ninguém remonta querystring à mão.
    # Teto de 3 chips por tela: aqui só "Só saídas".
    chips_filtro = [
        montar_chip(
            request,
            id='so-saidas',
            rotulo='Só saídas',
            glifo='↧',
            chave='tipos',
            valores=[t.value for t in TIPOS_SO_SAIDAS],
            ordem_chaves=ORDEM_QUERYSTRING_MOVIMENTACOES,
            chaves_multivalor=('tipos',),
        )
    ][:3]
    presets_periodo = montar_presets_periodo(
        request,
        ordem_chaves=ORDEM_QUERYSTRING_MOVIMENTACOES,
        chaves_multivalor=('tipos',),
    )

    contexto = {
        'page_obj': resultado.page_obj,
        'is_htmx': resultado.is_htmx,
        'mostrar_filtro_setor': mostrar_filtro_setor,
        'setores_disponiveis': setores_disponiveis,
        'tipos_opcoes': TipoMovimentacaoEstoque.choices,
        'filtros': {
            'material': material,
            'tipos': tipos,
            'data_ini': request.GET.get('data_ini', ''),
            'data_fim': request.GET.get('data_fim', ''),
            'setor': setor,
        },
        'ordem': resultado.ordem,
        'url_ordenacao': resultado.url_ordenacao,
        'chips_filtro': chips_filtro,
        'presets_periodo': presets_periodo,
        'tem_filtro_ativo': tem_filtro_ativo,
        'qtd_filtros_ativos': qtd_filtros_ativos,
        'querystring_filtros': resultado.querystring_filtros,
    }

    if resultado.is_htmx:
        template = 'estoque/historico_movimentacoes.html#resultados'
    else:
        template = 'estoque/historico_movimentacoes.html'
    resposta = render(request, template, contexto)
    if request.htmx:
        # Empurra a canônica em vez de deixar o HTMX serializar o form.
        resposta['HX-Push-Url'] = url_canonica
    return resposta


@login_required
@require_http_methods(['GET', 'POST'])
def nova_saida_excepcional_view(request):
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_registrar_saida_excepcional(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    estoque = Estoque.objects.filter(ativo=True).first()

    if estoque is None:
        return render(
            request,
            'estoque/nova_saida_excepcional.html',
            {
                'estoque': None,
                'form': SaidaExcepcionalForm(),
                'formset': ItemSaidaExcepcionalFormSet(prefix='itens', initial=[{}]),
                'erro_geral': 'Não há estoque ativo configurado.',
            },
            status=409,
        )

    if request.method == 'GET':
        return render(
            request,
            'estoque/nova_saida_excepcional.html',
            {
                'estoque': estoque,
                'form': SaidaExcepcionalForm(),
                'formset': ItemSaidaExcepcionalFormSet(
                    prefix='itens', initial=[{}], estoque_id=estoque.pk
                ),
            },
        )

    form = SaidaExcepcionalForm(request.POST)
    formset = ItemSaidaExcepcionalFormSet(
        request.POST, prefix='itens', estoque_id=estoque.pk
    )

    if form.is_valid() and formset.is_valid():
        # A baixa pode empurrar o físico abaixo do reservado e criar divergência
        # crítica (EST-07). Ela continua permitida — TR-013 é o caminho de
        # resolução —, mas as requisições autorizadas afetadas precisam ser
        # avisadas, e o operador precisa saber que criou o problema.
        from apps.requisicoes.services.ciclo_vida import (
            registrar_timeline_divergencia_saida_excepcional,
        )

        requisicoes_avisadas: list[int] = []

        def _avisar_divergencia(**kwargs):
            avisadas = registrar_timeline_divergencia_saida_excepcional(**kwargs)
            requisicoes_avisadas.extend(avisadas)
            return avisadas

        try:
            saida = registrar_saida_excepcional(
                ator_id=request.user.pk,
                estoque_id=estoque.pk,
                motivo=form.cleaned_data['motivo'],
                observacao=form.cleaned_data['observacao'],
                itens=formset.linhas_validas(),
                _pos_saida_hook=_avisar_divergencia,
            )
        except PermissaoNegada as exc:
            raise PermissionDenied(str(exc))
        except DadosInvalidos as exc:
            messages.error(request, str(exc))
        except ConflitoDominio as exc:
            messages.warning(request, str(exc))
        else:
            messages.success(
                request, f'Saída {saida.numero_publico} registrada com sucesso.'
            )
            if requisicoes_avisadas:
                total = len(requisicoes_avisadas)
                plural = (
                    'requisições autorizadas' if total > 1 else 'requisição autorizada'
                )
                foram = 'foram avisadas' if total > 1 else 'foi avisada'
                messages.warning(
                    request,
                    f'Esta baixa criou divergência crítica de estoque: '
                    f'{total} {plural} {foram}. A separação delas fica bloqueada '
                    f'até a divergência ser resolvida ou a requisição ser cancelada.',
                )
            return htmx_redirect(request, reverse('estoque:listar_saidas_excepcionais'))

    return render(
        request,
        'estoque/nova_saida_excepcional.html',
        {'estoque': estoque, 'form': form, 'formset': formset},
    )


@login_required
@require_GET
def nova_linha_item_saida_excepcional_view(request):
    """Retorna partial HTML com nova linha vazia do formset de saída excepcional."""
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_registrar_saida_excepcional(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    try:
        index = int(request.GET.get('index', 0))
    except (ValueError, TypeError):
        index = 0

    form = ItemSaidaExcepcionalFormSet.form(prefix=f'itens-{index}')
    form.fields[DELETION_FIELD_NAME] = BooleanField(label='Deletar', required=False)
    return render(
        request,
        'components/item_form_row.html',
        {
            'material_id_field': form['material_id'],
            'material_label_field': form['material_label'],
            'quantidade_field': form['quantidade'],
            'quantidade_label': 'Quantidade',
            'autocomplete_url_name': 'estoque:buscar_materiais_saida_excepcional',
            'autocomplete_item_template': 'estoque/partials/_autocomplete_item_material.html',
            'delete_field': form[DELETION_FIELD_NAME],
            'form_index': index,
        },
    )


@login_required
@require_GET
def buscar_materiais_saida_excepcional_view(request):
    papel = papel_efetivo(request.user)
    try:
        exigir_pode_registrar_saida_excepcional(papel)
    except PermissaoNegada:
        return JsonResponse({'error': 'Sem permissão.'}, status=403)

    q = request.GET.get('q', '').strip()
    materiais = list(buscar_materiais_saida_excepcional(q=q, limite=20))
    material_ids = [m.pk for m in materiais]

    saldo_por_material: dict = {}
    if material_ids:
        for row in (
            SaldoEstoque.objects.filter(material_id__in=material_ids)
            .values('material_id')
            .annotate(
                fisico=Sum(
                    ExpressionWrapper(F('saldo_fisico'), output_field=DecimalField())
                )
            )
        ):
            saldo_por_material[row['material_id']] = row['fisico']

    resultado = [
        {
            'id': m.pk,
            'codigo': m.codigo,
            'nome': m.nome,
            'unidade': m.unidade,
            'label': f'{m.codigo} — {m.nome}',
            'saldo_fisico': formatar_quantidade(
                saldo_por_material.get(m.pk, 0), m.unidade
            ),
        }
        for m in materiais
    ]
    return JsonResponse({'resultados': resultado})


@login_required
@require_http_methods(['GET'])
def detalhe_saida_excepcional_view(request, pk: int):
    from apps.estoque.policies import pode_estornar_saida_excepcional
    from apps.estoque.selectors import buscar_detalhe_saida_excepcional

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_saidas_excepcionais(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    saida = buscar_detalhe_saida_excepcional(saida_id=pk)
    if saida is None:
        from django.http import Http404

        raise Http404

    pode_estornar = pode_estornar_saida_excepcional(papel)

    return render(
        request,
        'estoque/detalhe_saida_excepcional.html',
        {
            'saida': saida,
            'pode_estornar': pode_estornar,
            'registro': registro_saida_excepcional(saida),
            # Preserva a página da listagem paginada de onde o operador veio
            # (`?next=` no link do cartão); fallback para a primeira página.
            'voltar_url': voltar_url_seguro(
                request, default=reverse('estoque:listar_saidas_excepcionais')
            ),
        },
    )


@login_required
@require_http_methods(['POST'])
def estornar_saida_excepcional_view(request, pk: int):
    from apps.estoque.policies import exigir_pode_estornar_saida_excepcional
    from apps.estoque.selectors import buscar_detalhe_saida_excepcional
    from apps.estoque.services import estornar_saida_excepcional

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_saidas_excepcionais(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    try:
        exigir_pode_estornar_saida_excepcional(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    saida = buscar_detalhe_saida_excepcional(saida_id=pk)
    if saida is None:
        from django.http import Http404

        raise Http404

    justificativa = request.POST.get('justificativa', '').strip()

    try:
        estornar_saida_excepcional(
            ator_id=request.user.pk,
            saida_id=pk,
            justificativa=justificativa,
        )
    except PermissaoNegada as exc:
        # Antes do `except ErroDominio`, como nas views irmãs: `PermissaoNegada`
        # é subclasse de `ErroDominio`, e sem esta linha ela sairia como 422 com
        # o botão "Confirmar estorno" — convidando a repetir uma ação que a
        # pessoa não pode executar. O service revalida a policy, então este
        # caminho é alcançável mesmo com a checagem do topo desta view.
        raise PermissionDenied(str(exc))
    except ErroDominio as exc:
        if request.htmx:
            # Título, descrição e rótulos vêm de MODAL_COPY (#135): o modal que
            # reabre com erro tem de ser o mesmo modal, não um parente.
            copy = MODAL_COPY['estornar_saida']
            return render_modal_erro(
                request,
                modal_id='estornar-saida',
                titulo=copy['titulo'],
                descricao=copy['descricao'],
                consequencia=copy['consequencia'],
                registro=registro_saida_excepcional(saida),
                erro=str(exc),
                form_body_template=('estoque/partials/_modal_form_estorno_saida.html'),
                confirm_label=copy['confirm_label'],
                confirm_variant='danger',
                icon_variant=copy['icon_variant'],
                acao_erro='estornar a saída',
                contexto_form={'justificativa': justificativa},
            )
        pres = traduz_erro_dominio(exc)
        getattr(messages, pres.severity)(request, str(exc))
        return redirect('estoque:detalhe_saida_excepcional', pk=pk)

    messages.success(request, f'Saída {saida.numero_publico} estornada com sucesso.')
    return htmx_redirect(
        request, reverse('estoque:detalhe_saida_excepcional', args=[pk])
    )


@login_required
@require_http_methods(['GET', 'POST'])
def preview_importacao_scpi_view(request):
    from apps.core.exceptions import DadosInvalidos, PermissaoNegada
    from apps.estoque.policies import exigir_pode_visualizar_preview_scpi
    from apps.estoque.selectors import gerar_preview_importacao_scpi

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_visualizar_preview_scpi(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    if request.method == 'GET':
        request.session.pop('scpi_preview_bytes', None)
        request.session.pop('scpi_preview_nome', None)
        return render(request, 'estoque/preview_importacao_scpi.html', {})

    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return render(
            request,
            'estoque/preview_importacao_scpi.html',
            {'erro_arquivo': 'O arquivo é obrigatório.'},
        )

    estoque = Estoque.objects.filter(ativo=True).first()
    if estoque is None:
        return render(
            request,
            'estoque/preview_importacao_scpi.html',
            {'erro_arquivo': 'Não há estoque ativo configurado.'},
        )

    try:
        conteudo = arquivo.read()
        linhas = gerar_preview_importacao_scpi(
            conteudo_bytes=conteudo,
            estoque_id=estoque.pk,
        )
    except DadosInvalidos as exc:
        return render(
            request,
            'estoque/preview_importacao_scpi.html',
            {'erro_arquivo': str(exc)},
        )

    # Arquivo lido com sucesso e sem nenhuma linha de dados. Sem este ramo o
    # POST cai de volta no formulário de upload — idêntico ao que a pessoa já
    # estava vendo, sem alerta e sem foco —, e uma tela que não reage é
    # indistinguível de uma tela travada. O caminho de erro do arquivo já tem o
    # mecanismo certo montado: alerta amarrado ao campo de retry por
    # aria-describedby, com autofocus. Depois de um POST full-page é o foco que
    # anuncia, não live region.
    if not linhas:
        return render(
            request,
            'estoque/preview_importacao_scpi.html',
            {
                'erro_arquivo': (
                    'O arquivo não contém linhas de dados após o cabeçalho. '
                    'Verifique se há registros abaixo do cabeçalho e envie novamente.'
                )
            },
        )

    import base64

    request.session['scpi_preview_bytes'] = base64.b64encode(conteudo).decode('ascii')
    request.session['scpi_preview_nome'] = arquivo.name

    total = len(linhas)
    divergencias = sum(1 for linha in linhas if linha.status == 'divergente')
    novos = sum(1 for linha in linhas if linha.status == 'novo')

    # A tela existe para evidenciar delta: divergência e material novo primeiro,
    # linha "OK" por último. Na ordem do arquivo, conferir 12 divergências num
    # CSV de 800 linhas é caçar. Ordenação estável, então dentro de cada grupo a
    # ordem do arquivo é preservada — o operador confere contra o papel na mesma
    # sequência em que ele foi impresso.
    prioridade_status = {'divergente': 0, 'novo': 1, 'ok': 2}
    linhas = sorted(linhas, key=lambda linha: prioridade_status.get(linha.status, 3))

    return render(
        request,
        'estoque/preview_importacao_scpi.html',
        {
            'linhas': linhas,
            'total': total,
            'divergencias': divergencias,
            'novos': novos,
            'nome_arquivo': arquivo.name,
            'registro': registro_arquivo_scpi(arquivo.name),
            'pode_confirmar': True,
        },
    )


@login_required
@require_http_methods(['GET'])
def sucesso_importacao_scpi_view(request, pk: int):
    from apps.core.exceptions import PermissaoNegada
    from apps.estoque.models import ImportacaoSCPI
    from apps.estoque.policies import exigir_pode_confirmar_importacao_scpi

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_confirmar_importacao_scpi(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    try:
        importacao = ImportacaoSCPI.objects.get(pk=pk)
    except ImportacaoSCPI.DoesNotExist:
        from django.http import Http404

        raise Http404

    return render(
        request,
        'estoque/confirmar_importacao_scpi.html',
        {
            'importacao': importacao,
            'sucesso': True,
        },
    )


PAGINA_IMPORTACOES_SCPI_TAMANHO = 25


@login_required
@require_http_methods(['GET'])
def historico_importacoes_scpi_view(request):
    from apps.core.exceptions import PermissaoNegada
    from apps.estoque.policies import exigir_pode_consultar_historico_scpi
    from apps.estoque.selectors import listar_historico_importacoes_scpi

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_historico_scpi(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    importacoes = listar_historico_importacoes_scpi()
    page_obj = paginar(request, importacoes, per_page=PAGINA_IMPORTACOES_SCPI_TAMANHO)
    return render(
        request,
        'estoque/historico_importacoes_scpi.html',
        {'page_obj': page_obj, 'importacoes': page_obj.object_list},
    )


@login_required
@require_http_methods(['GET'])
def baixar_arquivo_importacao_scpi_view(request, pk: int):
    """Serve o CSV arquivado de uma importação SCPI, atrás da policy do histórico."""
    from pathlib import PurePosixPath

    from django.http import FileResponse, Http404

    from apps.core.exceptions import PermissaoNegada
    from apps.estoque.policies import exigir_pode_consultar_historico_scpi
    from apps.estoque.selectors import buscar_importacao_scpi

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_historico_scpi(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    importacao = buscar_importacao_scpi(importacao_id=pk)
    if importacao is None or not importacao.arquivo:
        raise Http404

    # `FileResponse` lê de forma tardia. Sem abrir aqui, um arquivo que sumiu do
    # storage estouraria no meio do streaming — 500 com o header já enviado.
    try:
        arquivo = importacao.arquivo.open('rb')
    except FileNotFoundError:
        raise Http404

    # Basename do nome original: `arquivo_nome` veio do upload e pode trazer
    # componentes de caminho, que não entram no `Content-Disposition`.
    nome = PurePosixPath(importacao.arquivo_nome.replace('\\', '/')).name
    return FileResponse(arquivo, as_attachment=True, filename=nome or 'importacao.csv')


PAGINA_MATERIAIS_TAMANHO = 25


@login_required
@require_GET
def lista_materiais_view(request):
    from apps.core.exceptions import PermissaoNegada
    from apps.estoque.policies import exigir_pode_consultar_catalogo_estoque
    from apps.estoque.selectors import listar_materiais_com_saldo

    papel = papel_efetivo(request.user)
    try:
        exigir_pode_consultar_catalogo_estoque(papel)
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc))

    busca = request.GET.get('busca', '').strip()
    saldos = listar_materiais_com_saldo(busca=busca)
    page_obj = paginar(request, saldos, per_page=PAGINA_MATERIAIS_TAMANHO)
    return render(
        request,
        'estoque/lista_materiais.html',
        {
            'page_obj': page_obj,
            'saldos': page_obj.object_list,
            'busca': busca,
            'querystring_filtros': querystring_sem_page(request.GET),
        },
    )
