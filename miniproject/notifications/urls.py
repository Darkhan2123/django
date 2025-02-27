from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceView

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Notification preferences endpoint (current user only)
    path('notifications/preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    # Include the viewset routes (list, detail, actions)
    path('', include(router.urls)),
]
