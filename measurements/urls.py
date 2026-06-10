from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name="dashboard"),
    path('project/<int:pk>/', views.project_detail, name="project_detail"),
    path('project/<int:pk>/export-csv/', views.export_project_csv, name="export_project_csv"),
    path('project/<int:pk>/add-electrode/', views.add_electrode_to_project, name="add_electrode_to_project"),
    path('project/<int:pk>/add-biomarker/', views.add_biomarker_to_project, name="add_biomarker_to_project"),
    path('measurement/<int:pk>/', views.measurement_detail, name='measurement_detail'),
    path('api/calendar/', views.calendar_data, name='calendar_api'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('register/', views.register, name='register'),
    path("create/", views.create_structure, name="create_structure"),
    path("projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path('projects/<int:project_id>/measurements/create/', views.measurement_create, name='measurement_create'),
    path('project/<int:pk>/remove-electrode/<int:electrode_id>/', views.remove_electrode_from_project, name="remove_electrode_from_project"),
    path('project/<int:pk>/remove-biomarker/<int:biomarker_id>/', views.remove_biomarker_from_project, name="remove_biomarker_from_project"),
]
