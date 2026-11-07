from django.urls import path
from .views import ResumeUploadView, MyResumeView, SuggestedTestsView, ResumeViewFileView, ResumeReparseView

urlpatterns = [
    path('upload/', ResumeUploadView.as_view(), name='resume-upload'),
    path('my-resume/', MyResumeView.as_view(), name='my-resume'),
    path('view/', ResumeViewFileView.as_view(), name='resume-view-file'),
    path('reparse/', ResumeReparseView.as_view(), name='resume-reparse'),
    path('suggested-tests/', SuggestedTestsView.as_view(), name='suggested-tests'),
]
