from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import PaymentMethod, Transaction

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ('id', 'bank_name', 'bank_account', 'account_name', 'notes')

class TransactionSerializer(serializers.ModelSerializer):
    payment_method_details = PaymentMethodSerializer(source='payment_method', read_only=True)

    class Meta:
        model = Transaction
        fields = ('id', 'amount', 'tx_type', 'txd_id', 'screenshot', 'status', 'created_at', 'payment_method_details')

class DepositSerializer(serializers.ModelSerializer):
    txd_id = serializers.CharField(
        validators=[RegexValidator(r'^\d{6}$', message='TXD ID must be exactly the last 6 digits.')],
        max_length=6,
        min_length=6
    )
    
    class Meta:
        model = Transaction
        fields = ('amount', 'txd_id', 'payment_method', 'screenshot')

    def validate_screenshot(self, value):
        if value and not '.' in value.name:
            value.name += '.jpg'
        return value

    def create(self, validated_data):
        validated_data['tx_type'] = 'DEPOSIT'
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class WithdrawSerializer(serializers.ModelSerializer):
    user_bank_name = serializers.CharField(required=True)
    user_account_name = serializers.CharField(required=True)
    user_bank_account = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    class Meta:
        model = Transaction
        fields = ('amount', 'user_bank_name', 'user_account_name', 'user_bank_account')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Withdrawal amount must be greater than 0.")
        return value