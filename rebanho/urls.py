from django.urls import path, include
from . import views
from .views import  AnaliseDesempenhoLotesCBV, AnimalViewSet, AnalisePorIdadeView,  AnimalCreateView, AnimalUpdateView,  AnimalListView, AnimalDetailView
from infraestrutura.views import MovimentacaoPastoCreateView
from rest_framework.routers import DefaultRouter


# Cria um roteador e registra os ViewSets
router = DefaultRouter()
router.register(r'animais', AnimalViewSet)
# Você registraria outros ViewSets aqui (ex: router.register(r'pesagens', PesagemViewSet))


urlpatterns = [
    path('analise/idade/', AnalisePorIdadeView.as_view(), name='analise_por_idade'),
    path('animais/', AnimalListView.as_view(), name='animal_list'),
    path('animal/<int:pk>/', AnimalDetailView.as_view(), name='animal_detail'), 
    path('animal/novo/', AnimalCreateView.as_view(), name='animal_create'),
    path('animal/<int:pk>/editar/', AnimalUpdateView.as_view(), name='animal_update'),
    path('animais/movimentar/', MovimentacaoPastoCreateView.as_view(), name='movimentar_animais'),
    path('analise_lotes/', AnaliseDesempenhoLotesCBV.as_view(), name='analise_lotes'),

    # Rotas da API (JSON)
    # Tudo em http://127.0.0.1:8000/api/v1/
    path('api/v1/', include(router.urls)),
]