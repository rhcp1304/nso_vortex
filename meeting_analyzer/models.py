# meeting_analyzer/models.py
from django.db import models

class AnalysisTask(models.Model):
    """Stores uploaded files for a single analysis task."""
    ppt_file = models.FileField(upload_to='uploads/')
    video_file = models.FileField(upload_to='uploads/')
    transcript_file = models.FileField(upload_to='uploads/')
    report_file = models.FileField(upload_to='reports/', null=True, blank=True) # Added for final report
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Pending')

    def __str__(self):
        return f"Task {self.id} - {self.status}"