from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    dashboard_stats_view, OrganizationViewSet, DepartmentViewSet,
    OperationTaskViewSet, OrganizationMemberViewSet, AdminUserManagementViewSet
)

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='operation-organizations')
router.register(r'departments', DepartmentViewSet, basename='operation-departments')
router.register(r'tasks', OperationTaskViewSet, basename='operation-tasks')
router.register(r'members', OrganizationMemberViewSet, basename='operation-members')
router.register(r'users', AdminUserManagementViewSet, basename='operation-users')

urlpatterns = [
    path('dashboard/', dashboard_stats_view, name='operations-dashboard'),
    path('', include(router.urls)),
]
