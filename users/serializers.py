from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from .utils import validate_and_identify_operator
from .models import Notification

User = get_user_model()

# ==============================================================================
# AUTHENTICATION & SECURITY
# ==============================================================================
class SingleDeviceTokenSerializer(TokenObtainPairSerializer):
    """
    Stateful JWT Authentication:
    Rotates the user's security stamp BEFORE minting the token to instantly 
    invalidate all previously issued tokens on other devices.
    """
    @classmethod
    def get_token(cls, user):
        # 1. Rotate the stamp in the database
        user.security_stamp = uuid.uuid4()
        user.save(update_fields=['security_stamp'])
        
        # 2. Mint the new JWT token and embed the fresh stamp
        token = super().get_token(user)
        token['stamp'] = str(user.security_stamp)
        return token

    def validate(self, attrs):
        return super().validate(attrs)


# ==============================================================================
# REGISTRATION & PROFILE
# ==============================================================================
class RegisterSerializer(serializers.ModelSerializer):
    """Handles secure onboarding with telecom validation and referral mapping."""
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    operator_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('phone_number', 'password', 'referral_code', 'operator_info')

    def get_operator_info(self, obj):
        is_valid, data = validate_and_identify_operator(obj.phone_number)
        return data.get('operator') if is_valid else None

    def validate_phone_number(self, value):
        # Strip invisible whitespace
        value = value.strip()
        is_valid, result = validate_and_identify_operator(value)
        
        if not is_valid:
            raise serializers.ValidationError(result)
        
        normalized_phone = result['normalized']
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise serializers.ValidationError("This phone number is already registered.")
            
        return normalized_phone

    def create(self, validated_data):
        ref_code = validated_data.pop('referral_code', None)
        referred_by = None
        
        if ref_code:
            referred_by = User.objects.filter(referral_code=ref_code).first()

        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            referred_by=referred_by
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Full user profile for the authenticated device."""
    class Meta:
        model = User
        fields = (
            'id', 'phone_number', 'username', 'is_profile_verified', 
            'balance', 'lifetime_deposit', 'user_type', 'referral_code', 
            'commission_balance', 'consecutive_logins'
        )
        read_only_fields = (
            'balance', 'lifetime_deposit', 'is_profile_verified', 
            'user_type', 'referral_code', 'commission_balance', 
            'consecutive_logins'
        )


# ==============================================================================
# PUBLIC LEADERBOARD & SOCIAL
# ==============================================================================
class LeaderboardSerializer(serializers.ModelSerializer):
    """
    Publicly safe serializer for the Global VIP Leaderboard.
    Masks PII (Phone Numbers) and dynamically calculates VIP Tiers.
    """
    vip_tier = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'display_name', 'lifetime_deposit', 'vip_tier')

    def get_vip_tier(self, obj):
        ltd = obj.lifetime_deposit
        if ltd >= 50000000: return 'IMMORTAL'
        if ltd >= 10000000: return 'MYTHICAL GLORY'
        if ltd >= 5000000:  return 'MYTHIC'
        if ltd >= 1000000:  return 'LEGEND'
        if ltd >= 500000:   return 'EPIC'
        if ltd >= 100000:   return 'GRANDMASTER'
        if ltd >= 50000:    return 'MASTER'
        if ltd >= 10000:    return 'ELITE'
        return 'WARRIOR'

    def get_display_name(self, obj):
        # Return verified public username if it exists
        if obj.username:
            return obj.username
            
        # Privacy Masking: "0995****06"
        phone = obj.phone_number
        if len(phone) >= 8:
            return f"{phone[:4]}****{phone[-2:]}"
            
        return "Unknown Operator"


# ==============================================================================
# SYSTEM INBOX
# ==============================================================================
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'title', 'message', 'is_read', 'created_at')