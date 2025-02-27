from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from django.contrib.auth.views import LogoutView

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
    # Template-based URLs
    path('dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),

    # API URLs
    path('api/users/', views.UserListView.as_view(), name='user-list'),
    path('api/users/create/', views.UserCreateView.as_view(), name='user-create'),
    path('api/users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('api/users/me/', views.CurrentUserView.as_view(), name='current-user'),
    path('api/users/change-password/', views.PasswordChangeView.as_view(), name='change-password'),
    path('api/users/profile-image/', views.ProfileImageUpdateView.as_view(), name='profile-image-update'),

    # Authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Email verification
    path('email/verify/<uuid:token>/', VerifyEmailView.as_view(), name='verify_email'),
    path('email/resend/', ResendVerificationEmailView.as_view(), name='resend_verification'),
]
