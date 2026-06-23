"""URLs de notificações."""

from django.urls import path

from apps.notificacoes import views

app_name = 'notificacoes'

urlpatterns = [
    path('', views.lista_notificacoes_view, name='lista'),
    path('<int:pk>/lida/', views.marcar_lida_view, name='marcar_lida'),
    path(
        'marcar-todas-lidas/', views.marcar_todas_lidas_view, name='marcar_todas_lidas'
    ),
]
