from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, 
    SingleDeviceLoginView, # CRITICAL FIX: Imported our custom Stateful JWT view
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
    # CRITICAL FIX: Used SingleDeviceLoginView so the security stamp is properly injected into the token
    path('login/', SingleDeviceLoginView.as_view(), name='auth_login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile, Referrals & Retention
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('daily-bonus/', DailyBonusClaimView.as_view(), name='daily_bonus'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('referrals/', ReferralDashboardView.as_view(), name='referral_dashboard'),
    
    # Inbox endpoints
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification_read'),
    
    # Banker endpoints
    path('admin/players/', BankerPlayerListView.as_view(), name='admin_players'),
    path('admin/players/<int:user_id>/toggle-ban/', BankerPlayerToggleBanView.as_view(), name='admin_player_ban'),
]