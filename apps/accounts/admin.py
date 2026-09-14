import logging

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import (
    BaseUserCreationForm,
    ReadOnlyPasswordHashField,
    SetPasswordMixin,
    UsernameField,
)
from django.db import OperationalError
from django.http import HttpResponseRedirect

from apps.accounts.models import Setor, User, VinculoAuxiliar
from apps.core.exceptions import (
    ConflitoDominio,
    ErroDominio,
    EstadoInvalido,
    PermissaoNegada,
)

logger = logging.getLogger(__name__)

# 40P01 deadlock_detected, 40001 serialization_failure: a transação foi abortada
# por concorrência e a mesma operação, repetida, tende a passar.
SQLSTATES_RETENTAVEIS = frozenset({'40P01', '40001'})


def _changeform_com_captura_dominio(
    admin_instance, request, object_id, form_url, extra_context
):
    """Wrapper: captura ErroDominio de save_model e exibe como mensagem.

    O nível segue o mapeamento de `docs/CONVENTIONS.md`: conflito de estado é
    `warning` (a ação não foi aplicada, mas o estado atual é compreensível);
    dado inválido é `error` (o usuário precisa corrigir).
    """
    from django.core.exceptions import PermissionDenied

    try:
        return admin.ModelAdmin.changeform_view(
            admin_instance, request, object_id, form_url, extra_context
        )
    except PermissaoNegada as exc:
        raise PermissionDenied(str(exc)) from exc
    except (EstadoInvalido, ConflitoDominio) as exc:
        admin_instance.message_user(request, str(exc), level=messages.WARNING)
        return HttpResponseRedirect(request.get_full_path())
    except ErroDominio as exc:
        admin_instance.message_user(request, str(exc), level=messages.ERROR)
        return HttpResponseRedirect(request.get_full_path())
    except OperationalError as exc:
        # Contenção, não prevenção: a ordem canônica de locks em `services` é o
        # que evita o ciclo. Este ramo existe para o caso de um escapar mesmo
        # assim, e é restrito por SQLSTATE — dizer "tente novamente" para uma
        # conexão caída transformaria indisponibilidade em erro de formulário.
        if getattr(exc.__cause__, 'sqlstate', None) not in SQLSTATES_RETENTAVEIS:
            raise
        logger.warning(
            'operação administrativa abortada por concorrência', exc_info=exc
        )
        admin_instance.message_user(
            request,
            'A operação não pôde ser concluída por concorrência com outra '
            'alteração de cadastro. Tente novamente.',
            level=messages.ERROR,
        )
        return HttpResponseRedirect(request.get_full_path())


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'classificacao', 'chefe', 'ativo')
    list_filter = ('classificacao', 'ativo')
    search_fields = ('codigo', 'nome')
    ordering = ('nome',)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        return _changeform_com_captura_dominio(
            self, request, object_id, form_url, extra_context
        )

    def save_model(self, request, obj, form, change):
        # Antes do ramo de chefia: se os dois campos mudarem no mesmo POST e a
        # troca de chefe rodasse primeiro, o super() gravaria ativo=False sem
        # passar pelo service.
        if change and 'ativo' in form.changed_data and not obj.ativo:
            from apps.accounts.services import desativar_setor
            from apps.core.exceptions import ConflitoDominio

            campos_extras = set(form.changed_data) - {'ativo'}
            if campos_extras:
                raise ConflitoDominio(
                    'Desative o setor separadamente de outras alterações de cadastro.',
                    code='desativacao_setor_com_campos_extras',
                )
            desativar_setor(ator_id=request.user.pk, setor_id=obj.pk)
            return  # service já persistiu; super sobrescreveria com os dados do form

        if change and 'chefe' in form.changed_data:
            from apps.accounts.services import trocar_chefe_setor
            from apps.core.exceptions import ConflitoDominio

            if obj.chefe_id is None:
                raise ConflitoDominio(
                    'Não é possível remover a chefia sem indicar um substituto.',
                    code='chefe_nulo',
                )
            trocar_chefe_setor(
                ator_id=request.user.pk,
                setor_id=obj.pk,
                novo_chefe_id=obj.chefe_id,
            )
        super().save_model(request, obj, form, change)


class UserCreationForm(BaseUserCreationForm):
    """Formulário de criação de usuário no admin (issue #217).

    `BaseUserCreationForm` é a base documentada pelo Django para adaptar a
    criação a um model de usuário customizado: `Meta.model`/`fields` trocam
    `username` por `matricula`, e `clean`/`_post_clean`/`save` (herdados)
    validam senha+confirmação e gravam com `set_password` — nunca em texto
    puro.

    Sem `usable_password` (o Django 6 traz essa opção via
    `AdminUserCreationForm`/`SetUnusablePasswordMixin`, que permite criar
    usuário sem senha para autenticação por outro backend, ex. SSO/LDAP): o
    domínio não tem backend alternativo em `AUTHENTICATION_BACKENDS` — todo
    usuário entra por matrícula + senha, então a opção só criaria um estado
    que o login nunca aceita.
    """

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('matricula', 'nome', 'email', 'setor')
        field_classes = {'matricula': UsernameField}


class UserChangeForm(forms.ModelForm):
    """Formulário de edição no admin (issue #217): senha vira hash somente leitura.

    Mesma estrutura do `django.contrib.auth.forms.UserChangeForm` — que não dá
    para reaproveitar direto porque o `Meta.model` dele aponta para
    `auth.models.User`, não para este model.
    """

    password = ReadOnlyPasswordHashField(
        label='Senha',
        help_text=(
            'Senhas não ficam salvas em texto puro, então não há como ver a '
            'senha deste usuário.'
        ),
    )

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get('password')
        if password and self.instance and not self.instance.has_usable_password():
            password.help_text = (
                'Ative a autenticação por senha definindo uma senha para este usuário.'
            )
        user_permissions = self.fields.get('user_permissions')
        if user_permissions:
            user_permissions.queryset = user_permissions.queryset.select_related(
                'content_type'
            )


class AdminPasswordChangeForm(SetPasswordMixin, forms.Form):
    """Troca de senha de usuário existente pelo admin (issue #217).

    Mesma decisão de `UserCreationForm`: sem a opção `usable_password` do
    Django 6 (`django.contrib.auth.forms.AdminPasswordChangeForm` a traz via
    `SetUnusablePasswordMixin`) — aqui a senha é sempre exigida.
    """

    required_css_class = 'required'
    password1, password2 = SetPasswordMixin.create_password_fields()

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['autofocus'] = True

    def clean(self):
        self.validate_passwords()
        self.validate_password_for_user(self.user)
        # `django.contrib.auth.admin.UserAdmin.user_change_password` (herdado
        # por `UserAdmin` abaixo) lê `set_usable_password` para decidir se o
        # POST é válido. Aqui a senha é sempre obrigatória, então o valor é
        # sempre `True` — nunca há o ramo de "desativar senha".
        self.cleaned_data['set_usable_password'] = True
        return super().clean()

    def save(self, commit=True):
        return self.set_password_and_save(self.user, commit=commit)

    @property
    def changed_data(self):
        data = super().changed_data
        if 'password1' in data and 'password2' in data:
            return ['password']
        return []


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Admin de usuário, adaptado a `matricula` como `USERNAME_FIELD` (#217).

    Herda de `django.contrib.auth.admin.UserAdmin` em vez de montar tudo à
    mão: o Django já resolve criação com senha+confirmação, edição com hash
    somente leitura e a view de troca de senha (`user_change_password`) —
    reescrever isso duplicaria lógica já testada pelo próprio framework.
    Todo atributo/método que a base referencia e que não existe neste model
    (`username`, `first_name`, `last_name`, `add_fieldsets` da base) é
    sobrescrito abaixo.
    """

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    # O template da base oferece "desativar autenticação por senha", que
    # `AdminPasswordChangeForm` não implementa (ver o comentário do template).
    change_user_password_template = 'admin/accounts/user/change_password.html'

    list_display = ('matricula', 'nome', 'email', 'setor', 'is_active', 'is_staff')
    list_filter = ('setor', 'is_active', 'is_staff')
    search_fields = ('matricula', 'nome', 'email')
    ordering = ('nome',)
    fieldsets = (
        (None, {'fields': ('matricula', 'password')}),
        ('Informações Pessoais', {'fields': ('nome', 'email', 'setor')}),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    # Substitui o `add_fieldsets` da base (`username`, `usable_password`,
    # `password1`, `password2`): sem `usable_password` (ver `UserCreationForm`
    # acima) e com `nome`/`email`/`setor` — sem essa seção a criação regrediria
    # (hoje dá para lotar o usuário na mesma tela) e `nome` é obrigatório no
    # model, então deixá-lo de fora criaria usuário com nome vazio sem avisar.
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('matricula', 'password1', 'password2'),
            },
        ),
        ('Informações Pessoais', {'fields': ('nome', 'email', 'setor')}),
    )

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        return _changeform_com_captura_dominio(
            self, request, object_id, form_url, extra_context
        )

    def save_model(self, request, obj, form, change):
        if change and 'is_active' in form.changed_data and not obj.is_active:
            from apps.accounts.services import desativar_usuario
            from apps.core.exceptions import ConflitoDominio

            campos_extras = set(form.changed_data) - {'is_active'}
            if campos_extras:
                raise ConflitoDominio(
                    'Desative o usuário separadamente de outras alterações de cadastro.',
                    code='desativacao_com_campos_extras',
                )
            desativar_usuario(ator_id=request.user.pk, usuario_id=obj.pk)
            return  # service já persistiu; super sobrescreveria dados de auditoria

        if change and 'setor' in form.changed_data:
            from apps.accounts.services import remanejar_usuario
            from apps.core.exceptions import ConflitoDominio

            campos_extras = set(form.changed_data) - {'setor'}
            if campos_extras:
                raise ConflitoDominio(
                    'Remaneje a lotação separadamente de outras alterações de cadastro.',
                    code='remanejamento_com_campos_extras',
                )
            remanejar_usuario(
                ator_id=request.user.pk,
                usuario_id=obj.pk,
                novo_setor_id=obj.setor_id,
            )
            return  # service já persistiu; super sobrescreveria com os dados do form
        super().save_model(request, obj, form, change)


@admin.register(VinculoAuxiliar)
class VinculoAuxiliarAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'setor', 'ativo', 'criado_em')
    list_filter = ('ativo', 'setor')
    search_fields = ('usuario__nome', 'setor__nome')
    ordering = ('-criado_em',)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        return _changeform_com_captura_dominio(
            self, request, object_id, form_url, extra_context
        )

    def save_model(self, request, obj, form, change):
        from apps.core.exceptions import ConflitoDominio

        if not change and not obj.ativo:
            raise ConflitoDominio(
                'Não é permitido criar vínculo auxiliar já inativo pelo admin.',
                code='vinculo_inativo_admin',
            )

        if not change and obj.ativo:
            from apps.accounts.services import ativar_vinculo_auxiliar

            vinculo = ativar_vinculo_auxiliar(
                ator_id=request.user.pk,
                usuario_id=obj.usuario_id,
                setor_id=obj.setor_id,
            )
            obj.pk = vinculo.pk
            return  # service já persistiu; super causaria INSERT duplo

        if 'ativo' in form.changed_data:
            campos_identidade = {'usuario', 'setor'} & set(form.changed_data)
            if change and campos_identidade:
                raise ConflitoDominio(
                    'Altere usuário/setor separadamente da ativação do vínculo auxiliar.',
                    code='vinculo_identidade_com_status',
                )

            from apps.accounts.services import (
                ativar_vinculo_auxiliar,
                desativar_vinculo_auxiliar,
            )

            if obj.ativo:
                vinculo = ativar_vinculo_auxiliar(
                    ator_id=request.user.pk,
                    usuario_id=obj.usuario_id,
                    setor_id=obj.setor_id,
                )
                obj.pk = vinculo.pk
                return  # service já persistiu; super causaria INSERT duplo
            elif obj.pk:
                desativar_vinculo_auxiliar(ator_id=request.user.pk, vinculo_id=obj.pk)
                return  # service já persistiu desativado_em; super sobrescreveria
        super().save_model(request, obj, form, change)
