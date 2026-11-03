from django.db import models
from django.conf import settings

from cloudinary_storage.storage import RawMediaCloudinaryStorage

class Resume(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to='resumes/', storage=RawMediaCloudinaryStorage())
    extracted_text = models.TextField(blank=True, null=True)
    extracted_skills = models.JSONField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Resume for {self.user.email} ({self.parsing_status})"
