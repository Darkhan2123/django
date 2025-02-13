from django.shortcuts import render, redirect
from .forms import BasicContactForm, ContactForm, CVForm
from .models import CV
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib import messages

def basic_contact_view(request):
    if request.method == "POST":
        form = BasicContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            # Do something with the data (e.g., send an email)
            return render(request, 'success.html', {'name': name})
    else:
        form = BasicContactForm()
    return render(request, 'basic_contact.html', {'form': form})

def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # Saves to the database
            return redirect('success_page')
    else:
        form = ContactForm()
    return render(request, 'contacts.html', {'form': form})

def success_view(request):
    return render(request, 'success.html')

def create_cv(request):
    if request.method == "POST":
        form = CVForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('cv_list')
    else:
        form = CVForm()
    return render(request, 'cv_form.html', {'form': form})

def cv_list(request):
    cvs = CV.objects.all()
    return render(request, 'cv_list.html', {'cvs': cvs})

def share_cv_email(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id)

    if request.method == "POST":
        recipient_email = request.POST.get('email')
        if recipient_email:
            subject = f"{cv.name}'s CV"
            message = f"Check out {cv.name}'s CV at {request.build_absolute_uri(cv.profile_picture.url)}"
            sender_email = settings.EMAIL_HOST_USER

            send_mail(subject, message, sender_email, [recipient_email])
            messages.success(request, "CV shared successfully via email.")
        else:
            messages.error(request, "Please provide a valid email.")
        return redirect('cv_list')

    return redirect('cv_list')

def cv_detail(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id)
    return render(request, 'cv_detail.html', {'cv': cv})
