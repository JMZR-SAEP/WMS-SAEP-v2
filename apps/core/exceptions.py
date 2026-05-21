"""Exceções de domínio esperadas pelas camadas de aplicação."""


class ErroDominio(Exception):
    """Base para erros esperados de regra de negócio."""

    default_code = 'erro_dominio'

    def __init__(self, message=None, *, code=None):
        self.message = message or self.__class__.__name__
        self.code = code or self.default_code
        super().__init__(self.message)


class PermissaoNegada(ErroDominio):
    default_code = 'permissao_negada'


class EstadoInvalido(ErroDominio):
    default_code = 'estado_invalido'


class DadosInvalidos(ErroDominio):
    default_code = 'dados_invalidos'


class ConflitoDominio(ErroDominio):
    default_code = 'conflito_dominio'
