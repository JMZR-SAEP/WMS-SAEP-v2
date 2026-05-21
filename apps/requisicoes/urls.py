from django.urls import path

from apps.requisicoes import views

app_name = 'requisicoes'

urlpatterns = [
    path('nova/', views.NovaRequisicaoView.as_view(), name='nova'),
    path('<int:pk>/', views.DetalheRequisicaoView.as_view(), name='detalhe'),
]
