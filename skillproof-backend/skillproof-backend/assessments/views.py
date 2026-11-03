import json
import logging
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import TestAttempt, SkillScore
from .serializers import TestAttemptSerializer, StartAttemptSerializer, SubmitAttemptSerializer
from skills.models import SkillTest
from .tasks import process_test_attempt

logger = logging.getLogger(__name__)

class MyAttemptsListView(generics.ListAPIView):
    serializer_class = TestAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TestAttempt.objects.filter(
            user=self.request.user
        ).select_related(
            'test', 'test__category', 'score'
        ).order_by('-started_at')

class AttemptDetailView(generics.RetrieveAPIView):
    serializer_class = TestAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TestAttempt.objects.filter(
            user=self.request.user
        ).select_related('test', 'test__category', 'score')

class StartAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartAttemptSerializer(data=request.data)
        if serializer.is_valid():
            test_id = serializer.validated_data['test_id']
            test = get_object_or_404(SkillTest, id=test_id, is_active=True)
            
            attempt = TestAttempt.objects.create(
                user=request.user,
                test=test,
                status='in_progress',
                started_at=timezone.now()
            )
            return Response({'attempt_id': attempt.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubmitAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        attempt = get_object_or_404(TestAttempt, pk=pk, user=request.user)
        
        if attempt.status != 'in_progress':
            return Response({"error": "Only in_progress attempts can be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle audio file upload for communication tests
        audio_file = request.FILES.get('audio_file')
        if audio_file:
            import os
            from django.conf import settings as django_settings
            recordings_dir = os.path.join(django_settings.MEDIA_ROOT, 'recordings')
            os.makedirs(recordings_dir, exist_ok=True)
            
            file_name = f'attempt_{attempt.id}_{audio_file.name}'
            file_path = os.path.join(recordings_dir, file_name)
            
            with open(file_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            
            attempt.recording_url = file_path
        
        # Handle other fields from JSON payload
        serializer = SubmitAttemptSerializer(data=request.data)
        if serializer.is_valid():
            attempt.recording_url = serializer.validated_data.get('recording_url', attempt.recording_url)
            attempt.code_submission = serializer.validated_data.get('code_submission', attempt.code_submission)
            attempt.project_url = serializer.validated_data.get('project_url', attempt.project_url)
            
            keystrokes = serializer.validated_data.get('keystroke_log', attempt.keystroke_log) or {}
            if isinstance(keystrokes, dict):
                cheating_flags = serializer.validated_data.get('cheating_flags')
                # Also check request.data for 'cheating_flags' in case it came as a string (FormData)
                if not cheating_flags and 'cheating_flags' in request.data:
                    try:
                        cheating_flags = json.loads(request.data['cheating_flags'])
                    except (json.JSONDecodeError, ValueError, TypeError):
                        pass
                if cheating_flags:
                    keystrokes['frontend_cheating_flags'] = cheating_flags
            
            attempt.keystroke_log = keystrokes
        
        attempt.status = 'processing'
        attempt.completed_at = timezone.now()
        attempt.save()

        # Dispatch Celery task
        process_test_attempt.delay(attempt.id)

        return Response({
            "message": "Attempt submitted successfully and is processing.", 
            "status": "processing",
            "attempt_id": attempt.id
        }, status=status.HTTP_200_OK)

class StatusCheckView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        attempt = get_object_or_404(TestAttempt, pk=pk, user=request.user)
        return Response({'status': attempt.status})

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cache_key = f'analytics_user_{user.id}'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)
        
        # Monthly score trend
        monthly_trends = SkillScore.objects.filter(attempt__user=user).annotate(
            month=TruncMonth('generated_at')
        ).values('month').annotate(
            avg_score=Avg('overall_score'),
            count=Count('id')
        ).order_by('month')
        
        trends = [{
            'date': item['month'].strftime('%Y-%m'),
            'score': round(item['avg_score']),
            'tests_taken': item['count']
        } for item in monthly_trends if item['month']]

        # Skill breakdown
        skills = SkillScore.objects.filter(attempt__user=user).values(
            'attempt__test__category__name'
        ).annotate(
            avg_score=Avg('overall_score'),
            count=Count('id')
        ).order_by('-avg_score')
        
        radar = [{
            'subject': item['attempt__test__category__name'],
            'score': round(item['avg_score']),
            'fullMark': 100
        } for item in skills]
        
        # Calculate rank percentile
        user_avg = SkillScore.objects.filter(attempt__user=user).aggregate(Avg('overall_score'))['overall_score__avg']
        rank_percentile = 100
        if user_avg is not None:
            all_avgs = list(SkillScore.objects.values('attempt__user').annotate(avg=Avg('overall_score')).values_list('avg', flat=True))
            better_count = sum(1 for avg in all_avgs if avg > user_avg)
            total_users = len(all_avgs)
            if total_users > 1:
                rank_percentile = max(1, int((better_count / total_users) * 100))
            else:
                rank_percentile = 1

        # Calculate matching jobs
        passed_tests = TestAttempt.objects.filter(
            user=user, 
            status='completed', 
            score__overall_score__gte=60
        ).values_list('test_id', flat=True)
        
        from jobs.models import JobListing
        matching_jobs_count = JobListing.objects.filter(
            is_active=True, 
            required_tests__in=passed_tests
        ).distinct().count()

        result = {
            'trends': trends,
            'radar': radar,
            'total_tests': sum(item['count'] for item in skills) if skills else 0,
            'rank_percentile': rank_percentile,
            'matching_jobs_count': matching_jobs_count
        }
        
        # Cache for 60 seconds to reduce DB load on repeated dashboard visits
        cache.set(cache_key, result, 60)
        return Response(result)

class SkillInsightsView(APIView):
    """
    AI-powered Skill Gap Analyzer & Personalized Learning Roadmap.
    Returns cached insights or generates fresh ones when the user
    has completed new assessments since last generation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'candidate':
            return Response(
                {"error": "Skill insights are only available for candidates."},
                status=status.HTTP_403_FORBIDDEN
            )

        from .insights import generate_skill_insights
        try:
            result = generate_skill_insights(user)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Skill insights generation error: {e}")
            return Response(
                {"error": "Failed to generate skill insights. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if result is None:
            return Response({
                "empty": True,
                "message": "Complete at least one assessment to unlock your personalized Skill Insights."
            })

        return Response(result)
