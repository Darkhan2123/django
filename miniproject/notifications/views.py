from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user notifications.
    Users can list their notifications and mark them read. Admins can create notifications.
    """
    queryset = Notification.objects.none()  # Queryset is defined per request in get_queryset
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # Only return notifications for the authenticated user
        return Notification.objects.filter(user=self.request.user)

    def get_permissions(self):
        # Only admins can create new notifications via the API
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Custom action to mark a single notification as read."""
        notification = self.get_object()
        if notification.user != request.user:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        notification.read = True
        notification.save()
        return Response({"detail": "Notification marked as read."})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Custom action to mark all notifications of the current user as read."""
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({"detail": "All notifications marked as read."})

class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    API view to retrieve or update the authenticated user's notification preferences.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Get or create the NotificationPreference for the current user
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj
