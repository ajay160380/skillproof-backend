from django.db import models
from django.conf import settings
from skills.models import SkillTest

class JobListing(models.Model):
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_listings')
    company_name = models.CharField(max_length=255)
    role_title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255, blank=True, null=True)
    salary_range = models.CharField(max_length=100, blank=True, null=True)
    min_score = models.IntegerField(default=70, help_text="Minimum score required to be eligible")
    required_tests = models.ManyToManyField(SkillTest, related_name='job_listings')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    application_deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.role_title} at {self.company_name}"

class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_applications')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    overall_fit_score = models.IntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('candidate', 'job_listing')

    def __str__(self):
        return f"{self.candidate.email} - {self.job_listing.role_title} ({self.status})"

class CompanyRequirement(models.Model):
    recruiter = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_requirements')
    company_name = models.CharField(max_length=255)
    required_skills = models.ManyToManyField('skills.SkillCategory', related_name='company_requirements', blank=True)
    preferred_min_score = models.IntegerField(null=True, blank=True)
    company_description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} Requirements (Recruiter: {self.recruiter.email})"

class DirectInvite(models.Model):
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invites')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_invites')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='invites', null=True, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('recruiter', 'candidate', 'job_listing')

    def __str__(self):
        return f"Invite from {self.recruiter.email} to {self.candidate.email}"

class Interview(models.Model):
    STATUS_CHOICES = (
        ('proposed', 'Proposed'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
    )
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scheduled_interviews')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate_interviews')
    job_listing = models.ForeignKey('JobListing', on_delete=models.CASCADE, related_name='interviews', null=True, blank=True)
    proposed_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview: {self.recruiter.email} with {self.candidate.email} at {self.proposed_time}"
