from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # ─── AUTH ──────────────────────────────────
    path('login', views.login_view),
    path('logout', views.logout_view),
    path('profile', views.profile_view),

    # ─── DASHBOARD ─────────────────────────────
    path('', views.dashboard),

    # ─── ROLES ─────────────────────────────────
    path('role/list', views.role_list),
    path('role/add', views.role_add),
    path('role/edit/<int:role_id>', views.role_edit),
    path('role/delete/<int:role_id>', views.role_delete),

    # ─── USERS ─────────────────────────────────
    path('user/list', views.user_list),
    path('user/add', views.user_add),
    path('user/edit/<int:user_id>', views.user_edit),
    path('user/delete/<int:user_id>', views.user_delete),

    # ─── SCHOLARSHIPS ───────────────────────────
    path('scholarship/list', views.scholarship_list),
    path('scholarship/add', views.scholarship_add),
    path('scholarship/edit/<int:scholarship_id>', views.scholarship_edit),
    path('scholarship/delete/<int:scholarship_id>', views.scholarship_delete),

    # ─── SCHOLARS ───────────────────────────────
    path('scholar/list', views.scholar_list),
    path('scholar/add', views.scholar_add),
    path('scholar/edit/<int:scholar_id>', views.scholar_edit),
    path('scholar/delete/<int:scholar_id>', views.scholar_delete),

    # ─── APPLICATIONS ───────────────────────────
    path('application/list', views.application_list),
    path('application/add', views.application_add),
    path('application/edit/<int:application_id>', views.application_edit),
    path('application/delete/<int:application_id>', views.application_delete),

    # ─── DOCUMENTS ──────────────────────────────
    path('application/<int:application_id>/documents', views.document_list),
    path('application/<int:application_id>/documents/add', views.document_add),
    path('document/delete/<int:document_id>', views.document_delete),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)