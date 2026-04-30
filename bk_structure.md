Slopara Backend Directory Structure

slopara-backend/
├── manage.py                   # Django CLI entry point
├── db.sqlite3                  # Local database (swap to PostgreSQL for prod)
├── media/                      # Uploaded media files (ignored in git)
│   └── receipts/               # Deposit screenshots uploaded by users
├── config/                     # Main project configuration
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py             # Global settings (Apps, JWT, Media, DB)
│   ├── urls.py                 # Root URL routing
│   └── wsgi.py
├── users/                      # Authentication & Profile Management App
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py               # Custom User model (phone_number, balances)
│   ├── serializers.py          # Registration & Profile serializers
│   ├── urls.py
│   ├── utils.py                # Myanmar Telecom regex validation logic
│   └── views.py                # Auth endpoints
├── game/                       # Core Slot Game Engine App
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py               # Island, GJP_Pool, SpinHistory
│   ├── serializers.py
│   ├── urls.py
│   ├── utils.py                # Transactional RTP & Spin Matrix logic
│   └── views.py                # Spin endpoints
└── payments/                   # Financial Transactions App
    ├── __init__.py
    ├── admin.py                # Secure Deposit Approval/Rejection panel
    ├── apps.py
    ├── models.py               # PaymentMethod, Transaction (Deposits)
    ├── serializers.py          # TXD validation and file upload handling
    ├── urls.py
    └── views.py                # Deposit request endpoints
