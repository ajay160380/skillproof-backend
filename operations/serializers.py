from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, Department, OperationTask, OrganizationMember, AuditLog

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'avatar_url', 'is_verified']


class DepartmentSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    manager_details = UserSummarySerializer(source='manager', read_only=True)
    members_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'organization', 'organization_name', 'name', 'code',
            'description', 'manager', 'manager_details', 'status',
            'members_count', 'tasks_count', 'created_at', 'updated_at'
        ]

    def get_members_count(self, obj):
        return obj.members.count()

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class OrganizationSerializer(serializers.ModelSerializer):
    departments_count = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'code', 'description', 'website', 'contact_email',
            'contact_phone', 'address', 'logo_url', 'status',
            'departments_count', 'members_count', 'tasks_count',
            'created_at', 'updated_at'
        ]

    def get_departments_count(self, obj):
        return obj.departments.count()

    def get_members_count(self, obj):
        return obj.memberships.count()

    def get_tasks_count(self, obj):
        return obj.tasks.count()


class OperationTaskSerializer(serializers.ModelSerializer):
    assigned_to_details = UserSummarySerializer(source='assigned_to', read_only=True)
    created_by_details = UserSummarySerializer(source='created_by', read_only=True)
    audited_by_details = UserSummarySerializer(source='audited_by', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = OperationTask
        fields = [
            'id', 'title', 'description', 'task_type', 'priority', 'status',
            'organization', 'organization_name', 'department', 'department_name',
            'assigned_to', 'assigned_to_details', 'created_by', 'created_by_details',
            'audited_by', 'audited_by_details', 'start_date', 'due_date',
            'completed_at', 'score', 'mis_score', 'checklist_data',
            'workflow_stages', 'additional_fields', 'proof_submission',
            'audit_notes', 'created_at', 'updated_at'
        ]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(source='user', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'organization_name', 'department',
            'department_name', 'user', 'user_details', 'role',
            'status', 'joined_at'
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(source='user', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_details', 'action', 'target_model', 'target_id', 'details', 'timestamp']


class AdminUserManagementSerializer(serializers.ModelSerializer):
    org_memberships = OrganizationMemberSerializer(many=True, read_only=True)
    assigned_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'role', 'headline',
            'location', 'company_name', 'avatar_url', 'is_verified',
            'is_active', 'is_staff', 'is_superuser', 'created_at',
            'org_memberships', 'assigned_tasks_count'
        ]

    def get_assigned_tasks_count(self, obj):
        return OperationTask.objects.filter(assigned_to=obj).count()
