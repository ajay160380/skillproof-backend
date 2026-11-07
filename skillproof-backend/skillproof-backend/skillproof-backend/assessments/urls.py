from django.urls import path
from .views import StartAttemptView, SubmitAttemptView, AttemptDetailView, MyAttemptsListView, StatusCheckView, AnalyticsView, SkillInsightsView

urlpatterns = [
    path('start/', StartAttemptView.as_view(), name='start_attempt'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('skill-insights/', SkillInsightsView.as_view(), name='skill_insights'),
    path('<int:pk>/submit/', SubmitAttemptView.as_view(), name='submit_attempt'),
    path('<int:pk>/status/', StatusCheckView.as_view(), name='status_check'),
    path('<int:pk>/', AttemptDetailView.as_view(), name='attempt_detail'),
    path('my-attempts/', MyAttemptsListView.as_view(), name='my_attempts'),
]
