# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect
# pyrefly: ignore [missing-import]
from django.contrib.auth import authenticate, login, logout
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from .models import UserProfile

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check profile suspension status
            profile = getattr(user, 'profile', None)
            if profile and profile.is_suspended:
                return render(request, 'login.html', {
                    'error_message': 'Your account has been suspended. Please contact administration/support.',
                    'username': username
                })
            
            login(request, user)
            if next_url:
                return redirect(next_url)
            return redirect('index')
        else:
            return render(request, 'login.html', {
                'error_message': 'Invalid username or password.',
                'username': username
            })
            
    return render(request, 'login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        print(request.POST)
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        full_name = request.POST.get('full_name', '').strip()
        

        # Validation checks
        if not username or not email or not password or not confirm_password:
            return render(request, 'register.html', {
                'error_message': 'All fields are required.',
                'username': username,
                'email': email,
                'full_name': full_name
            })
            
        if password != confirm_password:
            return render(request, 'register.html', {
                'error_message': 'Passwords do not match.',
                'username': username,
                'email': email,
                'full_name': full_name
            })
            
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {
                'error_message': 'Username is already taken.',
                'username': username,
                'email': email,
                'full_name': full_name
            })
            
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {
                'error_message': 'Email address is already in use.',
                'username': username,
                'email': email,
                'full_name': full_name
            })
            
        try:
            # Create user and let post_save signal handle profile creation
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Update the profile full_name if it was created
            if hasattr(user, 'profile'):
                user.profile.full_name = full_name
                user.profile.save()
                
            login(request, user)
            return redirect('index')
        except Exception as e:
            return render(request, 'register.html', {
                'error_message': f'An error occurred: {str(e)}',
                'username': username,
                'email': email,
                'full_name': full_name
            })
            
    return render(request, 'register.html')

def logout_view(request):
    logout(request)
    return redirect('index')