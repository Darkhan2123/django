from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow read access to all authenticated users, but only admin can write.
    """

    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True

        # Write permissions only for admin and staff
        return request.user.is_staff


class IsTraderOrAdminForTrading(permissions.BasePermission):
    """
    Allow traders and admins to manage tradeable products.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Admins can do anything
        if request.user.is_staff:
            return True

        # Traders can access tradeable products
        return request.user.role == 'trader'

    def has_object_permission(self, request, view, obj):
        # Admins can access any product
        if request.user.is_staff:
            return True

        # Traders can only access tradeable products
        if request.user.role == 'trader':
            return obj.is_tradeable

        return False


class IsSalesOrAdminForInventory(permissions.BasePermission):
    """
    Allow sales representatives and admins to manage inventory.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Admins can do anything
        if request.user.is_staff:
            return True

        # Sales reps can access inventory
        return request.user.role == 'sales'
