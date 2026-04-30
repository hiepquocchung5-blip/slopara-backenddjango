from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from decimal import Decimal

class CustomUserManager(BaseUserManager):
    """
    Custom manager to handle Phone Number based authentication instead of usernames/emails.
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Core Player Identity & Wallet Model
    """
    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_profile_verified = models.BooleanField(default=False)
    
    # Financials (Using Decimal to prevent floating point math errors)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lifetime_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Retention Mechanics
    last_daily_bonus_claim = models.DateTimeField(null=True, blank=True)
    consecutive_logins = models.IntegerField(default=0)

    # Django Admin Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username if self.username else self.phone_number


class Notification(models.Model):
    """
    Persistent Player Inbox System
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} - {self.title}"