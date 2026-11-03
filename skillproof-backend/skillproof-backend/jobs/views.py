from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import F, Prefetch
from .models import JobListing, JobApplication, CompanyRequirement, DirectInvite, Interview
from .serializers import (
    JobListingSerializer, JobApplicationSerializer, JobApplicantSerializer,
    CompanyRequirementSerializer, DirectInviteSerializer, InterviewSerializer
)
from marketplace.permissions import IsRecruiter
from django.utils import timezone
from .services import update_job_applications
from badges.models import UserStats, Badge

User = get_user_model()

class JobCreateView(generics.CreateAPIView):
    serializer_class = JobListingSerializer
    permission_classes = [IsRecruiter]

    def perform_create(self, serializer):
        serializer.save(recruiter=self.request.user)

class JobListView(generics.ListAPIView):
    serializer_class = JobListingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['role_title', 'company_name']

    def get_queryset(self):
        return JobListing.objects.filter(is_active=True).order_by('-created_at')

class JobDetailView(generics.RetrieveAPIView):
    serializer_class = JobListingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobListing.objects.filter(is_active=True)

class JobApplyView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if request.user.role != 'candidate':
            return Response({"error": "Only candidates can apply to jobs"}, status=status.HTTP_403_FORBIDDEN)
            
        job = get_object_or_404(JobListing, pk=pk, is_active=True)
        app, created = JobApplication.objects.get_or_create(
            candidate=request.user,
            job_listing=job
        )
        
        # Manually trigger a progress update in case they already took tests
        update_job_applications(request.user.id)
        
        # Fetch it fresh after update
        app.refresh_from_db()
        return Response(JobApplicationSerializer(app).data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

class JobProgressView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        if request.user.role != 'candidate':
            return Response({"error": "Only candidates have job progress"}, status=status.HTTP_403_FORBIDDEN)
            
        app = get_object_or_404(JobApplication, job_listing_id=pk, candidate=request.user)
        
        # We can also return a list of completed test IDs here to help the frontend
        from assessments.models import SkillScore
        scores = SkillScore.objects.filter(
            attempt__user=request.user,
            attempt__status='completed'
        ).values_list('attempt__test_id', flat=True)
        
        data = JobApplicationSerializer(app).data
        data['completed_test_ids'] = list(set(scores))
        
        return Response(data)

class RecruiterJobListView(generics.ListAPIView):
    serializer_class = JobListingSerializer
    permission_classes = [IsRecruiter]
    
    def get_queryset(self):
        return JobListing.objects.filter(recruiter=self.request.user).order_by('-created_at')

class RecruiterJobApplicantsView(generics.ListAPIView):
    serializer_class = JobApplicantSerializer
    permission_classes = [IsRecruiter]
    
    def get_queryset(self):
        job_id = self.kwargs.get('pk')
        job = get_object_or_404(JobListing, pk=job_id, recruiter=self.request.user)
        return JobApplication.objects.filter(job_listing=job).select_related(
            'candidate'
        ).order_by(F('overall_fit_score').desc(nulls_last=True), '-completed_at')



class CompanyRequirementView(APIView):
    permission_classes = [IsRecruiter]
    
    def get(self, request):
        req, _ = CompanyRequirement.objects.get_or_create(
            recruiter=request.user,
            defaults={'company_name': request.user.company_name or ''}
        )
        return Response(CompanyRequirementSerializer(req).data)
        
    def put(self, request):
        req, _ = CompanyRequirement.objects.get_or_create(
            recruiter=request.user,
            defaults={'company_name': request.user.company_name or ''}
        )
        serializer = CompanyRequirementSerializer(req, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class PublicCompanyRequirementView(generics.RetrieveAPIView):
    serializer_class = CompanyRequirementSerializer
    permission_classes = []
    
    def get_object(self):
        recruiter_id = self.kwargs.get('recruiter_id')
        return get_object_or_404(CompanyRequirement, recruiter_id=recruiter_id)


class TalentMatchView(APIView):
    permission_classes = [IsRecruiter]

    def get(self, request):
        skill_id = request.query_params.get('skill_id')
        min_score = request.query_params.get('min_score', 0)
        
        candidates_query = UserStats.objects.exclude(
            user__role='recruiter'
        ).select_related('user')
        
        if skill_id:
            candidates_query = candidates_query.filter(
                user__badges__skill_category_id=skill_id,
                user__badges__score__overall_score__gte=min_score
            ).distinct()
            
        candidates_query = candidates_query.order_by('-total_points')[:50]
        
        # Prefetch top 3 badges for all candidates at once (avoids N+1)
        user_ids = [stat.user_id for stat in candidates_query]
        top_badges_by_user = {}
        if user_ids:
            all_badges = Badge.objects.filter(
                user_id__in=user_ids
            ).select_related(
                'skill_category', 'score'
            ).order_by('user_id', '-score__overall_score')
            
            for badge in all_badges:
                uid = badge.user_id
                if uid not in top_badges_by_user:
                    top_badges_by_user[uid] = []
                if len(top_badges_by_user[uid]) < 3:
                    top_badges_by_user[uid].append({
                        'skill_name': badge.skill_category.name,
                        'badge_level': badge.badge_level,
                        'score': badge.score.overall_score
                    })
        
        results = []
        for stat in candidates_query:

            results.append({
                'user_id': stat.user.id,
                'name': stat.user.full_name,
                'email': stat.user.email,
                'total_points': stat.total_points,
                'global_rank': stat.global_rank,
                'top_skills': top_badges_by_user.get(stat.user_id, [])
            })
            
        return Response(results)

class SendInviteView(APIView):
    permission_classes = [IsRecruiter]

    def post(self, request):
        candidate_id = request.data.get('candidate_id')
        job_listing_id = request.data.get('job_listing_id')
        message = request.data.get('message', '')
        
        candidate = get_object_or_404(User, id=candidate_id, role='candidate')
        job_listing = None
        if job_listing_id:
            job_listing = get_object_or_404(JobListing, id=job_listing_id, recruiter=request.user)
            
        invite, created = DirectInvite.objects.get_or_create(
            recruiter=request.user,
            candidate=candidate,
            job_listing=job_listing,
            defaults={'message': message}
        )
        
        return Response(DirectInviteSerializer(invite).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class MyInvitesView(generics.ListAPIView):
    serializer_class = DirectInviteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'recruiter':
            return DirectInvite.objects.filter(recruiter=user).order_by('-created_at')
        return DirectInvite.objects.filter(candidate=user).order_by('-created_at')


class ProposeInterviewView(APIView):
    permission_classes = [IsRecruiter]

    def post(self, request):
        candidate_id = request.data.get('candidate_id')
        job_listing_id = request.data.get('job_listing_id')
        proposed_time = request.data.get('proposed_time')
        message = request.data.get('message', '')
        
        candidate = get_object_or_404(User, id=candidate_id, role='candidate')
        job_listing = None
        if job_listing_id:
            job_listing = get_object_or_404(JobListing, id=job_listing_id, recruiter=request.user)
            
        interview = Interview.objects.create(
            recruiter=request.user,
            candidate=candidate,
            job_listing=job_listing,
            proposed_time=proposed_time,
            message=message,
            status='proposed'
        )
        
        return Response(InterviewSerializer(interview).data, status=status.HTTP_201_CREATED)

class MyInterviewsView(generics.ListAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'recruiter':
            return Interview.objects.filter(recruiter=user).order_by('proposed_time')
        return Interview.objects.filter(candidate=user).order_by('proposed_time')

class RespondInterviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        interview = get_object_or_404(Interview, pk=pk, candidate=request.user)
        new_status = request.data.get('status')
        if new_status not in ['accepted', 'declined']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
            
        interview.status = new_status
        interview.save()
        
        return Response(InterviewSerializer(interview).data, status=status.HTTP_200_OK)

class AIGenerateJobDescriptionView(APIView):
    permission_classes = [IsRecruiter]

    def post(self, request):
        role_title = request.data.get('role_title')
        company_name = request.data.get('company_name', '')
        
        if not role_title:
            return Response({'error': 'Role title is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from groq import Groq
            from django.conf import settings
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            prompt = f"Write a professional and engaging job description for the role of '{role_title}' at '{company_name}'. Include responsibilities and requirements. Keep it under 200 words."
            
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300,
            )
            
            description = completion.choices[0].message.content.strip()
            return Response({'description': description})
        except Exception as e:
            return Response({'error': str(e), 'description': f"We are looking for a skilled {role_title} to join {company_name}. You will be responsible for building high-quality products and collaborating with our team."})

class AIGenerateInterviewPrepView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        role_title = request.data.get('role_title', 'this role')
        description = request.data.get('description', '')
        
        try:
            from groq import Groq
            from django.conf import settings
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            prompt = f"Based on the following job description for '{role_title}', generate 3 key interview questions the candidate should prepare for, and provide a brief tip for answering each. Keep it encouraging and concise.\n\nDescription:\n{description[:1000]}"
            
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400,
            )
            
            prep_guide = completion.choices[0].message.content.strip()
            return Response({'prep_guide': prep_guide})
        except Exception as e:
            return Response({
                'prep_guide': f"1. Tell me about a time you overcame a technical challenge related to {role_title}.\n2. Why are you interested in this role?\n3. How do you keep your skills updated?"
            })
