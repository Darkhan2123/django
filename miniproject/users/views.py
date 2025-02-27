from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from rest_framework import generics, permissions, status, filters
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    ProfileImageSerializer
)

User = get_user_model()


class IsOwnerOrAdmin(BasePermission):
    """
    Custom permission to allow only the user or an admin to edit user data.
    """
    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff


class UserListView(generics.ListAPIView):
    """
    List all users (Admin only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined']


class UserCreateView(generics.CreateAPIView):
    """
    Register a new user
    """
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        # Save the new user
        user = serializer.save()

        # Send verification email
        from .email_verification import send_verification_email
        send_verification_email(user, self.request)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a user instance.
    """
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]


class PasswordChangeView(APIView):
    """
    Change password for authenticated user
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {"message": "Password updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageUpdateView(generics.UpdateAPIView):
    """
    Update user profile image
    """
    serializer_class = ProfileImageSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class CurrentUserView(APIView):
    """
    Retrieve the currently authenticated user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# Template-based Views
class UserDashboardView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/dashboard.html'
    context_object_name = 'user'

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['trading_orders'] = user.trading_orders.all()[:5]
        context['sales_orders'] = user.sales_orders.all()[:5]
        return context

class UserProfileView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'users/profile.html'
    fields = ['first_name', 'last_name', 'email', 'profile_image']
    success_url = reverse_lazy('users:dashboard')

    def get_object(self):
        return self.request.user

def register_view(request):
    if request.method == 'POST':
        serializer = UserCreateSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return redirect('users:dashboard')
        return render(request, 'users/register.html', {'errors': serializer.errors})
    return render(request, 'users/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('users:dashboard')
        return render(request, 'users/login.html', {'error': 'Invalid credentials'})
    return render(request, 'users/login.html')
