# meeting_analyzer/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.analysis_ui, name='analysis_ui'),
    path('start-analysis/', views.start_analysis, name='start_analysis'),
]