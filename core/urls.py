from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.conf import settings

from .views import  DashboardView, ZootecnicoAnalyticsView, logout

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('dashboard/zootecnico/', ZootecnicoAnalyticsView.as_view(), name='zootecnico_stats'),
    path('logout/', logout, name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon.ico')),
]