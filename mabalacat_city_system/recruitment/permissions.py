"""Custom permission classes for recruitment workflows."""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsHRStaff(BasePermission):
    """Allow access to HR staff, HR head, or admins."""

    allowed_roles = {"HR_STAFF", "HR_HEAD", "ADMIN"}

    def has_permission(self, request, view) -> bool:
        """Check role-based access for authenticated users."""

        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) in self.allowed_roles)


class IsHRHeadOrAdmin(BasePermission):
    """Allow access to HR head or admin accounts only."""

    allowed_roles = {"HR_HEAD", "ADMIN"}

    def has_permission(self, request, view) -> bool:
        """Check elevated role-based access."""

        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) in self.allowed_roles)


class IsApplicant(BasePermission):
    """Allow read-only access to applicant users."""

    def has_permission(self, request, view) -> bool:
        """Restrict applicant-facing permission to safe requests."""

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "APPLICANT"
            and request.method in SAFE_METHODS
        )
