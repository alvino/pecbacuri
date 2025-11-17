from django.urls import path, include
from . import views
from .views import DashboardFinanceiroCBV, AnaliseDesempenhoLotesCBV, AlertaRiscoListView, AnimalViewSet, AnalisePorIdadeView
from rest_framework.routers import DefaultRouter


# Cria um roteador e registra os ViewSets
router = DefaultRouter()
router.register(r'animais', AnimalViewSet)
# Você registraria outros ViewSets aqui (ex: router.register(r'pesagens', PesagemViewSet))


urlpatterns = [
    path('analise/idade/', AnalisePorIdadeView.as_view(), name='analise_por_idade'),
    path('alertas-risco/', AlertaRiscoListView.as_view(), name='alertas_risco'),
    path('alertas/', views.alertas_de_manejo, name='alertas_de_manejo'),
    path('relatorios/desempenho-pasto/', views.relatorio_desempenho_pasto, name='relatorio_desempenho_pasto'),
    path('financeiro/', DashboardFinanceiroCBV.as_view(), name='dashboard_financeiro'),
    path('pastos/', views.PastoListView.as_view(), name='pasto_list'), 
    path('pasto/<int:pk>/', views.PastoDetailView.as_view(), name='pasto_detail'),
    path('animais/', views.AnimalListView.as_view(), name='animal_list'),
    path('animal/<int:pk>/', views.AnimalDetailView.as_view(), name='animal_detail'), 
    path('', views.dashboard, name='dashboard'),
    path('home', views.dashboard, name='home'),
    path('tratamentos', views.TratamentoSaudeListView.as_view(), name='tratamentos_saude_list'),
    path('reproducao', views.ReproducaoListView.as_view(), name='manejo_reprodutivo_list'),
    path('controle_peso/', views.PesagemListView.as_view(), name='controle_peso_list'),
    path('analise_lotes/', AnaliseDesempenhoLotesCBV.as_view(), name='analise_lotes'),
    path('analise_idade_sexo_lotes/', views.analise_idade_sexo_lotes, name='analise_idade_sexo_lotes'),
    path('logout/', views.logout, name='logout'),

    # Rotas da API (JSON)
    # Tudo em http://127.0.0.1:8000/api/v1/
    path('api/v1/', include(router.urls)),
]