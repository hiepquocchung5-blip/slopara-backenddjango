from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, UserProfileView, LeaderboardView, 
    NotificationListView, NotificationReadView, DailyBonusClaimView,
    BankerPlayerListView, BankerPlayerToggleBanView
)

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', TokenObtainPairView.as_view(), name='auth_login'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile & Engagement
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('daily-bonus/', DailyBonusClaimView.as_view(), name='daily_bonus'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    
    # Inbox
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/<int:pk>/read/', NotificationReadView.as_view(), name='notification_read'),
    
    # Banker Administration
    path('admin/players/', BankerPlayerListView.as_view(), name='admin_players'),
    path('admin/players/<int:user_id>/toggle-ban/', BankerPlayerToggleBanView.as_view(), name='admin_player_ban'),
]