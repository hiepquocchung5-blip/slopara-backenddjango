from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .serializers import RegisterSerializer, UserSerializer, LeaderboardSerializer
from .models import Notification

User = get_user_model()

# --- AUTH & PROFILE ---
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User registered successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)

class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {}
        if 'username' in request.data: data['username'] = request.data['username']
        
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if instance.username and not instance.is_profile_verified:
            instance.is_profile_verified = True
            instance.save()

        return Response(serializer.data)

# --- DAILY BONUS ENGINE ---
class DailyBonusClaimView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = User.objects.select_for_update().get(id=request.user.id)
        now = timezone.now()

        # Enforce 24-hour cooldown
        if user.last_daily_bonus_claim and now < user.last_daily_bonus_claim + timedelta(hours=24):
            time_left = (user.last_daily_bonus_claim + timedelta(hours=24)) - now
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return Response({"error": f"Check back in {hours}h {minutes}m."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate Consecutive Streak
        if user.last_daily_bonus_claim and now > user.last_daily_bonus_claim + timedelta(hours=48):
            user.consecutive_logins = 1
        else:
            user.consecutive_logins += 1

        bonus_amount = min(1000 + (user.consecutive_logins - 1) * 500, 5000)
        user.balance += Decimal(str(bonus_amount))
        user.last_daily_bonus_claim = now
        user.save()

        Notification.objects.create(
            user=user,
            title=f"Day {user.consecutive_logins} Streak 🎁",
            message=f"You received {bonus_amount} MMK for your daily login bonus!"
        )

        return Response({
            "message": "Daily bonus claimed.",
            "bonus_amount": bonus_amount,
            "new_balance": str(user.balance),
            "streak": user.consecutive_logins
        })

# --- LEADERBOARD & INBOX ---
class LeaderboardView(generics.ListAPIView):
    serializer_class = LeaderboardSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return User.objects.filter(lifetime_deposit__gt=0).order_by('-lifetime_deposit')[:50]

from rest_framework import serializers

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'message', 'is_read', 'created_at')

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.is_read = True
            notif.save()
            return Response({"status": "success"})
        except Notification.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

# --- BANKER / ADMIN ENGINE ---
class BankerPlayerListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer
    def get_queryset(self):
        return User.objects.all().order_by('-lifetime_deposit')

class BankerPlayerToggleBanView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                return Response({"error": "Cannot ban an admin."}, status=status.HTTP_403_FORBIDDEN)
            user.is_active = not user.is_active
            user.save()
            state = "UNBANNED" if user.is_active else "BANNED"
            return Response({"message": f"User {state} successfully.", "is_active": user.is_active})
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)