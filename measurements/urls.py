from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name="dashboard"),
    path('project/<int:pk>/', views.project_detail, name="project_detail"),
    #path('measurement/<int:pk>/', views.measurement_detail, name='measurement_detail'),
]