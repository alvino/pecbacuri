from django.urls import path
from .views import DashboardFinanceiroCBV


urlpatterns = [
   path('financeiro/', DashboardFinanceiroCBV.as_view(), name='dashboard_financeiro'),
  
]