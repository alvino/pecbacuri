from django.urls import path, include
from . import views
from .views import AlertaRiscoListView,  PesagemCreateView,   PesagemListView, ReproducaoListView, TratamentoSaudeListView, TratamentoCreateView, ReproducaoCreateView,  PesagemUpdateView


urlpatterns = [
   
    path('alertas-risco/', AlertaRiscoListView.as_view(), name='alertas_risco'),
    path('alertas/', views.alertas_de_manejo, name='alertas_de_manejo'),
   
    path('tratamentos', TratamentoSaudeListView.as_view(), name='tratamentos_saude_list'),
    path('tratamentos/novo-tratamento/', TratamentoCreateView.as_view(),name='tratamento_create'),
    path('reproducao', ReproducaoListView.as_view(), name='manejo_reprodutivo_list'),
    path('reproducao/nova-reproducao/', ReproducaoCreateView.as_view(),name='reproducao_create'),
    path('controle_peso/', PesagemListView.as_view(), name='controle_peso_list'),
    path('controle_peso/nova-pesagem/', PesagemCreateView.as_view(), name='pesagem_create'),
    path('controle_peso/<int:pk>/editar/', PesagemUpdateView.as_view(), name='pesagem_update'),
    
]