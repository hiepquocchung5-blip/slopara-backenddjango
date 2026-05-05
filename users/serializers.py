from rest_framework import serializers
from django.contrib.auth import get_user_model
from .utils import validate_and_identify_operator

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'phone_number', 'username', 'is_profile_verified', 
            'balance', 'lifetime_deposit', 'user_type', 
            'referral_code', 'commission_balance'
        )
        read_only_fields = ('balance', 'lifetime_deposit', 'is_profile_verified', 'user_type', 'referral_code', 'commission_balance')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    operator_info = serializers.SerializerMethodField(read_only=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('phone_number', 'password', 'referral_code', 'operator_info')

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
        ref_code = validated_data.pop('referral_code', None)
        referred_by = None
        
        # Lookup and validate the referrer if a code was provided
        if ref_code:
            referred_by = User.objects.filter(referral_code=ref_code).first()

        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            referred_by=referred_by
        )
        return user

class LeaderboardSerializer(serializers.ModelSerializer):
    vip_tier = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'display_name', 'lifetime_deposit', 'vip_tier')

    def get_vip_tier(self, obj):
        ltd = obj.lifetime_deposit
        if ltd >= 50000000: return 'IMMORTAL'
        if ltd >= 10000000: return 'MYTHICAL GLORY'
        if ltd >= 5000000: return 'MYTHIC'
        if ltd >= 1000000: return 'LEGEND'
        if ltd >= 500000: return 'EPIC'
        if ltd >= 100000: return 'GRANDMASTER'
        if ltd >= 50000: return 'MASTER'
        if ltd >= 10000: return 'ELITE'
        return 'WARRIOR'

    def get_display_name(self, obj):
        return obj.username if obj.username else f"User {obj.phone_number[:4]}****{obj.phone_number[-2:]}"