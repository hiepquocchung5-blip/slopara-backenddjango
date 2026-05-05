from django.contrib import admin
from django.contrib import messages
from .models import User

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    # 1. Dynamic Table View: Exposes all relevant fields except the password hash
    list_display = (
        'id', 
        'phone_number', 
        'username', 
        'balance', 
        'lifetime_deposit', 
        'is_profile_verified', 
        'is_active', 
        'created_at'  # CRITICAL FIX: Changed from date_joined to created_at
    )
    
    # 2. Filters for quick sorting
    list_filter = ('is_active', 'is_profile_verified', 'is_staff')
    
    # 3. Search capability
    search_fields = ('phone_number', 'username')
    
    # 4. Protect critical timestamp fields
    readonly_fields = ('created_at', 'last_login') # CRITICAL FIX: Changed from date_joined
    ordering = ('-created_at',) # CRITICAL FIX: Changed from date_joined

    # 5. Form Layout: Hides the password field to prevent plaintext saving issues
    # while organizing the remaining data into clean sections.
    fieldsets = (
        ('Authentication Info', {
            'fields': ('phone_number', 'last_login')
        }),
        ('Profile Data', {
            'fields': ('username', 'is_profile_verified')
        }),
        ('Financial Analytics', {
            'fields': ('balance', 'lifetime_deposit')
        }),
        ('Security & Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Timestamps', {
            'fields': ('created_at',) # CRITICAL FIX: Changed from date_joined
        }),
    )

    # 6. Custom Bulk Actions (Ban / Valid)
    actions = ['ban_users', 'unban_users', 'verify_profiles']

    def ban_users(self, request, queryset):
        """Bans users by setting is_active to False (prevents JWT login)."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, 
            f"{updated} users have been BANNED (Deactivated).", 
            messages.WARNING
        )
    ban_users.short_description = "Ban selected users (Set Inactive)"

    def unban_users(self, request, queryset):
        """Unbans users by setting is_active to True."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, 
            f"{updated} users have been UNBANNED (Activated).", 
            messages.SUCCESS
        )
    unban_users.short_description = "Unban selected users (Set Active)"

    def verify_profiles(self, request, queryset):
        """Marks user profiles as verified."""
        updated = queryset.update(is_profile_verified=True)
        self.message_user(
            request, 
            f"{updated} user profiles marked as VERIFIED.", 
            messages.SUCCESS
        )
    verify_profiles.short_description = "Mark selected profiles as Verified"