from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserListView,
    UserCreateView,
    UserDetailView,
    PasswordChangeView,
    ProfileImageUpdateView,
    CurrentUserView
)
from .email_verification import ResendVerificationEmailView, VerifyEmailView

app_name = 'users'

urlpatterns = [
    # User CRUD operations
    path('', UserListView.as_view(), name='user_list'),
    path('register/', UserCreateView.as_view(), name='user_register'),
    path('<int:pk>/', UserDetailView.as_view(), name='user_detail'),

    # Authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User profile operations
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('profile-image/update/', ProfileImageUpdateView.as_view(), name='profile_image_update'),

    # Email verification
    path('email/verify/<uuid:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('email/resend/', ResendVerificationEmailView.as_view(), name='resend_verification'),
]
