from django.urls import path
from . import views

urlpatterns = [
    # This path maps the URL "process-transcript/" to the "process_transcript" function in views.py
    path('process-transcript/', views.process_transcript, name='process_transcript'),
]
