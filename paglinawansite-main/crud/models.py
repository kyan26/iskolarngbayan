from django.db import models

# Create your models here.

# ─── ROLES ─────────────────────────────────────────────────
class Roles(models.Model):
    class Meta:
        db_table = 'tbl_roles'
    role_id = models.BigAutoField(primary_key=True)
    role = models.CharField(max_length=55)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.role

# ─── USERS ─────────────────────────────────────────────────
class Users(models.Model):
    class Meta:
        db_table = 'tbl_users'
    user_id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    role = models.ForeignKey(Roles, on_delete=models.CASCADE)
    email = models.EmailField(max_length=100, unique=True)
    username = models.CharField(max_length=55, unique=True)
    password = models.CharField(max_length=255)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

# ─── SCHOLARSHIPS ───────────────────────────────────────────
class Scholarships(models.Model):
    class Meta:
        db_table = 'tbl_scholarships'
    scholarship_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    slots = models.IntegerField()
    eligibility = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# ─── SCHOLAR PROFILES ───────────────────────────────────────
class ScholarProfiles(models.Model):
    class Meta:
        db_table = 'tbl_scholar_profiles'
    scholar_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(Users, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    school = models.CharField(max_length=200)
    course = models.CharField(max_length=200)
    year_level = models.CharField(max_length=20)
    gpa = models.DecimalField(max_digits=4, decimal_places=2)
    photo = models.ImageField(upload_to='scholar_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

# ─── APPLICATIONS ───────────────────────────────────────────
class Applications(models.Model):
    class Meta:
        db_table = 'tbl_applications'

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('renewal', 'Renewal'),
    )
    application_id = models.BigAutoField(primary_key=True)
    scholar = models.ForeignKey(ScholarProfiles, on_delete=models.CASCADE)
    scholarship = models.ForeignKey(Scholarships, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.scholar.full_name} - {self.scholarship.name} ({self.status})"

# ─── DOCUMENTS ──────────────────────────────────────────────
class Documents(models.Model):
    class Meta:
        db_table = 'tbl_documents'
    document_id = models.BigAutoField(primary_key=True)
    application = models.ForeignKey(Applications, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.application.scholar.full_name}"