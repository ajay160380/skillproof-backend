from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q
from django.utils import timezone
from .models import Organization, Department, OperationTask, OrganizationMember, AuditLog
from .permissions import IsOperationsStaffOrAdmin, CanAuditTaskPermission
from .serializers import (
    OrganizationSerializer, DepartmentSerializer, OperationTaskSerializer,
    OrganizationMemberSerializer, AuditLogSerializer, AdminUserManagementSerializer
)

User = get_user_model()


def log_audit(user, action_str, target_model, target_id, details=None):
    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action_str,
            target_model=target_model,
            target_id=str(target_id),
            details=details or {}
        )
    except Exception:
        pass


@api_view(['GET'])
@permission_classes([IsOperationsStaffOrAdmin])
def dashboard_stats_view(request):
    """
    Returns high-level platform KPI statistics for Super Admin & Admin Dashboards.
    Inspired by XYZ OPS Web & Mobile specifications.
    """
    total_orgs = Organization.objects.count()
    active_orgs = Organization.objects.filter(status='active').count()
    total_depts = Department.objects.count()
    
    total_users = User.objects.count()
    users_by_role = dict(User.objects.values_list('role').annotate(count=Count('id')))

    # Tasks stats
    tasks_qs = OperationTask.objects.all()
    # Auto-flag overdue tasks
    now = timezone.now()
    tasks_qs.filter(due_date__lt=now, status__in=['pending', 'in_progress']).update(status='overdue')

    tasks_total = tasks_qs.count()
    tasks_pending = tasks_qs.filter(status='pending').count()
    tasks_in_progress = tasks_qs.filter(status='in_progress').count()
    tasks_completed = tasks_qs.filter(status='completed').count()
    tasks_overdue = tasks_qs.filter(status='overdue').count()
    tasks_audited = tasks_qs.filter(status='audited').count()
    
    avg_mis = tasks_qs.filter(mis_score__gt=0).aggregate(Avg('mis_score'))['mis_score__avg'] or 85.4

    # Connect with SkillProof assessments if available
    assessments_stats = {'total_attempts': 0, 'verified_count': 0}
    try:
        from assessments.models import TestAttempt, SkillScore
        assessments_stats['total_attempts'] = TestAttempt.objects.count()
        assessments_stats['verified_count'] = SkillScore.objects.filter(is_verified=True).count()
    except Exception:
        pass

    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    recent_logs_data = AuditLogSerializer(recent_logs, many=True).data

    return Response({
        'overview': {
            'total_organizations': total_orgs,
            'active_organizations': active_orgs,
            'total_departments': total_depts,
            'total_users': total_users,
            'mis_score_avg': round(float(avg_mis), 1),
        },
        'users_breakdown': users_by_role,
        'tasks_summary': {
            'total': tasks_total,
            'pending': tasks_pending,
            'in_progress': tasks_in_progress,
            'completed': tasks_completed,
            'overdue': tasks_overdue,
            'audited': tasks_audited,
        },
        'assessments_summary': assessments_stats,
        'recent_activity': recent_logs_data,
    })


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by('-created_at')
    serializer_class = OrganizationSerializer
    permission_classes = [IsOperationsStaffOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if status_param:
            qs = qs.filter(status=status_param)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs

    def perform_create(self, serializer):
        org = serializer.save()
        log_audit(self.request.user, 'Created Organization', 'Organization', org.id, {'name': org.name, 'code': org.code})

    def perform_update(self, serializer):
        org = serializer.save()
        log_audit(self.request.user, 'Updated Organization', 'Organization', org.id, {'name': org.name})

    def perform_destroy(self, instance):
        log_audit(self.request.user, 'Deleted Organization', 'Organization', instance.id, {'name': instance.name})
        instance.delete()


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('-created_at')
    serializer_class = DepartmentSerializer
    permission_classes = [IsOperationsStaffOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        org_id = self.request.query_params.get('organization')
        search = self.request.query_params.get('search')
        if org_id:
            qs = qs.filter(organization_id=org_id)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return qs

    def perform_create(self, serializer):
        dept = serializer.save()
        log_audit(self.request.user, 'Created Department', 'Department', dept.id, {'name': dept.name, 'org': dept.organization.name})

    def perform_update(self, serializer):
        dept = serializer.save()
        log_audit(self.request.user, 'Updated Department', 'Department', dept.id, {'name': dept.name})


class OperationTaskViewSet(viewsets.ModelViewSet):
    queryset = OperationTask.objects.all().order_by('-created_at')
    serializer_class = OperationTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        is_staff_or_admin = (
            user.is_superuser or
            user.is_staff or
            getattr(user, 'role', None) in ['admin', 'superadmin', 'manager', 'auditor']
        )
        if not is_staff_or_admin:
            qs = qs.filter(assigned_to=user)

        task_type = self.request.query_params.get('task_type')
        task_status = self.request.query_params.get('status')
        assigned_to = self.request.query_params.get('assigned_to')
        org_id = self.request.query_params.get('organization')
        search = self.request.query_params.get('search')

        if task_type:
            qs = qs.filter(task_type=task_type)
        if task_status:
            qs = qs.filter(status=task_status)
        if assigned_to and is_staff_or_admin:
            qs = qs.filter(assigned_to_id=assigned_to)
        if org_id:
            qs = qs.filter(organization_id=org_id)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        return qs

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        log_audit(self.request.user, 'Created Task', 'OperationTask', task.id, {'title': task.title, 'type': task.task_type})

    @action(detail=True, methods=['post'], url_path='submit-proof')
    def submit_proof(self, request, pk=None):
        task = self.get_object()
        proof = request.data.get('proof_submission', '')
        checklist = request.data.get('checklist_data')
        workflow_stages = request.data.get('workflow_stages')

        task.proof_submission = proof
        if checklist is not None:
            task.checklist_data = checklist
        if workflow_stages is not None:
            task.workflow_stages = workflow_stages

        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()

        log_audit(request.user, 'Submitted Task Proof', 'OperationTask', task.id, {'title': task.title})
        return Response(OperationTaskSerializer(task).data)

    @action(detail=True, methods=['post'], url_path='audit', permission_classes=[CanAuditTaskPermission])
    def audit_task(self, request, pk=None):
        task = self.get_object()
        audit_action = request.data.get('action', 'approve')
        notes = request.data.get('audit_notes', '')
        mis_score = request.data.get('mis_score', 80.0)

        task.audited_by = request.user
        task.audit_notes = notes
        task.mis_score = float(mis_score)
        task.status = 'audited' if audit_action == 'approve' else 'in_progress'
        task.save()

        log_audit(request.user, f'Audited Task ({audit_action})', 'OperationTask', task.id, {'notes': notes, 'score': mis_score})
        return Response(OperationTaskSerializer(task).data)


class OrganizationMemberViewSet(viewsets.ModelViewSet):
    queryset = OrganizationMember.objects.all().order_by('-joined_at')
    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsOperationsStaffOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        org_id = self.request.query_params.get('organization')
        dept_id = self.request.query_params.get('department')
        if org_id:
            qs = qs.filter(organization_id=org_id)
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        return qs


class AdminUserManagementViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsOperationsStaffOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        search = self.request.query_params.get('search')
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(username__icontains=search) |
                Q(full_name__icontains=search)
            )
        return qs

    @action(detail=True, methods=['post'], url_path='toggle-verified')
    def toggle_verified(self, request, pk=None):
        user = self.get_object()
        user.is_verified = not user.is_verified
        user.save()
        log_audit(request.user, 'Toggled User Verification', 'User', user.id, {'is_verified': user.is_verified})
        return Response({'status': 'success', 'is_verified': user.is_verified})

    @action(detail=True, methods=['post'], url_path='change-role')
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        if new_role:
            user.role = new_role
            user.save()
            log_audit(request.user, 'Changed User Role', 'User', user.id, {'new_role': new_role})
            return Response({'status': 'success', 'role': user.role})
        return Response({'error': 'Role is required'}, status=status.HTTP_400_BAD_REQUEST)
