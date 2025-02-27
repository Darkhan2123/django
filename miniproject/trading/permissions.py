from rest_framework import permissions


class IsTraderOrAdmin(permissions.BasePermission):
    """
    Allow access only to traders or admin users.
    """
    def has_permission(self, request, view):
        # Allow if user is authenticated and is either a trader or admin
        return (
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_staff or
                getattr(request.user, 'role', None) == 'trader'
            )
        )


class IsOrderOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to allow owners of an order or admin
    to modify it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow admin users
        if request.user.is_staff:
            return True

        # Allow order owner
        return obj.user == request.user


class CanApproveOrders(permissions.BasePermission):
    """
    Allow only admin users or authorized approvers to approve orders.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_staff or
                getattr(request.user, 'role', None) == 'admin'
            )
        )


class ReadOnly(permissions.BasePermission):
    """
    Allow only read-only access.
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class CanViewTransactions(permissions.BasePermission):
    """
    Allow users to view transactions related to their orders.
    """
    def has_permission(self, request, view):
        # Admin can view all transactions
        if request.user.is_staff:
            return True

        # Only allow GET for non-admin users
        return request.method == 'GET'

    def has_object_permission(self, request, view, obj):
        # Admin can view all transactions
        if request.user.is_staff:
            return True

        # Users can view transactions related to their orders
        return obj.order.user == request.user or (obj.counter_order and obj.counter_order.user == request.user)
