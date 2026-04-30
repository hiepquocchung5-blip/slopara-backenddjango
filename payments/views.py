from rest_framework import generics, parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import PaymentMethod, Transaction
from .serializers import PaymentMethodSerializer, DepositSerializer, WithdrawSerializer, TransactionSerializer
from users.models import User, Notification

class ActivePaymentMethodsView(generics.ListAPIView):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

class DepositCreateView(generics.CreateAPIView):
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)

class WithdrawCreateView(generics.CreateAPIView):
    serializer_class = WithdrawSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data['amount']
        user = User.objects.select_for_update().get(id=request.user.id)
        
        if user.balance < amount:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.balance -= amount
        user.save()
        
        serializer.save(user=user, tx_type='WITHDRAW', status='PENDING')
        return Response({"message": "Withdrawal requested successfully."}, status=status.HTTP_201_CREATED)

class TransactionHistoryView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-created_at')


class PaymentGatewayWebhookView(APIView):
    """
    Server-to-Server endpoint for Payment Providers (KBZPay, WaveMoney).
    Automatically approves deposits when the gateway confirms funds received.
    """
    permission_classes = [AllowAny] # Must be open for the gateway to reach it

    @transaction.atomic
    def post(self, request):
        # In production, verify the cryptographic signature of the provider here.
        # signature = request.headers.get('X-Provider-Signature')
        
        data = request.data
        txd_id = data.get('txd_id')
        status_code = data.get('status') # e.g., 'SUCCESS'
        
        if not txd_id or status_code != 'SUCCESS':
            return Response({"status": "ignored"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the pending transaction matching the Gateway's TXD ID
            tx = Transaction.objects.select_for_update().get(txd_id=txd_id, tx_type='DEPOSIT', status='PENDING')
            
            user = User.objects.select_for_update().get(id=tx.user.id)
            
            # Credit the user automatically
            user.balance += tx.amount
            user.lifetime_deposit += tx.amount
            user.save()
            
            tx.status = 'APPROVED'
            tx.save()

            title = 'Auto-Deposit Approved ⚡'
            msg = f'{tx.amount} MMK has been instantly credited to your balance via Payment Gateway.'
            Notification.objects.create(user=user, title=title, message=msg)

            # Fire real-time WebSocket push to the user's active session
            try:
                channel_layer = get_channel_layer()
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

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Transaction.DoesNotExist:
            return Response({"error": "Transaction not found or already processed"}, status=status.HTTP_404_NOT_FOUND)