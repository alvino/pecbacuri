from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
from .views import  DashboardView


urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('logout/', views.logout, name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),

]