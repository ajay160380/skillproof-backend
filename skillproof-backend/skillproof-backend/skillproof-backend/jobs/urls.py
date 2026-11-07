from django.urls import path
from .views import (
    JobCreateView, JobListView, JobDetailView, JobApplyView,
    JobProgressView, RecruiterJobListView, RecruiterJobApplicantsView,
    CompanyRequirementView, PublicCompanyRequirementView,
    TalentMatchView, SendInviteView, MyInvitesView,
    ProposeInterviewView, MyInterviewsView, RespondInterviewView,
    AIGenerateJobDescriptionView, AIGenerateInterviewPrepView
)

urlpatterns = [
    path('', JobListView.as_view(), name='job-list'),
    path('create/', JobCreateView.as_view(), name='job-create'),
    path('generate-description/', AIGenerateJobDescriptionView.as_view(), name='job-generate-description'),
    path('generate-prep/', AIGenerateInterviewPrepView.as_view(), name='job-generate-prep'),
    path('my-listings/', RecruiterJobListView.as_view(), name='recruiter-jobs'),
    path('my-listings/<int:pk>/applicants/', RecruiterJobApplicantsView.as_view(), name='recruiter-job-applicants'),
    path('company-requirements/', CompanyRequirementView.as_view(), name='company-requirements'),
    path('company-requirements/<int:recruiter_id>/', PublicCompanyRequirementView.as_view(), name='public-company-requirements'),
    path('talent-match/', TalentMatchView.as_view(), name='talent-match'),
    path('invites/', MyInvitesView.as_view(), name='my-invites'),
    path('invites/send/', SendInviteView.as_view(), name='send-invite'),
    
    path('interviews/propose/', ProposeInterviewView.as_view(), name='propose-interview'),
    path('interviews/my-interviews/', MyInterviewsView.as_view(), name='my-interviews'),
    path('interviews/<int:pk>/respond/', RespondInterviewView.as_view(), name='respond-interview'),

    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('<int:pk>/apply/', JobApplyView.as_view(), name='job-apply'),
    path('<int:pk>/my-progress/', JobProgressView.as_view(), name='job-progress'),
]
