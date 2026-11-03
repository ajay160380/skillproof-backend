from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('candidate', 'Candidate'),
        ('recruiter', 'Recruiter'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
        ('manager', 'Manager'),
        ('auditor', 'Auditor'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='candidate')
    full_name = models.CharField(max_length=255)
    avatar_url = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(blank=True)
    headline = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    github_url = models.URLField(max_length=500, blank=True, null=True)
    linkedin_url = models.URLField(max_length=500, blank=True, null=True)
    website_url = models.URLField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
