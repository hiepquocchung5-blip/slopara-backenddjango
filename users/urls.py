from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, 
    SingleDeviceLoginView, 
    UserProfileView, 
    NotificationListView, 
    NotificationReadView,
    LeaderboardView,
    DailyBonusClaimView,
    ReferralDashboardView,
    BankerPlayerListView,
    BankerPlayerToggleBanView
)

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='auth_register'),
    
    # CRITICAL FIX: Restored custom login view to fix 401 missing security stamps
    path('login/', SingleDeviceLoginView.as_view(), name='auth_login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile & Inbox endpoints
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification_read'),
    
    # Leaderboard & Economy
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('daily-bonus/', DailyBonusClaimView.as_view(), name='daily_bonus'),
    path('referrals/', ReferralDashboardView.as_view(), name='referral_dashboard'),
    
    # Admin
    path('admin/players/', BankerPlayerListView.as_view(), name='admin_players'),
    path('admin/players/<int:user_id>/toggle-ban/', BankerPlayerToggleBanView.as_view(), name='admin_player_ban'),
]