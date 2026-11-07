from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from badges.serializers import PublicBadgeSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'full_name', 'role', 'avatar_url', 'cover_image', 'bio', 'headline', 'location', 'company_name', 'github_url', 'linkedin_url', 'website_url', 'is_verified', 'created_at')
        read_only_fields = ('id', 'role', 'email', 'is_verified', 'is_staff', 'is_superuser', 'created_at')

class PublicUserSerializer(serializers.ModelSerializer):
    public_badges = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'full_name', 'headline', 'bio', 'location',
            'avatar_url', 'cover_image', 'company_name', 'role',
            'github_url', 'linkedin_url', 'website_url', 'is_verified',
            'created_at', 'public_badges'
        )
        read_only_fields = fields

    def get_public_badges(self, obj):
        from badges.models import Badge
        badges = Badge.objects.filter(user=obj).select_related('skill_category', 'score')
        return PublicBadgeSerializer(badges, many=True).data

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, min_length=3, max_length=150)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    full_name = serializers.CharField(required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=['candidate', 'recruiter'], default='candidate', required=False)

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return normalized_email

    def validate_username(self, value):
        import re
        if not re.match(r'^[\w]+$', value):
            raise serializers.ValidationError('Username can only contain letters, numbers, and underscores.')
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'full_name', 'role', 'company_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'].lower().strip(),
            password=validated_data['password'],
            full_name=validated_data.get('full_name', ''),
            role=validated_data.get('role', 'candidate'),
            company_name=validated_data.get('company_name', '')
        )
        return user
