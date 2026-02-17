from django.urls import path
from .views import  PastoListView, PastoDetailView, PastoCreateView, PastoUpdateView, relatorio_desempenho_pasto

urlpatterns = [
    
    path('pastos/', PastoListView.as_view(), name='pasto_list'), 
    path('pasto/<int:pk>/', PastoDetailView.as_view(), name='pasto_detail'),
    path('pasto/novo/', PastoCreateView.as_view(), name='pasto_create'),
    path('pasto/<int:pk>/editar/', PastoUpdateView.as_view(), name='pasto_update'),
    path('relatorios/desempenho-pasto/', relatorio_desempenho_pasto, name='relatorio_desempenho_pasto'),

]