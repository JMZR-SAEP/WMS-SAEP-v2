from django.contrib import admin

from apps.notificacoes.models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'tipo', 'requisicao_id', 'lida', 'criado_em')
    list_filter = ('tipo', 'lida')
    search_fields = ('destinatario__matricula', 'destinatario__nome')
    readonly_fields = ('destinatario', 'tipo', 'requisicao_id', 'criado_em')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions
