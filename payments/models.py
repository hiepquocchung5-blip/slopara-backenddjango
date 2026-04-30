from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentMethod(models.Model):
    """
    Banker-controlled list of active deposit methods (e.g., KBZ Pay, Wave Money).
    """
    bank_name = models.CharField(max_length=50)
    bank_account = models.CharField(max_length=50)
    account_name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True, help_text="Instructions for the user")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        status = "🟢" if self.is_active else "🔴"
        return f"{status} {self.bank_name} - {self.account_name}"


class Transaction(models.Model):
    """
    Financial ledger for Deposits and Withdrawals.
    """
    TX_TYPES = (
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAW', 'Withdraw'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tx_type = models.CharField(max_length=10, choices=TX_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # Proof of transfer (Transaction ID from KBZ/Wave)
    txd_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Target bank for withdrawals
    user_bank_name = models.CharField(max_length=50, blank=True, null=True)
    user_bank_account = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} | {self.tx_type} | {self.amount} | {self.status}"