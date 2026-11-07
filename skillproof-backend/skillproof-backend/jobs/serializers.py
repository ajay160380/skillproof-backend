from rest_framework import serializers
from .models import JobListing, JobApplication, CompanyRequirement
from skills.models import SkillTest
from skills.serializers import SkillTestSerializer

class JobListingSerializer(serializers.ModelSerializer):
    required_tests = SkillTestSerializer(many=True, read_only=True)
    required_test_ids = serializers.PrimaryKeyRelatedField(
        queryset=SkillTest.objects.all(), 
        source='required_tests', 
        many=True, 
        write_only=True
    )

    recruiter_id = serializers.IntegerField(source='recruiter.id', read_only=True)
    candidate_eligibility = serializers.SerializerMethodField()
    applicants_count = serializers.SerializerMethodField()

    class Meta:
        model = JobListing
        fields = [
            'id', 'recruiter_id', 'company_name', 'role_title', 'description', 
            'location', 'salary_range', 'min_score', 'required_tests', 'required_test_ids', 
            'is_active', 'created_at', 'application_deadline', 'candidate_eligibility', 'applicants_count'
        ]
        read_only_fields = ['id', 'created_at', 'candidate_eligibility', 'applicants_count']

    def get_applicants_count(self, obj):
        return obj.applications.count()

    def get_candidate_eligibility(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None

        user = request.user
        required_tests = list(obj.required_tests.all())
        min_required = getattr(obj, 'min_score', 70) or 70

        # Check existing application
        app = JobApplication.objects.filter(candidate=user, job_listing=obj).first()
        has_applied = app is not None

        if not required_tests:
            return {
                'is_eligible': True,
                'status': 'applied' if has_applied else 'eligible',
                'has_applied': has_applied,
                'candidate_score': None,
                'min_score': min_required,
                'completed_tests_count': 0,
                'total_required_tests': 0,
                'missing_tests': [],
                'completed_tests': []
            }

        from assessments.models import SkillScore
        req_test_ids = [t.id for t in required_tests]
        user_scores = SkillScore.objects.filter(
            attempt__user=user,
            attempt__status='completed',
            attempt__test_id__in=req_test_ids
        ).select_related('attempt__test').order_by('attempt__test_id', '-overall_score')

        best_scores = {}
        for s in user_scores:
            tid = s.attempt.test_id
            if tid not in best_scores or s.overall_score > best_scores[tid]:
                best_scores[tid] = s.overall_score

        missing = []
        completed = []
        total_score = 0

        for t in required_tests:
            if t.id in best_scores:
                score_val = best_scores[t.id]
                total_score += score_val
                completed.append({
                    'id': t.id,
                    'title': t.title,
                    'category': t.category.name if t.category else '',
                    'score': score_val,
                    'min_score': min_required,
                    'passed': score_val >= min_required
                })
            else:
                missing.append({
                    'id': t.id,
                    'title': t.title,
                    'category': t.category.name if t.category else '',
                    'duration_minutes': t.duration_minutes,
                    'test_type': t.test_type,
                    'min_score': min_required
                })

        is_all_completed = len(missing) == 0
        avg_score = int(total_score / len(required_tests)) if is_all_completed and required_tests else None
        all_passed = is_all_completed and all(c['passed'] for c in completed)

        if has_applied:
            status_val = 'applied'
        elif all_passed:
            status_val = 'eligible'
        elif is_all_completed and not all_passed:
            status_val = 'score_too_low'
        else:
            status_val = 'test_required'

        return {
            'is_eligible': all_passed,
            'status': status_val,
            'has_applied': has_applied,
            'candidate_score': avg_score,
            'min_score': min_required,
            'completed_tests_count': len(completed),
            'total_required_tests': len(required_tests),
            'missing_tests': missing,
            'completed_tests': completed
        }

class JobApplicationSerializer(serializers.ModelSerializer):
    job_listing = JobListingSerializer(read_only=True)
    job_listing_id = serializers.PrimaryKeyRelatedField(
        queryset=JobListing.objects.filter(is_active=True),
        source='job_listing',
        write_only=True
    )

    class Meta:
        model = JobApplication
        fields = ['id', 'job_listing', 'job_listing_id', 'status', 'overall_fit_score', 'started_at', 'completed_at']
        read_only_fields = ['id', 'status', 'overall_fit_score', 'started_at', 'completed_at']

class JobApplicantSerializer(serializers.ModelSerializer):
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_id = serializers.IntegerField(source='candidate.id', read_only=True)
    candidate_avatar = serializers.CharField(source='candidate.avatar_url', read_only=True, default='')
    
    # Optional: include badges if requested, or just rely on public badges API
    
    class Meta:
        model = JobApplication
        fields = ['id', 'candidate_id', 'candidate_name', 'candidate_email', 'candidate_avatar', 'status', 'overall_fit_score', 'completed_at']

from skills.models import SkillCategory
from skills.serializers import SkillCategorySerializer

class CompanyRequirementSerializer(serializers.ModelSerializer):
    required_skills = SkillCategorySerializer(many=True, read_only=True)
    required_skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=SkillCategory.objects.all(),
        source='required_skills',
        many=True,
        write_only=True
    )
    recruiter_name = serializers.CharField(source='recruiter.full_name', read_only=True)

    class Meta:
        model = CompanyRequirement
        fields = ['id', 'recruiter_name', 'company_name', 'company_description', 'required_skills', 'required_skill_ids', 'preferred_min_score', 'updated_at']
        read_only_fields = ['id', 'updated_at']

from .models import DirectInvite, Interview

class DirectInviteSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source='recruiter.full_name', read_only=True)
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    job_role = serializers.CharField(source='job_listing.role_title', read_only=True)

    class Meta:
        model = DirectInvite
        fields = ['id', 'recruiter', 'recruiter_name', 'candidate', 'candidate_name', 'job_listing', 'job_role', 'message', 'is_accepted', 'created_at']
        read_only_fields = ['id', 'is_accepted', 'created_at']

class InterviewSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source='recruiter.full_name', read_only=True)
    recruiter_company = serializers.CharField(source='recruiter.company_name', read_only=True)
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    job_role = serializers.CharField(source='job_listing.role_title', read_only=True)

    class Meta:
        model = Interview
        fields = ['id', 'recruiter', 'recruiter_name', 'recruiter_company', 'candidate', 'candidate_name', 'job_listing', 'job_role', 'proposed_time', 'status', 'message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
