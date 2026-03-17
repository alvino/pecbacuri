from django.urls import path
from .views import CategoriaDespesaCreateView, DashboardFinanceiroCBV, DespesaCreateView, DespesaListView, RegistroCustoListView, RelatorioDesempenhoPastoView, VendaCreateView


urlpatterns = [
   path('financeiro/', DashboardFinanceiroCBV.as_view(), name='dashboard_financeiro'),
   path('relatorios/desempenho-pasto/', RelatorioDesempenhoPastoView.as_view(), name='relatorio_desempenho_pasto'),
   path('despesas/nova/', DespesaCreateView.as_view(), name='despesa_create'),
   path('categorias-despesa/nova/', CategoriaDespesaCreateView.as_view(), name='categoria_despesa_create'),
   path('vendas/nova/', VendaCreateView.as_view(), name='venda_create'),
   path('despesas/', DespesaListView.as_view(), name='despesa_list'),
   path('custos/', RegistroCustoListView.as_view(), name='custo_list'), # Alias para despesas, já que no modelo se chama RegistroDeCusto
]