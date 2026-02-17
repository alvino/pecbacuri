from django.urls import path, include
from . import views
from .views import  DashboardView


urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('logout/', views.logout, name='logout'),
]