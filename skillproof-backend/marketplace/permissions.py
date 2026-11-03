from rest_framework.permissions import BasePermission

class IsRecruiter(BasePermission):
    """
    Allows access to recruiters, admins, superadmins, and staff.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return bool(
            request.user.role in ['recruiter', 'admin', 'superadmin', 'manager'] or
            request.user.is_staff or
            request.user.is_superuser
        )
