"""Formulários do app accounts."""

from django.contrib.auth.forms import AuthenticationForm


class MatriculaAuthenticationForm(AuthenticationForm):
    """Autenticação por matrícula e senha.

    Reaproveita o ``AuthenticationForm`` do Django; o `User` já usa
    ``USERNAME_FIELD = "matricula"``, então não há backend customizado.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Matrícula'
        self.fields['username'].widget.attrs.update(
            {
                'autocomplete': 'username',
                'autofocus': True,
                'class': 'campo',
            }
        )
        self.fields['password'].widget.attrs.update(
            {
                'autocomplete': 'current-password',
                'class': 'campo',
            }
        )
        # Credencial recusada não acusa qual das duas está errada — por decisão
        # de segurança —, então nenhum dos dois campos tem `errors` e nenhum
        # seria marcado pelo components/form_field.html, que só olha o campo. A
        # marcação de suspeita é do Form: é ele que sabe que a falha é do par.
        # A fiação de `aria-describedby` que vivia aqui saiu: os ids de erro
        # inline são emitidos pelo próprio componente, e mantê-los também aqui
        # era a mesma decisão em dois lugares, com o Form perdendo em silêncio.
        if self.is_bound and self.non_field_errors():
            self.fields['username'].widget.attrs['aria-invalid'] = 'true'
            self.fields['password'].widget.attrs['aria-invalid'] = 'true'
