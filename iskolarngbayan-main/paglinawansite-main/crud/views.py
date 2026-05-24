from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
import re
import os
from .models import Roles, Users, Scholarships, ScholarProfiles, Applications, Documents, Grades, Announcements
from datetime import date


# ─── HELPERS ────────────────────────────────────────────────

def get_session_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        return Users.objects.select_related('role').get(user_id=user_id)
    except Users.DoesNotExist:
        return None

def sync_user_pic(request, user):
    if user.profile_picture:
        request.session['user_pic'] = user.profile_picture.url
    else:
        request.session['user_pic'] = None

def admin_only(request):
    user = get_session_user(request)
    if not user:
        return redirect('/login')
    if user.role.role != 'Admin':
        messages.error(request, 'Access denied. Admins only.')
        return redirect('/profile')
    return None

def login_required(request):
    if not get_session_user(request):
        return redirect('/login')
    return None

def recalculate_gpa(scholar):
    grades = Grades.objects.filter(scholar=scholar)
    if grades.exists():
        total = sum(float(g.grade) for g in grades)
        new_gpa = round(total / grades.count(), 2)
    else:
        new_gpa = 0.00
    scholar.gpa = new_gpa
    scholar.save()

    # Auto-reject applications if GPA no longer meets requirement
    applications = Applications.objects.filter(
        scholar=scholar,
        status__in=['pending', 'under_review', 'approved']
    ).select_related('scholarship')

    for application in applications:
        if new_gpa > application.scholarship.gpa_requirement:
            application.status = 'rejected'
            application.remarks = f'Automatically rejected: Scholar GPA ({new_gpa}) no longer meets the required GPA ({application.scholarship.gpa_requirement}).'
            application.save()


# ─── AUTH ────────────────────────────────────────────────────

def login_view(request):
    try:
        if request.session.get('user_id'):
            user = get_session_user(request)
            if user:
                return redirect('/profile' if user.role.role == 'Scholar' else '/dashboard')

        if request.method == 'POST':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')

            errors = []
            if not username:
                errors.append('Username is required.')
            if not password:
                errors.append('Password is required.')
            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'auth/Login.html', {'form_data': {'username': username}})

            try:
                user = Users.objects.select_related('role').get(username__iexact=username)
                if check_password(password, user.password):
                    request.session['user_id']   = user.user_id
                    request.session['user_name'] = user.full_name
                    request.session['user_role'] = user.role.role
                    sync_user_pic(request, user)
                    messages.success(request, f'Welcome back, {user.full_name}!')
                    return redirect('/profile' if user.role.role == 'Scholar' else '/dashboard')
                else:
                    messages.error(request, 'Invalid username or password.')
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
        guard = login_required(request)
        if guard: return guard

        user = get_session_user(request)
        scholar = ScholarProfiles.objects.filter(user=user).first()
        applications = (
            Applications.objects.filter(scholar=scholar).select_related('scholarship')
            if scholar else []
        )
        sync_user_pic(request, user)
        return render(request, 'auth/Profile.html', {
            'user': user,
            'scholar': scholar,
            'applications': applications,
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during profile load: {e}')


# ─── DASHBOARD ──────────────────────────────────────────────

def dashboard(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        data = {
            'total_scholars':          ScholarProfiles.objects.count(),
            'total_scholarships':      Scholarships.objects.count(),
            'total_applications':      Applications.objects.count(),
            'pending':                 Applications.objects.filter(status='pending').count(),
            'approved':                Applications.objects.filter(status='approved').count(),
            'rejected':                Applications.objects.filter(status='rejected').count(),
            'renewal':    Applications.objects.filter(status='renewal').count(),
            'under_review':            Applications.objects.filter(status='under_review').count(),
            'recent_applications':     Applications.objects.select_related('scholar', 'scholarship').order_by('-applied_at')[:5],
            'recent_announcements':    Announcements.objects.select_related('posted_by').order_by('-created_at')[:3],
            'low_gpa_scholars':        ScholarProfiles.objects.filter(gpa__gte=2.50).order_by('-gpa')[:5],
            'scholarships_with_slots': Scholarships.objects.all().order_by('end_date'),
        }
        return render(request, 'dashboard/Dashboard.html', data)
    except Exception as e:
        return HttpResponse(f'Error occurred during load dashboard: {e}')


# ─── ROLES ──────────────────────────────────────────────────

def role_list(request):
    try:
        guard = admin_only(request)
        if guard: return guard
        return render(request, 'role/RoleList.html', {'roles': Roles.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during load roles: {e}')


def role_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

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
        guard = admin_only(request)
        if guard: return guard

        role_obj = Roles.objects.get(pk=role_id)
        if request.method == 'POST':
            role = request.POST.get('role', '').strip().title()
            if not role:
                messages.error(request, 'Role is required.')
                return render(request, 'role/RoleEdit.html', {'role': role_obj})
            if Roles.objects.filter(role__iexact=role).exclude(pk=role_id).exists():
                messages.error(request, 'Role already exists.')
                return render(request, 'role/RoleEdit.html', {'role': role_obj})
            role_obj.role = role
            role_obj.save()
            messages.success(request, 'Role updated successfully!')
            return render(request, 'role/RoleEdit.html', {'role': role_obj})

        return render(request, 'role/RoleEdit.html', {'role': role_obj})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit role: {e}')


def role_delete(request, role_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        role_obj = Roles.objects.get(pk=role_id)
        if request.method == 'POST':
            role_obj.delete()
            messages.success(request, 'Role deleted successfully!')
            return redirect('/role/list')

        return render(request, 'role/RoleDelete.html', {'role': role_obj})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete role: {e}')


# ─── USERS ──────────────────────────────────────────────────

def user_list(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        search = request.GET.get('search')
        qs = Users.objects.select_related('role').order_by('-user_id')
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(role__role__icontains=search)
            )
        page_obj = Paginator(qs, 10).get_page(request.GET.get('page', 1))
        return render(request, 'user/UserList.html', {'users': page_obj, 'search': search, 'page_obj': page_obj})
    except Exception as e:
        return HttpResponse(f'Error occurred during load users: {e}')


def user_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        if request.method == 'POST':
            full_name        = request.POST.get('full_name', '').strip().title()
            role             = request.POST.get('role', '').strip()
            gender           = request.POST.get('gender', '').strip()
            contact_number   = request.POST.get('contact_number', '').strip()
            email            = request.POST.get('email', '').strip()
            username         = request.POST.get('username', '').strip()
            password         = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            address          = request.POST.get('address', '').strip().title()
            birthdate        = request.POST.get('birthdate', '').strip() or None  # ← ADD THIS
            profile_picture  = request.FILES.get('profile_picture')

            errors = []

            if not full_name:
                errors.append('Full name is required.')
            elif len(full_name) < 2:
                errors.append('Full name must be at least 2 characters.')
            elif re.search(r'[^a-zA-Z\s]', full_name):
                errors.append('Full name must contain letters only.')

            if not role:
                errors.append('Please select a role.')
            elif not Roles.objects.filter(pk=role).exists():
                errors.append('Selected role is invalid.')

            if not contact_number:
                errors.append('Contact number is required.')
            elif not re.fullmatch(r'\d+', contact_number):
                errors.append('Contact number must contain numbers only.')
            elif not (contact_number.startswith('09') or contact_number.startswith('63')):
                errors.append('Contact number must start with 09 or 63.')
            elif Users.objects.filter(contact_number=contact_number).count() >= 3:
                errors.append('This contact number is already in use.')
                
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

            if password != confirm_password:
                errors.append('Passwords do not match.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'user/UserAdd.html', {
                    'roles': Roles.objects.all(),
                    'form_data': {
                        'full_name': full_name, 'gender': gender,
                        'contact_number': contact_number, 'email': email,
                        'username': username, 'role': role, 'address': address,
                        'birthdate': birthdate,   # ← add this
                    }
                })

            Users.objects.create(
                full_name=full_name,
                role=Roles.objects.get(pk=role),
                gender=gender,
                contact_number=contact_number,
                email=email,
                username=username,
                password=make_password(password),
                address=address,
                birthdate=birthdate,
                profile_picture=profile_picture,
            )
            messages.success(request, 'User added successfully!')
            return redirect('/user/add')

        return render(request, 'user/UserAdd.html', {'roles': Roles.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during add user: {e}')


def user_edit(request, user_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        user = Users.objects.get(user_id=user_id)

        if request.method == 'POST':
            full_name      = request.POST.get('full_name', '').strip().title()
            role           = request.POST.get('role', '').strip()
            email          = request.POST.get('email', '').strip()
            username       = request.POST.get('username', '').strip()
            gender         = request.POST.get('gender', '').strip()
            birthdate      = request.POST.get('birthdate', '').strip() or None
            contact_number = request.POST.get('contact_number', '').strip()
            address        = request.POST.get('address', '').strip().title()  # ← ADDED

            errors = []

            if not full_name:
                errors.append('Full name is required.')
            elif len(full_name) < 2:
                errors.append('Full name must be at least 2 characters.')
            elif re.search(r'[^a-zA-Z\s]', full_name):
                errors.append('Full name must contain letters only.')

            if not role:
                errors.append('Please select a role.')
            elif not Roles.objects.filter(pk=role).exists():
                errors.append('Selected role is invalid.')

            if not contact_number:
                errors.append('Contact number is required.')
            elif not re.fullmatch(r'\d+', contact_number):
                errors.append('Contact number must contain numbers only.')
            elif not (contact_number.startswith('09') or contact_number.startswith('63')):
                errors.append('Contact number must start with 09 or 63.')
            elif Users.objects.filter(contact_number=contact_number).exclude(user_id=user_id).count() >= 3:
                errors.append('This contact number is already in use.')

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
                for e in errors:
                    messages.error(request, e)
                return render(request, 'user/UserEdit.html', {'user': user, 'roles': Roles.objects.all()})

            user.full_name      = full_name
            user.role_id        = role
            user.email          = email
            user.username       = username
            user.gender         = gender
            user.birthdate      = birthdate
            user.contact_number = contact_number
            user.address        = address  # ← ADDED

            new_pic = request.FILES.get('profile_picture')
            if new_pic:
                if user.profile_picture and os.path.isfile(user.profile_picture.path):
                    os.remove(user.profile_picture.path)
                user.profile_picture = new_pic

            user.save()

            if request.session.get('user_id') == user.user_id:
                sync_user_pic(request, user)

            messages.success(request, 'User updated successfully!')
            return redirect('/user/list')

        return render(request, 'user/UserEdit.html', {'user': user, 'roles': Roles.objects.all()})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit user: {e}')


def user_delete(request, user_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        user = Users.objects.get(user_id=user_id)
        if request.method == 'POST':
            user.delete()
            messages.success(request, 'User deleted successfully!')
            return redirect('/user/list')

        return render(request, 'user/UserDelete.html', {'user': user})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete user: {e}')


def user_view(request, user_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        user = Users.objects.select_related('role').get(user_id=user_id)
        return render(request, 'user/UserView.html', {'user': user})
    except Exception as e:
        return HttpResponse(f'Error occurred during view user: {e}')


# ─── SCHOLARSHIPS ────────────────────────────────────────────

def scholarship_list(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        search = request.GET.get('search')
        qs = Scholarships.objects.order_by('-scholarship_id')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(eligibility__icontains=search)
            )
        page_obj = Paginator(qs, 10).get_page(request.GET.get('page', 1))
        return render(request, 'scholarship/ScholarshipList.html', {
            'scholarships': page_obj, 'search': search, 'page_obj': page_obj
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load scholarships: {e}')


def scholarship_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        if request.method == 'POST':
            name         = request.POST.get('name', '').strip()
            description  = request.POST.get('description', '').strip()
            amount       = request.POST.get('amount', '').strip()
            slots        = request.POST.get('slots', '').strip()
            eligibility  = request.POST.get('eligibility', '').strip()
            gpa_requirement = request.POST.get('gpa_requirement', '3.00').strip()
            start_date   = request.POST.get('start_date', '').strip()
            end_date     = request.POST.get('end_date', '').strip()

            errors = []
            if not name:
                errors.append('Scholarship name is required.')
            elif Scholarships.objects.filter(name__iexact=name).exists():
                errors.append('Scholarship name already exists.')
            if not description:  errors.append('Description is required.')
            if not amount:       errors.append('Amount is required.')
            if not slots:        errors.append('Slots is required.')
            if not eligibility:  errors.append('Eligibility is required.')
            if not gpa_requirement: errors.append('Required GPA is required.')
            if not start_date:   errors.append('Start date is required.')
            if not end_date:     errors.append('End date is required.')
            if start_date and end_date and start_date >= end_date:
                errors.append('End date must be after start date.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'scholarship/ScholarshipAdd.html')

            Scholarships.objects.create(
                name=name,
                description=description,
                amount=amount,
                slots=slots,
                eligibility=eligibility,
                gpa_requirement=gpa_requirement,
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
        guard = admin_only(request)
        if guard: return guard

        scholarship = Scholarships.objects.get(pk=scholarship_id)
        if request.method == 'POST':
            name         = request.POST.get('name', '').strip()
            description  = request.POST.get('description', '').strip()
            amount       = request.POST.get('amount', '').strip()
            slots        = request.POST.get('slots', '').strip()
            eligibility  = request.POST.get('eligibility', '').strip()
            gpa_requirement = request.POST.get('gpa_requirement', '3.00').strip()
            start_date   = request.POST.get('start_date', '').strip()
            end_date     = request.POST.get('end_date', '').strip()

            errors = []
            if not name:
                errors.append('Scholarship name is required.')
            elif Scholarships.objects.filter(name__iexact=name).exclude(pk=scholarship_id).exists():
                errors.append('Scholarship name already exists.')
            if not description:  errors.append('Description is required.')
            if not amount:       errors.append('Amount is required.')
            if not slots:        errors.append('Slots is required.')
            if not eligibility:  errors.append('Eligibility is required.')
            if not gpa_requirement: errors.append('Required GPA is required.')
            if not start_date:   errors.append('Start date is required.')
            if not end_date:     errors.append('End date is required.')
            if start_date and end_date and start_date >= end_date:
                errors.append('End date must be after start date.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'scholarship/ScholarshipEdit.html', {'scholarship': scholarship})

            scholarship.name         = name
            scholarship.description  = description
            scholarship.amount       = amount
            scholarship.slots        = slots
            scholarship.eligibility  = eligibility
            scholarship.gpa_requirement = gpa_requirement
            scholarship.start_date   = start_date
            scholarship.end_date     = end_date
            scholarship.save()
            messages.success(request, 'Scholarship updated successfully!')
            return redirect('/scholarship/list')

        return render(request, 'scholarship/ScholarshipEdit.html', {'scholarship': scholarship})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit scholarship: {e}')


def scholarship_delete(request, scholarship_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholarship = Scholarships.objects.get(pk=scholarship_id)
        if request.method == 'POST':
            scholarship.delete()
            messages.success(request, 'Scholarship deleted successfully!')
            return redirect('/scholarship/list')

        return render(request, 'scholarship/ScholarshipDelete.html', {'scholarship': scholarship})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete scholarship: {e}')


# ─── SCHOLAR PROFILES ────────────────────────────────────────

def scholar_list(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        search = request.GET.get('search')
        qs = ScholarProfiles.objects.select_related('user').order_by('-scholar_id')
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) |
                Q(address__icontains=search) |
                Q(school__icontains=search) |
                Q(course__icontains=search)
            )
        page_obj = Paginator(qs, 10).get_page(request.GET.get('page', 1))
        return render(request, 'scholar/ScholarList.html', {
            'scholars': page_obj, 'search': search, 'page_obj': page_obj
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load scholars: {e}')


def scholar_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        existing_user_ids = ScholarProfiles.objects.values_list('user_id', flat=True)
        available_users   = Users.objects.filter(role__role='Scholar').exclude(user_id__in=existing_user_ids)

        if request.method == 'POST':
            user_id     = request.POST.get('user_id', '').strip()
            address     = request.POST.get('address', '').strip().title()
            school      = request.POST.get('school', '').strip().title()
            course      = request.POST.get('course', '').strip().title()
            year_level  = request.POST.get('year_level', '').strip()
            gpa         = request.POST.get('gpa', '').strip()
            semester    = request.POST.get('semester', '').strip()
            school_year = request.POST.get('school_year', '').strip()
            subjects    = request.POST.getlist('subject[]')
            grades_list = request.POST.getlist('grade[]')

            errors = []
            if not user_id:
                errors.append('Please select a user.')
            elif not Users.objects.filter(pk=user_id, role__role='Scholar').exists():
                errors.append('Selected user is invalid.')
            elif ScholarProfiles.objects.filter(user_id=user_id).exists():
                errors.append('This user already has a scholar profile.')
            if not address:     errors.append('Address is required.')
            if not school:      errors.append('School is required.')
            if not course:      errors.append('Course is required.')
            if not year_level:  errors.append('Year level is required.')
            if not gpa:         errors.append('GPA is required.')
            if not semester:    errors.append('Semester is required.')
            if not school_year: errors.append('School year is required.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'scholar/ScholarAdd.html', {'available_users': available_users})

            user_obj = Users.objects.get(pk=user_id)
            scholar  = ScholarProfiles.objects.create(
                user=user_obj,
                full_name=user_obj.full_name,
                address=address,
                school=school,
                course=course,
                year_level=year_level,
                gpa=gpa,
            )

            for i, subj in enumerate(subjects):
                subj      = subj.strip()
                grade_val = grades_list[i].strip() if i < len(grades_list) else ''
                if subj and grade_val:
                    Grades.objects.create(
                        scholar=scholar,
                        subject=subj,
                        grade=grade_val,
                        semester=semester,
                        school_year=school_year,
                    )

            if request.session.get('user_id') == user_obj.user_id:
                sync_user_pic(request, user_obj)

            messages.success(request, 'Scholar added successfully!')
            return redirect('/scholar/list')

        return render(request, 'scholar/ScholarAdd.html', {'available_users': available_users})
    except Exception as e:
        return HttpResponse(f'Error occurred during add scholar: {e}')


def scholar_edit(request, scholar_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholar = ScholarProfiles.objects.get(pk=scholar_id)
        if request.method == 'POST':
            full_name  = request.POST.get('full_name', '').strip().title()
            address    = request.POST.get('address', '').strip().title()
            school     = request.POST.get('school', '').strip().title()
            course     = request.POST.get('course', '').strip().title()
            year_level = request.POST.get('year_level', '').strip()
            gpa        = request.POST.get('gpa', '').strip()

            errors = []
            if not full_name: errors.append('Full name is required.')
            if not address:    errors.append('Address is required.')
            if not school:     errors.append('School is required.')
            if not course:     errors.append('Course is required.')
            if not year_level: errors.append('Year level is required.')
            if not gpa:        errors.append('GPA is required.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'scholar/ScholarEdit.html', {'scholar': scholar})

            scholar.full_name  = full_name
            scholar.address    = address
            scholar.school     = school
            scholar.course     = course
            scholar.year_level = year_level
            scholar.gpa        = gpa
            scholar.save()

            if request.session.get('user_id') == scholar.user_id:
                sync_user_pic(request, scholar.user)

            messages.success(request, 'Scholar updated successfully!')
            return redirect('/scholar/list')

        return render(request, 'scholar/ScholarEdit.html', {'scholar': scholar})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit scholar: {e}')


def scholar_delete(request, scholar_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholar = ScholarProfiles.objects.get(pk=scholar_id)
        if request.method == 'POST':
            scholar.delete()
            messages.success(request, 'Scholar deleted successfully!')
            return redirect('/scholar/list')

        return render(request, 'scholar/ScholarDelete.html', {'scholar': scholar})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete scholar: {e}')


def scholar_view(request, scholar_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholar = ScholarProfiles.objects.select_related('user').get(pk=scholar_id)
        grades  = Grades.objects.filter(scholar=scholar).order_by('-school_year', 'semester')
        return render(request, 'scholar/ScholarView.html', {'scholar': scholar, 'grades': grades})
    except Exception as e:
        return HttpResponse(f'Error occurred during view scholar: {e}')


# ─── APPLICATIONS ────────────────────────────────────────────

def application_list(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        search = request.GET.get('search')
        qs = Applications.objects.select_related('scholar', 'scholarship').order_by('-application_id')
        if search:
            qs = qs.filter(
                Q(scholar__full_name__icontains=search) |
                Q(scholarship__name__icontains=search) |
                Q(status__icontains=search)
            )
        page_obj = Paginator(qs, 10).get_page(request.GET.get('page', 1))
        return render(request, 'application/ApplicationList.html', {
            'applications': page_obj, 'search': search, 'page_obj': page_obj
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load applications: {e}')


def application_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        already_applied_ids = Applications.objects.values_list('scholar_id', flat=True)
        available_scholars  = ScholarProfiles.objects.exclude(scholar_id__in=already_applied_ids)

        if request.method == 'POST':
            scholar_id     = request.POST.get('scholar', '').strip()
            scholarship_id = request.POST.get('scholarship', '').strip()
            remarks        = request.POST.get('remarks', '').strip()

            errors = []
            if not scholar_id:
                errors.append('Scholar is required.')
            if not scholarship_id:
                errors.append('Scholarship is required.')
            elif Applications.objects.filter(scholar_id=scholar_id, scholarship_id=scholarship_id).exists():
                errors.append('This scholar already applied for this scholarship.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'application/ApplicationAdd.html', {
                    'scholars': available_scholars,
                    'scholarships': Scholarships.objects.all()
                })

            scholar     = ScholarProfiles.objects.get(pk=scholar_id)
            scholarship = Scholarships.objects.get(pk=scholarship_id)

            if scholar.gpa > scholarship.gpa_requirement:
                Applications.objects.create(
                    scholar=scholar,
                    scholarship=scholarship,
                    status='rejected',
                    remarks=f'Automatically rejected: Scholar GPA ({scholar.gpa}) does not meet the required GPA ({scholarship.gpa_requirement}).'
                )
                messages.warning(request, f'Application automatically rejected — {scholar.full_name} GPA ({scholar.gpa}) does not meet the required GPA ({scholarship.gpa_requirement}).')
                return redirect('/application/list')

            Applications.objects.create(
                scholar=scholar,
                scholarship=scholarship,
                remarks=remarks
            )
            # Decrease slots
            if scholarship.slots > 0:
                scholarship.slots -= 1
                scholarship.save()
            messages.success(request, 'Application submitted successfully!')
            return redirect('/application/list')

        return render(request, 'application/ApplicationAdd.html', {
            'scholars': available_scholars,
            'scholarships': Scholarships.objects.all()
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during add application: {e}')


def application_edit(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)

        if request.method == 'POST':
            status         = request.POST.get('status', '').strip()
            remarks        = request.POST.get('remarks', '').strip()
            scholarship_id = request.POST.get('scholarship', '').strip()

            if not status:
                messages.error(request, 'Status is required.')
                return render(request, 'application/ApplicationEdit.html', {
                    'application': application,
                    'scholarships': Scholarships.objects.all()
                })

            if not scholarship_id:
                messages.error(request, 'Scholarship is required.')
                return render(request, 'application/ApplicationEdit.html', {
                    'application': application,
                    'scholarships': Scholarships.objects.all()
                })

            try:
                new_scholarship = Scholarships.objects.get(pk=scholarship_id)
            except Scholarships.DoesNotExist:
                messages.error(request, 'Selected scholarship does not exist.')
                return render(request, 'application/ApplicationEdit.html', {
                    'application': application,
                    'scholarships': Scholarships.objects.all()
                })

            old_status      = application.status
            old_scholarship = application.scholarship

            if status == 'approved':
                scholar_gpa  = application.scholar.gpa
                required_gpa = new_scholarship.gpa_requirement
                if scholar_gpa > required_gpa:
                    messages.error(request, f'Cannot approve — {application.scholar.full_name} GPA ({scholar_gpa}) does not meet the required GPA ({required_gpa}).')
                    return render(request, 'application/ApplicationEdit.html', {
                        'application': application,
                        'scholarships': Scholarships.objects.all()
                    })

            # Handle slot changes for OLD scholarship
            if old_scholarship != new_scholarship:
                # Scholarship changed — restore slot to old one if it was approved
                if old_status == 'approved':
                    old_scholarship.slots += 1
                    old_scholarship.save()
                # Deduct slot from new scholarship if approving
            if status == 'approved':
                if new_scholarship.slots <= 0:
                    messages.error(request, f'Cannot assign — {new_scholarship.name} has no available slots.')
                    return render(request, 'application/ApplicationEdit.html', {
                        'application': application,
                        'scholarships': Scholarships.objects.all()
                    })
                new_scholarship.slots -= 1
                new_scholarship.save()
                        
            else:
                # Same scholarship — just handle status change
                if status == 'approved' and old_status != 'approved':
                    if new_scholarship.slots > 0:
                        new_scholarship.slots -= 1
                        new_scholarship.save()
                elif old_status == 'approved' and status != 'approved':
                    new_scholarship.slots += 1
                    new_scholarship.save()

            application.status      = status
            application.remarks     = remarks
            application.scholarship = new_scholarship
            application.save()

            messages.success(request, 'Application updated successfully!')
            return redirect('/application/list')

        return render(request, 'application/ApplicationEdit.html', {
            'application': application,
            'scholarships': Scholarships.objects.all()
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during edit application: {e}')

def application_delete(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)
        if request.method == 'POST':
            # Restore slot if application was approved
            if application.status == 'approved':
                scholarship = application.scholarship
                scholarship.slots += 1
                scholarship.save()
            application.delete()
            messages.success(request, 'Application deleted successfully!')
            return redirect('/application/list')

        return render(request, 'application/ApplicationDelete.html', {'application': application})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete application: {e}')


def application_detail(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.select_related('scholar', 'scholarship').get(pk=application_id)
        documents   = Documents.objects.filter(application=application)
        return render(request, 'application/ApplicationDetail.html', {
            'application': application, 'documents': documents
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load application: {e}')


def application_approve(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)
        application.status = 'approved'
        application.save()
        messages.success(request, 'Application approved successfully!')
        return redirect(f'/application/{application_id}/detail')
    except Exception as e:
        return HttpResponse(f'Error occurred during approve: {e}')


def application_reject(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)
        application.status = 'rejected'
        application.save()
        messages.success(request, 'Application rejected successfully!')
        return redirect(f'/application/{application_id}/detail')
    except Exception as e:
        return HttpResponse(f'Error occurred during reject: {e}')


# ─── DOCUMENTS ───────────────────────────────────────────────

def document_list(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)
        documents   = Documents.objects.filter(application=application)
        return render(request, 'document/DocumentList.html', {
            'documents': documents, 'application': application
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load documents: {e}')


def document_add(request, application_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        application = Applications.objects.get(pk=application_id)
        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            file = request.FILES.get('file')

            errors = []
            if not name: errors.append('Document name is required.')
            if not file: errors.append('File is required.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'document/DocumentAdd.html', {'application': application})

            Documents.objects.create(application=application, name=name, file=file)
            messages.success(request, 'Document uploaded successfully!')
            return redirect(f'/application/{application_id}/documents')

        return render(request, 'document/DocumentAdd.html', {'application': application})
    except Exception as e:
        return HttpResponse(f'Error occurred during add document: {e}')


def document_edit(request, document_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        document       = Documents.objects.get(pk=document_id)
        application_id = document.application.application_id

        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            file = request.FILES.get('file')

            if not name:
                messages.error(request, 'Document name is required.')
                return render(request, 'document/DocumentEdit.html', {'document': document})

            document.name = name
            if file:
                if document.file and os.path.isfile(document.file.path):
                    os.remove(document.file.path)
                document.file = file

            document.save()
            messages.success(request, 'Document updated successfully!')
            return redirect(f'/application/{application_id}/documents')

        return render(request, 'document/DocumentEdit.html', {'document': document})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit document: {e}')


def document_delete(request, document_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        document       = Documents.objects.get(pk=document_id)
        application_id = document.application.application_id
        if request.method == 'POST':
            if document.file and os.path.isfile(document.file.path):
                os.remove(document.file.path)
            document.delete()
            messages.success(request, 'Document deleted successfully!')
            return redirect(f'/application/{application_id}/documents')

        return render(request, 'document/DocumentDelete.html', {'document': document})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete document: {e}')


# ─── GRADES ──────────────────────────────────────────────────

def grade_list(request, scholar_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholar = ScholarProfiles.objects.get(pk=scholar_id)
        grades  = Grades.objects.filter(scholar=scholar).order_by('-created_at')
        return render(request, 'grade/GradeList.html', {'grades': grades, 'scholar': scholar})
    except Exception as e:
        return HttpResponse(f'Error occurred during load grades: {e}')


def grade_add(request, scholar_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        scholar = ScholarProfiles.objects.get(pk=scholar_id)

        # Auto-calculate school year (June–May academic calendar)
        today = date.today()
        if today.month >= 6:
            school_year = f"{today.year}-{today.year + 1}"
        else:
            school_year = f"{today.year - 1}-{today.year}"

        if request.method == 'POST':
            subject  = request.POST.get('subject', '').strip()
            grade    = request.POST.get('grade', '').strip()
            semester = request.POST.get('semester', '').strip()
            # school_year is NO LONGER read from POST — use the auto value above

            errors = []
            if not subject:  errors.append('Subject is required.')
            if not grade:    errors.append('Grade is required.')
            if not semester: errors.append('Semester is required.')

            if subject and semester:
                if Grades.objects.filter(
                    scholar=scholar,
                    subject__iexact=subject,
                    semester__iexact=semester,
                    school_year=school_year
                ).exists():
                    errors.append(f'"{subject}" already exists for {semester} {school_year}.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'grade/GradeAdd.html', {
                    'scholar': scholar,
                    'school_year': school_year,  # pass it for display
                })

            Grades.objects.create(
                scholar=scholar, subject=subject, grade=grade,
                semester=semester, school_year=school_year,
            )
            recalculate_gpa(scholar)
            messages.success(request, f'Grade added! GPA updated to {scholar.gpa}.')
            return redirect(f'/scholar/{scholar_id}/grades')

        return render(request, 'grade/GradeAdd.html', {
            'scholar': scholar,
            'school_year': school_year,  # pass it for display
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during add grade: {e}')


def grade_delete(request, grade_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        grade_obj  = Grades.objects.get(pk=grade_id)
        scholar    = grade_obj.scholar
        scholar_id = scholar.scholar_id

        if request.method == 'POST':
            grade_obj.delete()
            recalculate_gpa(scholar)
            messages.success(request, 'Grade deleted! GPA recalculated.')
            return redirect(f'/scholar/{scholar_id}/grades')

        return render(request, 'grade/GradeDelete.html', {'grade': grade_obj})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete grade: {e}')


def my_grades(request):
    try:
        guard = login_required(request)
        if guard: return guard

        user    = get_session_user(request)
        scholar = ScholarProfiles.objects.filter(user=user).first()

        if not scholar:
            return render(request, 'grade/MyGrades.html', {'scholar': None, 'grades': []})

        maintaining_grade = scholar.maintaining_grade

        selected_semester = request.GET.get('semester', '')
        selected_year     = request.GET.get('school_year', '')

        grades = Grades.objects.filter(scholar=scholar).order_by('-school_year', 'semester')

        if selected_semester:
            grades = grades.filter(semester=selected_semester)
        if selected_year:
            grades = grades.filter(school_year=selected_year)

        school_years = Grades.objects.filter(scholar=scholar).values_list('school_year', flat=True).distinct().order_by('-school_year')

        all_grades       = Grades.objects.filter(scholar=scholar)
        total_units      = sum(float(g.units) for g in all_grades)
        passed_subjects  = all_grades.filter(grade__lte=maintaining_grade).count()
        failed_subjects  = all_grades.filter(grade__gt=maintaining_grade).count()

        return render(request, 'grade/MyGrades.html', {
            'scholar':            scholar,
            'grades':             grades,
            'total_units':        total_units,
            'passed_subjects':    passed_subjects,
            'failed_subjects':    failed_subjects,
            'maintaining_grade':  maintaining_grade,
            'school_years':       school_years,
            'selected_semester':  selected_semester,
            'selected_year':      selected_year,
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load grades: {e}')
def grade_edit(request, grade_id):
    try:
        guard = admin_only(request)
        if guard: return guard
 
        grade_obj  = Grades.objects.get(pk=grade_id)
        scholar    = grade_obj.scholar
        scholar_id = scholar.scholar_id
 
        if request.method == 'POST':
            subject  = request.POST.get('subject', '').strip()
            grade    = request.POST.get('grade', '').strip()
            units    = request.POST.get('units', '').strip()
            semester = request.POST.get('semester', '').strip()
 
            errors = []
            if not subject:  errors.append('Subject is required.')
            if not grade:    errors.append('Grade is required.')
            if not units:    errors.append('Units is required.')
            if not semester: errors.append('Semester is required.')
 
            # Check duplicate — same subject/semester/year but different grade_id
            if subject and semester:
                if Grades.objects.filter(
                    scholar=scholar,
                    subject__iexact=subject,
                    semester__iexact=semester,
                    school_year=grade_obj.school_year
                ).exclude(pk=grade_id).exists():
                    errors.append(f'"{subject}" already exists for {semester} {grade_obj.school_year}.')
 
            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'grade/GradeEdit.html', {'grade': grade_obj})
 
            grade_obj.subject  = subject
            grade_obj.grade    = grade
            grade_obj.units    = units
            grade_obj.semester = semester
            # school_year is intentionally NOT editable — kept as-is
            grade_obj.save()
 
            recalculate_gpa(scholar)
            messages.success(request, f'Grade updated! GPA recalculated to {scholar.gpa}.')
            return redirect(f'/scholar/{scholar_id}/grades')
 
        return render(request, 'grade/GradeEdit.html', {'grade': grade_obj})
    except Exception as e:
        return HttpResponse(f'Error occurred during edit grade: {e}')


# ─── SCHOLAR PORTAL ──────────────────────────────────────────

def scholar_my_applications(request):
    try:
        guard = login_required(request)
        if guard: return guard

        user    = get_session_user(request)
        scholar = ScholarProfiles.objects.filter(user=user).first()
        applications = (
            Applications.objects.filter(scholar=scholar)
            .select_related('scholarship').order_by('-applied_at')
            if scholar else []
        )
        return render(request, 'scholar/MyApplications.html', {
            'applications': applications, 'scholar': scholar
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load applications: {e}')


def scholar_my_documents(request, application_id):
    try:
        guard = login_required(request)
        if guard: return guard

        user    = get_session_user(request)
        scholar = ScholarProfiles.objects.filter(user=user).first()
        application = Applications.objects.get(pk=application_id)

        if not scholar or application.scholar != scholar:
            messages.error(request, 'Access denied.')
            return redirect('/scholar/my-applications')

        documents = Documents.objects.filter(application=application)
        return render(request, 'scholar/MyDocuments.html', {
            'documents': documents, 'application': application
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during load documents: {e}')


# ─── ANNOUNCEMENTS ───────────────────────────────────────────

def announcement_list(request):
    try:
        guard = login_required(request)
        if guard: return guard

        user = get_session_user(request)

        if user.role.role == 'Admin':
            # Admin sees everything
            announcements = Announcements.objects.select_related('posted_by', 'target_user').order_by('-created_at')
        else:
            # Scholars see public announcements + their own private ones
            announcements = Announcements.objects.select_related('posted_by', 'target_user').filter(
                Q(target_user__isnull=True) | Q(target_user=user)
            ).order_by('-created_at')

        return render(request, 'announcement/AnnouncementList.html', {'announcements': announcements})
    except Exception as e:
        return HttpResponse(f'Error occurred during load announcements: {e}')


def announcement_add(request):
    try:
        guard = admin_only(request)
        if guard: return guard

        user = get_session_user(request)
        # Only show Scholar-role users in the target dropdown
        scholars = Users.objects.filter(role__role='Scholar').order_by('full_name')

        if request.method == 'POST':
            title       = request.POST.get('title', '').strip()
            content     = request.POST.get('content', '').strip()
            target_user_id = request.POST.get('target_user', '').strip()  # optional

            errors = []
            if not title:   errors.append('Title is required.')
            if not content: errors.append('Content is required.')

            target_user_obj = None
            if target_user_id:
                try:
                    target_user_obj = Users.objects.get(pk=target_user_id)
                except Users.DoesNotExist:
                    errors.append('Selected user does not exist.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'announcement/AnnouncementAdd.html', {
                    'form_data': {'title': title, 'content': content},
                    'scholars': scholars,
                })

            Announcements.objects.create(
                title=title,
                content=content,
                posted_by=user,
                target_user=target_user_obj,  # None = public
            )
            messages.success(request, 'Announcement posted successfully!')
            return redirect('/announcement/list')

        return render(request, 'announcement/AnnouncementAdd.html', {'scholars': scholars})
    except Exception as e:
        return HttpResponse(f'Error occurred during add announcement: {e}')


def announcement_delete(request, announcement_id):
    try:
        guard = admin_only(request)
        if guard: return guard

        announcement = Announcements.objects.get(pk=announcement_id)
        if request.method == 'POST':
            announcement.delete()
            messages.success(request, 'Announcement deleted successfully!')
            return redirect('/announcement/list')

        return render(request, 'announcement/AnnouncementDelete.html', {'announcement': announcement})
    except Exception as e:
        return HttpResponse(f'Error occurred during delete announcement: {e}')
    
def check_contact(request):
    contact = request.GET.get('contact_number', '')
    user_id = request.GET.get('user_id', None)
    qs = Users.objects.filter(contact_number=contact)
    if user_id:
        qs = qs.exclude(user_id=user_id)
    # Allow up to 3 users to share the same contact number
    return JsonResponse({'available': not qs.exists()})

def check_email(request):
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id', None)
    qs = Users.objects.filter(email__iexact=email)
    if user_id:
        qs = qs.exclude(user_id=user_id)
    return JsonResponse({'available': not qs.exists()})

def check_username(request):
    username = request.GET.get('username', '').strip()
    user_id = request.GET.get('user_id', None) # Passed when editing an existing user
    
    if not username:
        return JsonResponse({'available': False})
        
    # Start evaluating global matching queries
    query = Users.objects.filter(username__iexact=username)
    
    # If a user_id exists (meaning we're editing an existing profile), exclude them from duplication logic
    if user_id:
        query = query.exclude(user_id=user_id)
        
    is_available = not query.exists()
    return JsonResponse({'available': is_available})

def scholar_apply(request):
    try:
        guard = login_required(request)
        if guard: return guard

        user    = get_session_user(request)
        scholar = ScholarProfiles.objects.filter(user=user).first()

        if not scholar:
            messages.error(request, 'You need a scholar profile to apply.')
            return redirect('/profile')

        # Only show scholarships the scholar qualifies for based on GPA
        # and has not already applied to
        already_applied_ids = Applications.objects.filter(
            scholar=scholar
        ).values_list('scholarship_id', flat=True)

        eligible_scholarships = Scholarships.objects.filter(
            gpa_requirement__gte=scholar.maintaining_grade
        ).exclude(
            scholarship_id__in=already_applied_ids
        ).filter(slots__gt=0)

        if request.method == 'POST':
            scholarship_id = request.POST.get('scholarship', '').strip()
            remarks        = request.POST.get('remarks', '').strip()

            def render_form(error_msg=None):
                if error_msg:
                    messages.error(request, error_msg)
                return render(request, 'scholar/ScholarApply.html', {
                    'scholarships': eligible_scholarships,
                    'scholar':      scholar,
                })

            if not scholarship_id:
                return render_form('Please select a scholarship.')

            try:
                scholarship = Scholarships.objects.get(pk=scholarship_id)
            except Scholarships.DoesNotExist:
                return render_form('Selected scholarship does not exist.')

            # GPA check
            if scholar.maintaining_grade > scholarship.gpa_requirement:
                return render_form(
                    f'You do not meet the GPA requirement for "{scholarship.name}". '
                    f'Required: {scholarship.gpa_requirement} | Your GPA: {scholar.maintaining_grade}'
                )

            # Duplicate check
            if Applications.objects.filter(scholar=scholar, scholarship=scholarship).exists():
                return render_form(f'You have already applied for "{scholarship.name}".')

            # Slots check
            if scholarship.slots <= 0:
                return render_form(f'"{scholarship.name}" has no available slots.')

            Applications.objects.create(
                scholar=scholar,
                scholarship=scholarship,
                remarks=remarks,
            )
            messages.success(request, f'Application for "{scholarship.name}" submitted successfully!')
            return redirect('/scholar/my-applications')

        return render(request, 'scholar/ScholarApply.html', {
            'scholarships': eligible_scholarships,
            'scholar':      scholar,
        })
    except Exception as e:
        return HttpResponse(f'Error occurred during apply: {e}')