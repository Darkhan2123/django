from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
import uuid

from .models import EmailVerificationToken, User


def send_verification_email(user, request):
    """
    Create a verification token and send email to user
    """
    # Create or update verification token
    token, created = EmailVerificationToken.objects.update_or_create(
        user=user,
        defaults={'token': uuid.uuid4()}
    )

    # Construct verification URL
    verification_url = request.build_absolute_uri(
        reverse('users:verify_email', kwargs={'token': token.token})
    )

    # Email content
    subject = 'Verify your email address'
    message = render_to_string('users/email_verification.html', {
        'user': user,
        'verification_url': verification_url,
        'expiry_hours': 24,
    })

    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message,
    )


class ResendVerificationEmailView(APIView):
    """
    Resend verification email to the user
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        send_verification_email(user, request)

        return Response(
            {"detail": "Verification email sent."},
            status=status.HTTP_200_OK
        )


class VerifyEmailView(APIView):
    """
    Verify user email with token
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        # Find token
        token_obj = get_object_or_404(EmailVerificationToken, token=token)

        # Check if token is valid
        if not token_obj.is_valid():
            return Response(
                {"detail": "Verification link has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify user email
        user = token_obj.user
        user.email_verified = True
        user.save()

        # Delete token
        token_obj.delete()

        return Response(
            {"detail": "Email successfully verified."},
            status=status.HTTP_200_OK
        )
