"""Exceções de domínio do WMS-SAEP.

Views traduzem para HTTP. Services lançam. Policies lançam PermissaoNegada.
Nunca usar exceções HTTP do Django dentro de services ou policies.
"""


class ErroDominio(Exception):
    """Base de todas as exceções de domínio.

    `detalhes` carrega o que a mensagem não consegue: identificadores que a tela
    precisa para **apontar** o erro em vez de só descrevê-lo. Um saldo
    insuficiente sabe qual material falhou; a faixa no topo da página só sabe
    escrever o nome dele. Sem esse par, o operador lê "MAT-006 pede 99.999" e
    volta a varrer uma lista de itens com o olho.

    É opcional e deliberadamente frouxo — dicionário simples, sem esquema, lido
    só por quem sabe o `code`. Não é canal de mensagem: o texto continua sendo
    `message`, e uma tela que ignore `detalhes` continua correta.
    """

    def __init__(
        self,
        message: str,
        code: str = 'erro_dominio',
        detalhes: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.detalhes: dict = detalhes or {}

    def __str__(self) -> str:
        return self.message


class PermissaoNegada(ErroDominio):
    """Ator não tem permissão para a operação solicitada."""

    def __init__(
        self,
        message: str = 'Você não tem permissão para esta operação.',
        code: str = 'permissao_negada',
    ):
        super().__init__(message, code)


class EstadoInvalido(ErroDominio):
    """Transição de estado inválida para o objeto de domínio."""

    def __init__(self, message: str, code: str = 'estado_invalido'):
        super().__init__(message, code)


class DadosInvalidos(ErroDominio):
    """Dados estruturalmente válidos mas semanticamente inválidos para o domínio."""

    def __init__(self, message: str, code: str = 'dados_invalidos'):
        super().__init__(message, code)


class ConflitoDominio(ErroDominio):
    """Conflito de estado, saldo, unicidade lógica ou corrida."""

    def __init__(
        self,
        message: str,
        code: str = 'conflito_dominio',
        detalhes: dict | None = None,
    ):
        super().__init__(message, code, detalhes)
