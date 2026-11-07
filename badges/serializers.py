from rest_framework import serializers
from .models import Badge, UserStats
from skills.serializers import SkillCategorySerializer

class UserStatsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = UserStats
        fields = ['id', 'username', 'full_name', 'total_points', 'current_streak', 'highest_streak', 'global_rank', 'last_activity_date']

class BadgeSerializer(serializers.ModelSerializer):
    skill_category = SkillCategorySerializer(read_only=True)
    
    class Meta:
        model = Badge
        fields = '__all__'

class PublicBadgeSerializer(serializers.ModelSerializer):
    skill_category = SkillCategorySerializer(read_only=True)
    overall_score = serializers.IntegerField(source='score.overall_score', read_only=True, default=80)
    sub_scores = serializers.JSONField(source='score.sub_scores', read_only=True)
    ai_feedback_text = serializers.CharField(source='score.ai_feedback_text', read_only=True)
    cheating_flags = serializers.JSONField(source='score.cheating_flags', read_only=True)
    
    class Meta:
        model = Badge
        fields = ('id', 'skill_category', 'badge_level', 'overall_score', 'sub_scores', 'ai_feedback_text', 'cheating_flags', 'issued_at', 'certificate_pdf_url', 'verification_id')
