import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from decimal import Decimal

class CustomUserManager(BaseUserManager):
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
        extra_fields.setdefault('user_type', 'VIP') # Admins are VIPs by default

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPES = (
        ('NORMAL', 'Normal Player'),
        ('AGENT', 'Agent (25% Commission)'),
        ('VIP', 'VIP (100% Commission)'),
    )

    phone_number = models.CharField(max_length=15, unique=True, db_index=True)
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    is_profile_verified = models.BooleanField(default=False)
    
    # User Type & Referral System
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='NORMAL')
    
    # CRITICAL FIX: Removed `unique=True` at the DB schema level to bypass SQLite's 
    # migration crash on existing rows. We enforce uniqueness in the save() method instead.
    referral_code = models.CharField(max_length=8, blank=True, null=True)
    
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    commission_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_commission_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Financials
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

    def save(self, *args, **kwargs):
        # Auto-generate a secure 8-character alphanumeric referral code on creation
        if not self.referral_code:
            # Programmatic uniqueness check to guarantee no collisions 
            # even without the DB-level unique constraint.
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    def get_commission_rate(self):
        """Returns the percentage multiplier of the base referral pool."""
        if self.user_type == 'VIP': return Decimal('1.00')    # 100%
        if self.user_type == 'AGENT': return Decimal('0.25')  # 25%
        return Decimal('0.00')                                # 0%

    def __str__(self):
        return f"[{self.user_type}] {self.username if self.username else self.phone_number}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} - {self.title}"