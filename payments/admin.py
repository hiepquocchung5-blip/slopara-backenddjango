from django.contrib import admin
from django.db import transaction
from django.contrib import messages
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from users.models import Notification
from .models import PaymentMethod, Transaction

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_name', 'bank_account', 'is_active')
    list_filter = ('is_active',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'tx_type', 'amount', 'txd_id', 'status', 'created_at')
    list_filter = ('status', 'tx_type')
    search_fields = ('user__phone_number', 'txd_id')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_transactions', 'reject_transactions']

    @transaction.atomic
    def approve_transactions(self, request, queryset):
        """Securely approves transactions (Both Deposits and Withdrawals)"""
        # CRITICAL FIX: Removed the tx_type='DEPOSIT' filter to allow withdrawal approvals
        pending_txs = queryset.filter(status='PENDING')
        channel_layer = get_channel_layer()
        
        count = 0
        for tx in pending_txs:
            user = tx.user.__class__.objects.select_for_update().get(id=tx.user.id)
            
            if tx.tx_type == 'DEPOSIT':
                user.balance += tx.amount
                user.lifetime_deposit += tx.amount
                title = 'Deposit Approved ✅'
                msg = f'{tx.amount} MMK has been added to your balance.'
            else:
                # For Withdrawals, balance was deducted at request time. Just notify.
                title = 'Withdrawal Processed 💸'
                msg = f'Your withdrawal of {tx.amount} MMK has been successfully transferred.'
            
            tx.status = 'APPROVED'
            tx.save()
            user.save()
            count += 1
            
            Notification.objects.create(user=user, title=title, message=msg)

            try:
                async_to_sync(channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'personal_notification',
                        'title': title,
                        'message': msg,
                        'new_balance': str(user.balance)
                    }
                )
            except Exception:
                pass
            
        self.message_user(request, f"Successfully approved {count} transactions.", messages.SUCCESS)
    approve_transactions.short_description = "Approve selected pending transactions"

    @transaction.atomic
    def reject_transactions(self, request, queryset):
        """Rejects transactions and handles withdrawal refunds."""
        pending_txs = queryset.filter(status='PENDING')
        channel_layer = get_channel_layer()
        
        count = 0
        for tx in pending_txs:
            if tx.tx_type == 'WITHDRAW':
                user = tx.user.__class__.objects.select_for_update().get(id=tx.user.id)
                user.balance += tx.amount
                user.save()

                title = 'Withdrawal Rejected ❌'
                msg = f'Your withdrawal request was rejected. {tx.amount} MMK has been refunded.'
                Notification.objects.create(user=user, title=title, message=msg)

                try:
                    async_to_sync(channel_layer.group_send)(
                        f'user_{user.id}',
                        {'type': 'personal_notification', 'title': title, 'message': msg, 'new_balance': str(user.balance)}
                    )
                except Exception:
                    pass

            tx.status = 'REJECTED'
            tx.save()
            count += 1

        self.message_user(request, f"Successfully rejected {count} transactions.", messages.WARNING)
    reject_transactions.short_description = "Reject selected pending transactions"