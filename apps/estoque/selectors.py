import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Exists, OuterRef, Q, QuerySet

from apps.accounts.models import User
from apps.accounts.papeis import papel_efetivo
from apps.requisicoes.models import EstadoRequisicao
from apps.estoque.models import (
    Material,
    MovimentacaoEstoque,
    SaidaExcepcional,
    TipoMovimentacaoEstoque,
)


def listar_saidas_excepcionais(ator_id: int) -> QuerySet:
    return (
        SaidaExcepcional.objects.select_related('registrado_por', 'estoque')
        .annotate(quantidade_itens=Count('itens'))
        # `-id` desempata registros do mesmo instante: sem ele, a fronteira de
        # página da listagem paginada não é determinística entre requisições.
        .order_by('-criado_em', '-id')
    )


def buscar_materiais_saida_excepcional(q: str = '', limite: int = 20):
    """Retorna materiais elegíveis para saída excepcional (JSON autocomplete).

    Elegível = ativo, com saldo_fisico > 0 em qualquer estoque.
    """
    from django.db.models import Q

    from apps.estoque.models import Material

    qs = Material.objects.filter(ativo=True, saldos__saldo_fisico__gt=0).distinct()
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(nome__icontains=q))
    return qs.order_by('nome')[:limite]


def unidades_por_materiais(material_ids: list) -> dict[str, str]:
    """Retorna dict {material_id como string: unidade} para os ids informados.

    Existe para o formulário de saída excepcional re-renderizado por erro: as
    linhas voltam com o material vinculado, mas nenhum evento de seleção
    dispara, e a recapitulação do modal — que lê `data-unidade` da linha —
    mostraria a quantidade sem dizer de quê. Chave em string porque é assim que
    o filtro `get_item` dos templates procura.

    Os ids chegam CRUS do POST — é `f['material_id'].value()`, não
    `cleaned_data`, porque o formulário aqui é justamente o que não validou.
    `pk__in` prepara cada item para o PK inteiro e um `material_id=abc` forjado
    levantaria `ValueError` no meio do render, trocando a página de erros do
    formset por um 500. O que não é inteiro é descartado: nenhum material casa
    com ele de qualquer forma, e a linha correspondente fica sem unidade — a
    mesma degradação de quando o material ainda não foi escolhido.
    """
    ids = []
    for bruto in material_ids:
        try:
            ids.append(int(bruto))
        except (TypeError, ValueError):
            continue
    if not ids:
        return {}
    return {
        str(pk): unidade
        for pk, unidade in Material.objects.filter(pk__in=ids).values_list(
            'pk', 'unidade'
        )
    }


def buscar_detalhe_saida_excepcional(saida_id: int) -> SaidaExcepcional | None:
    """Retorna SaidaExcepcional com itens e relações prefetchadas, ou None."""
    try:
        return (
            SaidaExcepcional.objects.select_related(
                'registrado_por', 'estoque', 'estornado_por'
            )
            .prefetch_related('itens__material')
            .get(pk=saida_id)
        )
    except SaidaExcepcional.DoesNotExist:
        return None


@dataclass
class LinhaPreviewSCPI:
    cadpro: str
    nome_material: str | None
    denominacao_scpi: str
    material_id: int | None
    saldo_wms: Decimal
    saldo_scpi: Decimal
    delta: Decimal
    status: str  # 'ok' | 'divergente' | 'novo'
    unidade: str


def _normalizar_csv_scpi(conteudo_bytes: bytes) -> str:
    import re

    from apps.core.exceptions import DadosInvalidos

    try:
        texto = conteudo_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise DadosInvalidos(
            'Arquivo deve estar em UTF-8 (BOM opcional).',
            code='csv_codificacao_invalida',
        )

    cadpro_re = re.compile(r'^\d{3}\.\d{3}\.\d{3};')
    linhas_raw = texto.splitlines()

    registros: list[str] = []
    buffer: list[str] = []

    for linha in linhas_raw:
        linha = linha.rstrip('\r')
        if cadpro_re.match(linha) or (
            not registros and not buffer and linha.startswith('CADPRO')
        ):
            if buffer:
                registros.append(' '.join(buffer))
                buffer = []
            buffer.append(linha)
        else:
            if buffer:
                buffer.append(linha.strip())
            else:
                registros.append(linha)

    if buffer:
        registros.append(' '.join(buffer))

    return '\n'.join(registros)


def _parse_linhas_csv_scpi(conteudo: str) -> list[dict]:
    from apps.core.exceptions import DadosInvalidos

    reader = csv.DictReader(io.StringIO(conteudo), delimiter=';')
    if reader.fieldnames is None or 'CADPRO' not in reader.fieldnames:
        raise DadosInvalidos(
            'CSV inválido: coluna CADPRO não encontrada.',
            code='csv_coluna_ausente',
        )
    colunas_quantidade = [
        f for f in reader.fieldnames if 'QUAN3' in f.upper() or f.upper() == 'QT'
    ]
    if not colunas_quantidade:
        raise DadosInvalidos(
            'CSV inválido: coluna de quantidade não encontrada.',
            code='csv_coluna_ausente',
        )
    col_qtd = colunas_quantidade[0]
    _COLUNAS_NOME = ('DISC1', 'DENOMINACAO')
    col_den = next(
        (f for f in reader.fieldnames if f.upper() in _COLUNAS_NOME),
        None,
    )
    linhas = []
    for i, row in enumerate(reader, start=2):
        cadpro = (row.get('CADPRO') or '').strip()
        qtd_raw = (row.get(col_qtd) or '').strip().replace(',', '.')
        if not cadpro:
            continue
        try:
            quantidade = Decimal(qtd_raw)
        except (InvalidOperation, ValueError):
            raise DadosInvalidos(
                f'Quantidade inválida no produto {cadpro} (linha {i}): "{qtd_raw}".',
                code='csv_quantidade_invalida',
            )
        denominacao = (row.get(col_den) or '').strip() if col_den else ''
        linhas.append(
            {'cadpro': cadpro, 'quantidade': quantidade, 'denominacao': denominacao}
        )
    return linhas


def gerar_preview_importacao_scpi(
    *, conteudo_bytes: bytes, estoque_id: int
) -> list[LinhaPreviewSCPI]:
    """Gera pré-visualização read-only da importação SCPI.

    Compara CADPRO → Material.codigo contra saldo_fisico do estoque indicado.
    Não persiste nenhuma alteração.
    """
    from apps.estoque.models import (
        UNIDADE_PADRAO_MATERIAL_SCPI,
        Material,
        SaldoEstoque,
    )

    conteudo = _normalizar_csv_scpi(conteudo_bytes)
    linhas_raw = _parse_linhas_csv_scpi(conteudo)

    if not linhas_raw:
        return []

    cadpros = [row['cadpro'] for row in linhas_raw]
    materiais = {
        m.codigo: m
        for m in Material.objects.filter(codigo__in=cadpros).only(
            'id', 'codigo', 'nome', 'unidade'
        )
    }
    material_ids = [m.id for m in materiais.values()]
    saldos = {
        s.material_id: s
        for s in SaldoEstoque.objects.filter(
            material_id__in=material_ids, estoque_id=estoque_id
        ).only('material_id', 'saldo_fisico')
    }

    resultado: list[LinhaPreviewSCPI] = []
    for linha in linhas_raw:
        cadpro = linha['cadpro']
        saldo_scpi = linha['quantidade']
        denominacao = linha['denominacao']
        material = materiais.get(cadpro)

        if material is None:
            resultado.append(
                LinhaPreviewSCPI(
                    cadpro=cadpro,
                    nome_material=None,
                    denominacao_scpi=denominacao,
                    material_id=None,
                    saldo_wms=Decimal('0'),
                    saldo_scpi=saldo_scpi,
                    delta=saldo_scpi,
                    status='novo',
                    # Mesma constante que `confirmar_importacao_scpi` grava
                    # neste material: o preview não pode prometer uma precisão
                    # diferente da que a criação aplica.
                    unidade=UNIDADE_PADRAO_MATERIAL_SCPI,
                )
            )
            continue

        saldo_obj = saldos.get(material.id)
        saldo_wms = saldo_obj.saldo_fisico if saldo_obj else Decimal('0')
        delta = saldo_scpi - saldo_wms
        status = 'ok' if delta == 0 else 'divergente'

        resultado.append(
            LinhaPreviewSCPI(
                cadpro=cadpro,
                nome_material=material.nome,
                denominacao_scpi=denominacao,
                material_id=material.id,
                saldo_wms=saldo_wms,
                saldo_scpi=saldo_scpi,
                delta=delta,
                status=status,
                unidade=material.unidade,
            )
        )

    return resultado


def listar_historico_importacoes_scpi():
    from apps.estoque.models import ImportacaoSCPI

    return ImportacaoSCPI.objects.select_related('importado_por', 'estoque').order_by(
        '-importado_em', '-id'
    )


def buscar_importacao_scpi(*, importacao_id: int):
    """Retorna a ImportacaoSCPI pelo pk, ou None."""
    from apps.estoque.models import ImportacaoSCPI

    try:
        return ImportacaoSCPI.objects.select_related('importado_por', 'estoque').get(
            pk=importacao_id
        )
    except ImportacaoSCPI.DoesNotExist:
        return None


def listar_divergencias_importacao_scpi(*, importacao_id: int):
    """Linhas divergentes gravadas na confirmação, na ordem do CADPRO (#161).

    Ordem por CADPRO e não pela ordem do arquivo: a lista existe para ser
    percorrida contra o SCPI, onde o produto é procurado pelo código.
    """
    from apps.estoque.models import LinhaDivergenteSCPI

    return LinhaDivergenteSCPI.objects.filter(importacao_id=importacao_id).order_by(
        'cadpro', 'id'
    )


def listar_materiais_com_saldo(*, busca: str = ''):
    from django.db.models import (
        BooleanField,
        Case,
        DecimalField,
        ExpressionWrapper,
        F,
        Q,
        When,
    )

    from apps.estoque.models import SaldoEstoque

    qs = (
        SaldoEstoque.objects.select_related('material', 'estoque')
        .annotate(
            saldo_disponivel_calculado=ExpressionWrapper(
                F('saldo_fisico') - F('saldo_reservado'),
                output_field=DecimalField(max_digits=12, decimal_places=3),
            ),
            divergente_calculado=Case(
                When(saldo_fisico__lt=F('saldo_reservado'), then=True),
                default=False,
                output_field=BooleanField(),
            ),
        )
        # Pelo código, não pelo nome: o cartão imprime o código como `<h2>` em
        # semibold e o nome como linha secundária em cinza, então ordenar por
        # nome deixava a coluna que o olho percorre — a única em destaque —
        # aparentemente embaralhada (MAT-010, MAT-004, MAT-002, MAT-012…). A
        # chave de ordenação tem de ser a que a hierarquia visual promete.
        # `codigo` é único (`Material.codigo`), então não precisa de desempate,
        # mas o `pk` fica: a fronteira de 25 registros da paginação depende de
        # ordem total e o custo é zero.
        .order_by('material__codigo', 'pk')
    )

    if busca:
        qs = qs.filter(
            Q(material__codigo__icontains=busca) | Q(material__nome__icontains=busca)
        )

    return qs


TIPOS_MOVIMENTO_ENTREGA_LIQUIDA = [
    TipoMovimentacaoEstoque.CONSUMO,
    TipoMovimentacaoEstoque.DEVOLUCAO,
    TipoMovimentacaoEstoque.ESTORNO_REQUISICAO,
]


def entregue_liquida_por_material(*, requisicao_id: int, material_id: int) -> Decimal:
    """Calcula a quantidade entregue líquida de um material de requisição via ledger.

    Entregue líquida = −Σ delta_fisico para movimentações do tipo consumo,
    devolucao ou estorno_requisicao vinculadas à requisição e ao material.

    Leitura pura: não faz select_for_update. Quem muta deve travar a requisição
    antes de chamar (ADR-0005) — o lock da Requisição garante que nenhuma nova
    movimentação será inserida para esse (requisicao_id, material_id) durante a
    operação.
    """
    from django.db.models import Sum

    from apps.estoque.models import MovimentacaoEstoque

    resultado = MovimentacaoEstoque.objects.filter(
        requisicao_id=requisicao_id,
        material_id=material_id,
        tipo__in=TIPOS_MOVIMENTO_ENTREGA_LIQUIDA,
    ).aggregate(total=Sum('delta_fisico'))

    total_delta_fisico = resultado['total'] or Decimal('0')
    return -total_delta_fisico


def entregue_liquida_por_requisicao(*, requisicao_id: int) -> dict[int, Decimal]:
    """Entregue líquida de todos os materiais de uma requisição, em uma query.

    Mesma definição de `entregue_liquida_por_material`, agrupada por material:
    a tela de detalhe precisa do valor de cada item para decidir se oferece
    devolução, e chamar a versão unitária dentro do laço fazia uma query por
    item. Materiais sem movimentação não aparecem no dict — quem lê usa 0.
    """
    from django.db.models import Sum

    from apps.estoque.models import MovimentacaoEstoque

    linhas = (
        MovimentacaoEstoque.objects.filter(
            requisicao_id=requisicao_id,
            tipo__in=TIPOS_MOVIMENTO_ENTREGA_LIQUIDA,
        )
        .values('material_id')
        .annotate(total=Sum('delta_fisico'))
    )
    return {linha['material_id']: -(linha['total'] or Decimal('0')) for linha in linhas}


def _eh_almoxarifado(ator: User) -> bool:
    """True se o ator é chefe ou auxiliar ativo de um setor ALMOXARIFADO ativo."""
    return papel_efetivo(ator).eh_almoxarifado


def _setores_visiveis_nao_almox(ator: User) -> list[int]:
    """IDs de setores não-almox ativos onde o ator é chefe OU auxiliar ativo."""
    return list(papel_efetivo(ator).setores_em_escopo)


def movimentacoes_visiveis_para(ator_id: int) -> QuerySet[MovimentacaoEstoque]:
    """Queryset do ledger visível ao ator, ordenado por -criado_em.

    RBAC (fronteira de segurança — nunca na view/template):
    - superuser → tudo.
    - almoxarifado (chefe ou auxiliar) → tudo, incluindo saídas excepcionais.
    - chefe de setor não-almox → movimentações de requisições com
      ``setor_beneficiario`` igual ao setor que ele chefia, mais as de
      requisições que ele criou; rascunho fica de fora nos dois casos.
    - auxiliar de setor não-almox → apenas movimentações de requisições que ele
      criou, fora de rascunho: ser auxiliar não é supervisionar o setor
      (``docs/matriz-permissoes.md`` §5; decisão da #106 estendida ao ledger
      pela #112). O ledger nunca lista metadado de requisição cujo detalhe
      devolve 404 a quem está olhando.
    - usuário inativo/inexistente → vazio.

    Saída excepcional (``requisicao`` nulo) fica fora do ramo de setor por
    construção: nenhum dos termos do predicado casa com requisição nula.

    ``requisicao_no_escopo`` acompanha cada linha porque LISTAR o metadado e
    poder ABRIR o documento não são a mesma permissão para o almoxarifado: ele
    vê o ledger inteiro, inclusive movimentações de rascunho de terceiro, e
    ``requisicoes_visiveis_para`` — o escopo que ``detalhe_requisicao_view``
    usa — exclui esses rascunhos. Sem a marca, o template linkava o número e o
    clique caía em 404. Quem decide continua sendo o selector de requisições,
    não o template.
    """
    from apps.requisicoes.selectors import requisicoes_visiveis_para

    base_qs = (
        MovimentacaoEstoque.objects.select_related(
            'material',
            'estoque',
            'ator',
            'requisicao',
            'requisicao__setor_beneficiario',
            'saida_excepcional',
        )
        .annotate(
            requisicao_no_escopo=Exists(
                requisicoes_visiveis_para(ator_id).filter(pk=OuterRef('requisicao_id'))
            )
        )
        .order_by('-criado_em')
    )

    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        return base_qs.none()

    if not ator.is_active:
        return base_qs.none()

    if ator.is_superuser:
        return base_qs

    papel = papel_efetivo(ator)
    if papel.eh_almoxarifado:
        return base_qs

    if not papel.setores_em_escopo:
        return base_qs.none()

    filtro = Q(requisicao__criador_id=ator.pk)
    if papel.setor_chefiado_ativo_id is not None:
        filtro |= Q(requisicao__setor_beneficiario_id=papel.setor_chefiado_ativo_id)

    # Rascunho é excluído explicitamente: ``requisicao`` é anulável e o model não
    # tem constraint de estado, então o não-vazamento não pode depender de os
    # services nunca produzirem esse par.
    nao_rascunho = ~Q(requisicao__estado=EstadoRequisicao.RASCUNHO)

    return base_qs.filter(filtro & nao_rascunho)


def filtrar_movimentacoes(
    qs: QuerySet[MovimentacaoEstoque],
    *,
    material: str | None,
    tipos: list[str],
    data_ini: date | None,
    data_fim: date | None,
    setor: int | None,
) -> QuerySet[MovimentacaoEstoque]:
    """Estreita o queryset de movimentações já escopado por RBAC.

    Aplica filtros **sobre** o ``qs`` recebido (resultado de
    ``movimentacoes_visiveis_para``), de forma que o filtro nunca amplia o
    universo visível — é sempre um ``AND`` adicional. Em particular, ``setor``
    aplicado sobre um qs já escopado a um setor não vaza dado de outro setor.

    - ``material``: busca por ``codigo`` OU ``nome`` (icontains); vazio → no-op.
    - ``tipos``: lista de ``TipoMovimentacaoEstoque``; valores fora do enum são
      descartados; lista vazia → no-op.
    - ``data_ini`` / ``data_fim``: período **inclusivo** sobre o dia de
      ``criado_em``; ``None`` → no-op.
    - ``setor``: ``requisicao__setor_beneficiario_id``; ``None`` → no-op.
    """
    if material:
        qs = qs.filter(
            Q(material__codigo__icontains=material)
            | Q(material__nome__icontains=material)
        )

    tipos_validos = [t for t in tipos if t in TipoMovimentacaoEstoque.values]
    if tipos_validos:
        qs = qs.filter(tipo__in=tipos_validos)

    if data_ini is not None:
        qs = qs.filter(criado_em__date__gte=data_ini)
    if data_fim is not None:
        qs = qs.filter(criado_em__date__lte=data_fim)

    if setor is not None:
        qs = qs.filter(requisicao__setor_beneficiario_id=setor)

    return qs


def pode_filtrar_movimentacoes_por_setor(ator_id: int) -> bool:
    """True se o ator pode filtrar o ledger por setor (somente almoxarifado).

    Chefe/auxiliar de setor já está escopado ao próprio setor pelo RBAC, então
    o filtro de setor não se aplica a ele. Superuser e almoxarifado veem todos
    os setores e podem recortar por setor beneficiário.
    """
    try:
        ator = User.objects.get(pk=ator_id)
    except User.DoesNotExist:
        return False
    if not ator.is_active:
        return False
    return ator.is_superuser or _eh_almoxarifado(ator)
