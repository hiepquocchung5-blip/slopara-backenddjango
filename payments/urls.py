from django.urls import path
from .views import (
    ActivePaymentMethodsView, 
    DepositCreateView, 
    TransactionHistoryView,
    WithdrawCreateView,
    PaymentGatewayWebhookView,
    # BankerTransactionListView,       # NEW
    # BankerTransactionActionView      # NEW
)

urlpatterns = [
    # User Routes
    path('methods/', ActivePaymentMethodsView.as_view(), name='payment_methods'),
    path('deposit/', DepositCreateView.as_view(), name='create_deposit'),
    path('withdraw/', WithdrawCreateView.as_view(), name='create_withdraw'),
    path('history/', TransactionHistoryView.as_view(), name='transaction_history'),

    # Server-to-Server Webhooks
    path('webhook/gateway/callback/', PaymentGatewayWebhookView.as_view(), name='gateway_webhook'),
    
    # Banker / Admin Routes
    # path('admin/transactions/', BankerTransactionListView.as_view(), name='admin_transactions'),
    # path('admin/transactions/<int:tx_id>/<str:action>/', BankerTransactionActionView.as_view(), name='admin_tx_action'),
]