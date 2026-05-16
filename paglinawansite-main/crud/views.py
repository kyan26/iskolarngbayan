from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
import re
import os
from datetime import date, datetime
from .models import Roles, Users, Scholarships, ScholarProfiles, Applications, Documents

# ─── DASHBOARD ─────────────────────────────────────────────
def dashboard(request):
    try:
        total_scholars = ScholarProfiles.objects.count()
        total_scholarships = Scholarships.objects.count()
        total_applications = Applications.objects.count()
        pending = Applications.objects.filter(status='pending').count()
        approved = Applications.objects.filter(status='approved').count()
        rejected = Applications.objects.filter(status='rejected').count()
        data = {
            'total_scholars': total_scholars,
            'total_scholarships': total_scholarships,
            'total_applications': total_applications,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
        }
        return render(request, 'dashboard/Dashboard.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load dashboard: {e}')


# ─── ROLES ─────────────────────────────────────────────────
def role_list(request):
    try:
        roles = Roles.objects.all()
        data = {'roles': roles}
        return render(request, 'role/RoleList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load roles: {e}')

def role_add(request):
    try:
        if request.method == 'POST':
            role = request.POST.get('role', '').strip().title()
            if not role:
                messages.error(request, 'Role is required.')
                return render(request, 'role/RoleAdd.html')
            if Roles.objects.filter(role__iexact=role).exists():
                messages.error(request, 'Role already exists.')
                return render(request, 'role/RoleAdd.html')
            Roles.objects.create(role=role)
            messages.success(request, 'Role added successfully!')
            return redirect('/role/list')
        return render(request, 'role/RoleAdd.html')
    except Exception as e:
        return HttpResponse(f'Error occurred during add role: {e}')

def role_edit(request, role_id):
    try:
        roleObj = Roles.objects.get(pk=role_id)
        if request.method == 'POST':
            role = request.POST.get('role', '').strip().title()
            if not role:
                messages.error(request, 'Role is required.')
                return render(request, 'role/RoleEdit.html', {'role': roleObj})
            if Roles.objects.filter(role__iexact=role).exclude(pk=role_id).exists():
                messages.error(request, 'Role already exists.')
                return render(request, 'role/RoleEdit.html', {'role': roleObj})
            roleObj.role = role
            roleObj.save()
            messages.success(request, 'Role updated successfully!')
            return render(request, 'role/RoleEdit.html', {'role': roleObj})
        return render(request, 'role/RoleEdit.html', {'role': roleObj})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit role: {e}')

def role_delete(request, role_id):
    try:
        roleObj = Roles.objects.get(pk=role_id)
        if request.method == 'POST':
            roleObj.delete()
            messages.success(request, 'Role deleted successfully!')
            return redirect('/role/list')
        return render(request, 'role/RoleDelete.html', {'role': roleObj})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete role: {e}')


# ─── USERS ─────────────────────────────────────────────────
def user_list(request):
    try:
        search = request.GET.get('search')
        userObj = Users.objects.select_related('role').order_by('-user_id')
        if search:
            userObj = userObj.filter(
                Q(full_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(role__role__icontains=search)
            )
        paginator = Paginator(userObj, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        data = {'users': page_obj, 'search': search, 'page_obj': page_obj}
        return render(request, 'user/UserList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load users: {e}')

def user_add(request):
    try:
        if request.method == 'POST':
            fullName = request.POST.get('full_name', '').strip().title()
            role = request.POST.get('role', '').strip()
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            confirmPassword = request.POST.get('confirm_password', '')
            profilePicture = request.FILES.get('profile_picture')

            errors = []

            if not fullName:
                errors.append('Full name is required.')
            elif len(fullName) < 2:
                errors.append('Full name must be at least 2 characters.')
            elif re.search(r'[^a-zA-Z\s]', fullName):
                errors.append('Full name must contain letters only.')

            if not role:
                errors.append('Please select a role.')
            elif not Roles.objects.filter(pk=role).exists():
                errors.append('Selected role is invalid.')

            if not email:
                errors.append('Email is required.')
            elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                errors.append('Please enter a valid email address.')
            elif Users.objects.filter(email__iexact=email).exists():
                errors.append('Email already exists.')

            if not username:
                errors.append('Username is required.')
            elif re.search(r'\s', username):
                errors.append('Username cannot contain spaces.')
            elif Users.objects.filter(username__iexact=username).exists():
                errors.append('Username already exists.')

            if not password:
                errors.append('Password is required.')
            elif len(password) < 3:
                errors.append('Password must be at least 3 characters.')

            if password != confirmPassword:
                errors.append('Passwords do not match.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'user/UserAdd.html', {
                    'roles': Roles.objects.all(),
                    'form_data': {
                        'full_name': fullName,
                        'email': email,
                        'username': username,
                        'role': role,
                    }
                })

            Users.objects.create(
                full_name=fullName,
                role=Roles.objects.get(pk=role),
                email=email,
                username=username,
                password=make_password(password),
                profile_picture=profilePicture
            )
            messages.success(request, 'User added successfully!')
            return redirect('/user/add')
        return render(request, 'user/UserAdd.html', {'roles': Roles.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during add user: {e}')

def user_edit(request, user_id):
    try:
        user = Users.objects.get(user_id=user_id)
        if request.method == 'POST':
            fullName = request.POST.get('full_name', '').strip().title()
            role = request.POST.get('role', '').strip()
            email = request.POST.get('email', '').strip()
            username = request.POST.get('username', '').strip()

            errors = []

            if not fullName:
                errors.append('Full name is required.')
            elif len(fullName) < 2:
                errors.append('Full name must be at least 2 characters.')
            elif re.search(r'[^a-zA-Z\s]', fullName):
                errors.append('Full name must contain letters only.')

            if not role:
                errors.append('Please select a role.')
            elif not Roles.objects.filter(pk=role).exists():
                errors.append('Selected role is invalid.')

            if not email:
                errors.append('Email is required.')
            elif not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                errors.append('Please enter a valid email address.')
            elif Users.objects.filter(email__iexact=email).exclude(user_id=user_id).exists():
                errors.append('Email already exists.')

            if not username:
                errors.append('Username is required.')
            elif re.search(r'\s', username):
                errors.append('Username cannot contain spaces.')
            elif Users.objects.filter(username__iexact=username).exclude(user_id=user_id).exists():
                errors.append('Username already exists.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'user/UserEdit.html', {
                    'user': user,
                    'roles': Roles.objects.all()
                })

            user.full_name = fullName
            user.role_id = role
            user.email = email
            user.username = username

            if request.FILES.get('profile_picture'):
                if user.profile_picture:
                    if os.path.isfile(user.profile_picture.path):
                        os.remove(user.profile_picture.path)
                user.profile_picture = request.FILES.get('profile_picture')

            user.save()
            messages.success(request, 'User updated successfully!')
            return redirect('/user/list')
        return render(request, 'user/UserEdit.html', {'user': user, 'roles': Roles.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit user: {e}')

def user_delete(request, user_id):
    try:
        user = Users.objects.get(user_id=user_id)
        if request.method == 'POST':
            user.delete()
            messages.success(request, 'User deleted successfully!')
            return redirect('/user/list')
        return render(request, 'user/UserDelete.html', {'user': user})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete user: {e}')


# ─── SCHOLARSHIPS ───────────────────────────────────────────
def scholarship_list(request):
    try:
        search = request.GET.get('search')
        scholarships = Scholarships.objects.order_by('-scholarship_id')
        if search:
            scholarships = scholarships.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(eligibility__icontains=search)
            )
        paginator = Paginator(scholarships, 10)
        page_obj = paginator.get_page(request.GET.get('page', 1))
        data = {'scholarships': page_obj, 'search': search, 'page_obj': page_obj}
        return render(request, 'scholarship/ScholarshipList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load scholarships: {e}')

def scholarship_add(request):
    try:
        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            amount = request.POST.get('amount', '').strip()
            slots = request.POST.get('slots', '').strip()
            eligibility = request.POST.get('eligibility', '').strip()
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()

            errors = []

            if not name:
                errors.append('Scholarship name is required.')
            elif Scholarships.objects.filter(name__iexact=name).exists():
                errors.append('Scholarship name already exists.')
            if not description:
                errors.append('Description is required.')
            if not amount:
                errors.append('Amount is required.')
            if not slots:
                errors.append('Slots is required.')
            if not eligibility:
                errors.append('Eligibility is required.')
            if not start_date:
                errors.append('Start date is required.')
            if not end_date:
                errors.append('End date is required.')
            if start_date and end_date and start_date >= end_date:
                errors.append('End date must be after start date.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'scholarship/ScholarshipAdd.html')

            Scholarships.objects.create(
                name=name,
                description=description,
                amount=amount,
                slots=slots,
                eligibility=eligibility,
                start_date=start_date,
                end_date=end_date
            )
            messages.success(request, 'Scholarship added successfully!')
            return redirect('/scholarship/list')
        return render(request, 'scholarship/ScholarshipAdd.html')
    except Exception as e:
        return HttpResponse(f'Error occurred during add scholarship: {e}')

def scholarship_edit(request, scholarship_id):
    try:
        scholarship = Scholarships.objects.get(pk=scholarship_id)
        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            amount = request.POST.get('amount', '').strip()
            slots = request.POST.get('slots', '').strip()
            eligibility = request.POST.get('eligibility', '').strip()
            start_date = request.POST.get('start_date', '').strip()
            end_date = request.POST.get('end_date', '').strip()

            errors = []

            if not name:
                errors.append('Scholarship name is required.')
            elif Scholarships.objects.filter(name__iexact=name).exclude(pk=scholarship_id).exists():
                errors.append('Scholarship name already exists.')
            if not description:
                errors.append('Description is required.')
            if not amount:
                errors.append('Amount is required.')
            if not slots:
                errors.append('Slots is required.')
            if not eligibility:
                errors.append('Eligibility is required.')
            if not start_date:
                errors.append('Start date is required.')
            if not end_date:
                errors.append('End date is required.')
            if start_date and end_date and start_date >= end_date:
                errors.append('End date must be after start date.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'scholarship/ScholarshipEdit.html', {'scholarship': scholarship})

            scholarship.name = name
            scholarship.description = description
            scholarship.amount = amount
            scholarship.slots = slots
            scholarship.eligibility = eligibility
            scholarship.start_date = start_date
            scholarship.end_date = end_date
            scholarship.save()
            messages.success(request, 'Scholarship updated successfully!')
            return redirect('/scholarship/list')
        return render(request, 'scholarship/ScholarshipEdit.html', {'scholarship': scholarship})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit scholarship: {e}')

def scholarship_delete(request, scholarship_id):
    try:
        scholarship = Scholarships.objects.get(pk=scholarship_id)
        if request.method == 'POST':
            scholarship.delete()
            messages.success(request, 'Scholarship deleted successfully!')
            return redirect('/scholarship/list')
        return render(request, 'scholarship/ScholarshipDelete.html', {'scholarship': scholarship})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete scholarship: {e}')


# ─── SCHOLAR PROFILES ───────────────────────────────────────
def scholar_list(request):
    try:
        search = request.GET.get('search')
        scholars = ScholarProfiles.objects.select_related('user').order_by('-scholar_id')
        if search:
            scholars = scholars.filter(
                Q(full_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(address__icontains=search) |
                Q(school__icontains=search) |
                Q(course__icontains=search)
            )
        paginator = Paginator(scholars, 10)
        page_obj = paginator.get_page(request.GET.get('page', 1))
        data = {'scholars': page_obj, 'search': search, 'page_obj': page_obj}
        return render(request, 'scholar/ScholarList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load scholars: {e}')

def scholar_add(request):
    try:
        if request.method == 'POST':
            fullName = request.POST.get('full_name', '').strip().title()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip().title()
            school = request.POST.get('school', '').strip().title()
            course = request.POST.get('course', '').strip().title()
            yearLevel = request.POST.get('year_level', '').strip()
            gpa = request.POST.get('gpa', '').strip()
            user_id = request.POST.get('user', '').strip()
            photo = request.FILES.get('photo')

            errors = []

            if not fullName:
                errors.append('Full name is required.')
            if not phone:
                errors.append('Phone number is required.')
            elif not re.fullmatch(r'\d+', phone):
                errors.append('Phone must contain numbers only.')
            elif not (phone.startswith('09') or phone.startswith('63')):
                errors.append('Phone must start with 09 or 63.')
            if not address:
                errors.append('Address is required.')
            if not school:
                errors.append('School is required.')
            if not course:
                errors.append('Course is required.')
            if not yearLevel:
                errors.append('Year level is required.')
            if not gpa:
                errors.append('GPA is required.')
            if not user_id:
                errors.append('User is required.')
            elif ScholarProfiles.objects.filter(user_id=user_id).exists():
                errors.append('This user already has a scholar profile.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'scholar/ScholarAdd.html', {'users': Users.objects.all()})

            ScholarProfiles.objects.create(
                user=Users.objects.get(pk=user_id),
                full_name=fullName,
                phone=phone,
                address=address,
                school=school,
                course=course,
                year_level=yearLevel,
                gpa=gpa,
                photo=photo
            )
            messages.success(request, 'Scholar added successfully!')
            return redirect('/scholar/list')
        return render(request, 'scholar/ScholarAdd.html', {'users': Users.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during add scholar: {e}')

def scholar_edit(request, scholar_id):
    try:
        scholar = ScholarProfiles.objects.get(pk=scholar_id)
        if request.method == 'POST':
            fullName = request.POST.get('full_name', '').strip().title()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip().title()
            school = request.POST.get('school', '').strip().title()
            course = request.POST.get('course', '').strip().title()
            yearLevel = request.POST.get('year_level', '').strip()
            gpa = request.POST.get('gpa', '').strip()

            errors = []

            if not fullName:
                errors.append('Full name is required.')
            if not phone:
                errors.append('Phone number is required.')
            elif not re.fullmatch(r'\d+', phone):
                errors.append('Phone must contain numbers only.')
            elif not (phone.startswith('09') or phone.startswith('63')):
                errors.append('Phone must start with 09 or 63.')
            if not address:
                errors.append('Address is required.')
            if not school:
                errors.append('School is required.')
            if not course:
                errors.append('Course is required.')
            if not yearLevel:
                errors.append('Year level is required.')
            if not gpa:
                errors.append('GPA is required.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'scholar/ScholarEdit.html', {'scholar': scholar})

            scholar.full_name = fullName
            scholar.phone = phone
            scholar.address = address
            scholar.school = school
            scholar.course = course
            scholar.year_level = yearLevel
            scholar.gpa = gpa

            if request.FILES.get('photo'):
                if scholar.photo:
                    if os.path.isfile(scholar.photo.path):
                        os.remove(scholar.photo.path)
                scholar.photo = request.FILES.get('photo')

            scholar.save()
            messages.success(request, 'Scholar updated successfully!')
            return redirect('/scholar/list')
        return render(request, 'scholar/ScholarEdit.html', {'scholar': scholar})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit scholar: {e}')

def scholar_delete(request, scholar_id):
    try:
        scholar = ScholarProfiles.objects.get(pk=scholar_id)
        if request.method == 'POST':
            scholar.delete()
            messages.success(request, 'Scholar deleted successfully!')
            return redirect('/scholar/list')
        return render(request, 'scholar/ScholarDelete.html', {'scholar': scholar})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete scholar: {e}')


# ─── APPLICATIONS ───────────────────────────────────────────
def application_list(request):
    try:
        search = request.GET.get('search')
        applications = Applications.objects.select_related('scholar', 'scholarship').order_by('-application_id')
        if search:
            applications = applications.filter(
                Q(scholar__full_name__icontains=search) |
                Q(scholarship__name__icontains=search) |
                Q(status__icontains=search)
            )
        paginator = Paginator(applications, 10)
        page_obj = paginator.get_page(request.GET.get('page', 1))
        data = {'applications': page_obj, 'search': search, 'page_obj': page_obj}
        return render(request, 'application/ApplicationList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load applications: {e}')

def application_add(request):
    try:
        if request.method == 'POST':
            scholar_id = request.POST.get('scholar', '').strip()
            scholarship_id = request.POST.get('scholarship', '').strip()
            remarks = request.POST.get('remarks', '').strip()

            errors = []

            if not scholar_id:
                errors.append('Scholar is required.')
            if not scholarship_id:
                errors.append('Scholarship is required.')
            elif Applications.objects.filter(scholar_id=scholar_id, scholarship_id=scholarship_id).exists():
                errors.append('This scholar already applied for this scholarship.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'application/ApplicationAdd.html', {
                    'scholars': ScholarProfiles.objects.all(),
                    'scholarships': Scholarships.objects.all()
                })

            Applications.objects.create(
                scholar=ScholarProfiles.objects.get(pk=scholar_id),
                scholarship=Scholarships.objects.get(pk=scholarship_id),
                remarks=remarks
            )
            messages.success(request, 'Application submitted successfully!')
            return redirect('/application/list')
        return render(request, 'application/ApplicationAdd.html', {
            'scholars': ScholarProfiles.objects.all(),
            'scholarships': Scholarships.objects.all()
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during add application: {e}')

def application_edit(request, application_id):
    try:
        application = Applications.objects.get(pk=application_id)
        if request.method == 'POST':
            status = request.POST.get('status', '').strip()
            remarks = request.POST.get('remarks', '').strip()

            if not status:
                messages.error(request, 'Status is required.')
                return render(request, 'application/ApplicationEdit.html', {'application': application})

            application.status = status
            application.remarks = remarks
            application.save()
            messages.success(request, 'Application updated successfully!')
            return redirect('/application/list')
        return render(request, 'application/ApplicationEdit.html', {'application': application})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit application: {e}')

def application_delete(request, application_id):
    try:
        application = Applications.objects.get(pk=application_id)
        if request.method == 'POST':
            application.delete()
            messages.success(request, 'Application deleted successfully!')
            return redirect('/application/list')
        return render(request, 'application/ApplicationDelete.html', {'application': application})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete application: {e}')


# ─── DOCUMENTS ──────────────────────────────────────────────
def document_list(request, application_id):
    try:
        application = Applications.objects.get(pk=application_id)
        documents = Documents.objects.filter(application=application)
        data = {'documents': documents, 'application': application}
        return render(request, 'document/DocumentList.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load documents: {e}')

def document_add(request, application_id):
    try:
        application = Applications.objects.get(pk=application_id)
        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            file = request.FILES.get('file')

            errors = []
            if not name:
                errors.append('Document name is required.')
            if not file:
                errors.append('File is required.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'document/DocumentAdd.html', {'application': application})

            Documents.objects.create(application=application, name=name, file=file)
            messages.success(request, 'Document uploaded successfully!')
            return redirect(f'/application/{application_id}/documents')
        return render(request, 'document/DocumentAdd.html', {'application': application})
    except Exception as e:
        return HttpResponse(f'Error occurred during add document: {e}')

def document_delete(request, document_id):
    try:
        document = Documents.objects.get(pk=document_id)
        application_id = document.application.application_id
        if request.method == 'POST':
            if document.file:
                if os.path.isfile(document.file.path):
                    os.remove(document.file.path)
            document.delete()
            messages.success(request, 'Document deleted successfully!')
            return redirect(f'/application/{application_id}/documents')
        return render(request, 'document/DocumentDelete.html', {'document': document})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete document: {e}')


# ─── AUTH ───────────────────────────────────────────────────
def login_view(request):
    try:
        if request.session.get('user_id'):
            return redirect('/profile')

        if request.method == 'POST':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')

            errors = []

            if not username:
                errors.append('Username is required.')
            if not password:
                errors.append('Password is required.')

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'auth/Login.html', {'form_data': {'username': username}})

            try:
                user = Users.objects.get(username__iexact=username)
                if check_password(password, user.password):
                    request.session['user_id'] = user.user_id
                    request.session['user_name'] = user.full_name
                    request.session['user_role'] = user.role.role
                    request.session['user_pic'] = user.profile_picture.url if user.profile_picture else None
                    messages.success(request, f'Welcome back, {user.full_name}!')
                    return redirect('/profile')
                else:
                    messages.error(request, 'Invalid username or password.')
                    return render(request, 'auth/Login.html', {'form_data': {'username': username}})
            except Users.DoesNotExist:
                messages.error(request, 'Invalid username or password.')
                return render(request, 'auth/Login.html', {'form_data': {'username': username}})

        return render(request, 'auth/Login.html')
    except Exception as e:
        return HttpResponse(f'Error occurred during login: {e}')

def logout_view(request):
    request.session.flush()
    messages.success(request, 'Logged out successfully!')
    return redirect('/login')

def profile_view(request):
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login')

        user = Users.objects.select_related('role').get(user_id=user_id)
        scholar = ScholarProfiles.objects.filter(user=user).first()
        applications = Applications.objects.filter(scholar=scholar).select_related('scholarship') if scholar else []

        data = {
            'user': user,
            'scholar': scholar,
            'applications': applications,
        }
        return render(request, 'auth/Profile.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during profile load: {e}')