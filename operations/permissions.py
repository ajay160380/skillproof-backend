from rest_framework import permissions

class IsOperationsStaffOrAdmin(permissions.BasePermission):
    """
    Custom permission to ensure only Admins, SuperAdmins, Managers,
    Auditors, or Django Staff can access operations/admin management APIs.
    """
    message = "Access Denied: You do not have administrator or operations staff privileges."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        allowed_roles = {'admin', 'superadmin', 'manager', 'auditor'}
        return getattr(user, 'role', None) in allowed_roles


class CanAuditTaskPermission(permissions.BasePermission):
    """
    Ensures only Auditors, Admins, or SuperAdmins can approve or audit tasks.
    """
    message = "Access Denied: Only designated Auditors or Administrators can evaluate and sign off tasks."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        return getattr(user, 'role', None) in {'auditor', 'admin', 'superadmin'}
