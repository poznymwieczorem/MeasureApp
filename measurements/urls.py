from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name="dashboard"),
    path('project/<int:pk>/', views.project_detail, name="project_detail"),
    path('measurement/<int:pk>/', views.measurement_detail, name='measurement_detail'),
    path('api/calendar/', views.calendar_data, name='calendar_api'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('register/', views.register, name='register'),
    path("create/", views.create_structure, name="create_structure"),
]