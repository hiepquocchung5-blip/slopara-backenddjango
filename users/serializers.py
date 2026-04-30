from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from .utils import validate_and_identify_operator

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=50, required=False, validators=[RegexValidator(r'^[a-zA-Z0-9_]+$', message='Username must be alphanumeric.')])
    vip_tier = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'phone_number', 'username', 'is_profile_verified', 'balance', 'lifetime_deposit', 'vip_tier', 'last_daily_bonus_claim', 'consecutive_logins')
        read_only_fields = ('balance', 'lifetime_deposit', 'is_profile_verified', 'vip_tier', 'last_daily_bonus_claim', 'consecutive_logins')

    def get_vip_tier(self, obj):
        ltd = obj.lifetime_deposit
        if ltd >= 100000: return 'PLATINUM'
        if ltd >= 50000: return 'GOLD'
        if ltd >= 10000: return 'SILVER'
        return 'BRONZE'

class LeaderboardSerializer(serializers.ModelSerializer):
    vip_tier = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'display_name', 'lifetime_deposit', 'vip_tier')

    def get_vip_tier(self, obj):
        ltd = obj.lifetime_deposit
        if ltd >= 100000: return 'PLATINUM'
        if ltd >= 50000: return 'GOLD'
        if ltd >= 10000: return 'SILVER'
        return 'BRONZE'

    def get_display_name(self, obj):
        if obj.username: return obj.username
        return f"{obj.phone_number[:4]}****{obj.phone_number[-2:]}"

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    operator_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('phone_number', 'password', 'operator_info')

    def get_operator_info(self, obj):
        is_valid, data = validate_and_identify_operator(obj.phone_number)
        return data.get('operator') if is_valid else None

    def validate_phone_number(self, value):
        is_valid, result = validate_and_identify_operator(value)
        if not is_valid: raise serializers.ValidationError(result)
        normalized_phone = result['normalized']
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return normalized_phone

    def create(self, validated_data):
        return User.objects.create_user(phone_number=validated_data['phone_number'], password=validated_data['password'])