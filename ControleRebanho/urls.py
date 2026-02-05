from django.urls import path, include
from . import views
from .views import DashboardFinanceiroCBV, AnaliseDesempenhoLotesCBV, AlertaRiscoListView, AnimalViewSet, AnalisePorIdadeView, DashboardView, AnimalCreateView, AnimalUpdateView, PesagemCreateView, PastoListView, PastoDetailView, PastoCreateView, PastoUpdateView, AnimalListView, AnimalDetailView, PesagemListView, ReproducaoListView, TratamentoSaudeListView, TratamentoCreateView, ReproducaoCreateView,  PesagemUpdateView, MovimentacaoPastoCreateView
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
    path('pastos/', PastoListView.as_view(), name='pasto_list'), 
    path('pasto/<int:pk>/', PastoDetailView.as_view(), name='pasto_detail'),
    path('pasto/novo/', PastoCreateView.as_view(), name='pasto_create'),
    path('pasto/<int:pk>/editar/', PastoUpdateView.as_view(), name='pasto_update'),
    path('animais/', AnimalListView.as_view(), name='animal_list'),
    path('animal/<int:pk>/', AnimalDetailView.as_view(), name='animal_detail'), 
    path('animal/novo/', AnimalCreateView.as_view(), name='animal_create'),
    path('animal/<int:pk>/editar/', AnimalUpdateView.as_view(), name='animal_update'),
    path('', DashboardView.as_view(), name='dashboard'),
    path('home', DashboardView.as_view(), name='home'),
    path('tratamentos', TratamentoSaudeListView.as_view(), name='tratamentos_saude_list'),
    path('tratamentos/novo-tratamento/', TratamentoCreateView.as_view(),name='tratamento_create'),
    path('reproducao', ReproducaoListView.as_view(), name='manejo_reprodutivo_list'),
    path('reproducao/nova-reproducao/', ReproducaoCreateView.as_view(),name='reproducao_create'),
    path('controle_peso/', PesagemListView.as_view(), name='controle_peso_list'),
    path('controle_peso/nova-pesagem/', PesagemCreateView.as_view(), name='pesagem_create'),
    path('controle_peso/<int:pk>/editar/', PesagemUpdateView.as_view(), name='pesagem_update'),
    path('analise_lotes/', AnaliseDesempenhoLotesCBV.as_view(), name='analise_lotes'),
    path('analise_idade_sexo_lotes/', views.analise_idade_sexo_lotes, name='analise_idade_sexo_lotes'),
    path('logout/', views.logout, name='logout'),
    path('animais/movimentar/', MovimentacaoPastoCreateView.as_view(), name='movimentar_animais'),

    # Rotas da API (JSON)
    # Tudo em http://127.0.0.1:8000/api/v1/
    path('api/v1/', include(router.urls)),
]