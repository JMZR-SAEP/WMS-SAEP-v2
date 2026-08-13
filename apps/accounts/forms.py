"""Formulários do app accounts."""

from django.contrib.auth.forms import AuthenticationForm


def _adicionar_aria_describedby(field, id_erro):
    ids_atuais = field.widget.attrs.get('aria-describedby', '').split()
    if id_erro not in ids_atuais:
        ids_atuais.append(id_erro)
    field.widget.attrs['aria-describedby'] = ' '.join(ids_atuais)


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
                'class': (
                    'mt-2 block min-h-11 w-full rounded-lg border border-border-strong '
                    'bg-surface px-3 py-2 text-text-primary shadow-sm '
                    'placeholder:text-text-tertiary focus:border-border-focus '
                    'focus:outline-none focus:ring-2 focus:ring-border-focus'
                ),
            }
        )
        self.fields['password'].widget.attrs.update(
            {
                'autocomplete': 'current-password',
                'class': (
                    'mt-2 block min-h-11 w-full rounded-lg border border-border-strong '
                    'bg-surface px-3 py-2 text-text-primary shadow-sm '
                    'placeholder:text-text-tertiary focus:border-border-focus '
                    'focus:outline-none focus:ring-2 focus:ring-border-focus'
                ),
            }
        )
        if self.is_bound:
            if self['username'].errors:
                self.fields['username'].widget.attrs['aria-invalid'] = 'true'
                _adicionar_aria_describedby(
                    self.fields['username'],
                    'username-error',
                )
            if self['password'].errors:
                self.fields['password'].widget.attrs['aria-invalid'] = 'true'
                _adicionar_aria_describedby(
                    self.fields['password'],
                    'password-error',
                )
            if self.non_field_errors():
                self.fields['username'].widget.attrs['aria-invalid'] = 'true'
                _adicionar_aria_describedby(
                    self.fields['username'],
                    'login-error',
                )
                self.fields['password'].widget.attrs['aria-invalid'] = 'true'
                _adicionar_aria_describedby(
                    self.fields['password'],
                    'login-error',
                )
