from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # This URL pattern includes the admin site.
    path('admin/', admin.site.urls),

    # This is the line that includes the URLs from your meeting agent app.
    # Any request starting with 'meeting-agent/' will be routed to your app's urls.py file.
    path('meeting-agent/', include('nso_meeting_agent.urls')),
]
