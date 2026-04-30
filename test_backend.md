Backend API & Admin Testing Guide

Before building the frontend, verify the Django backend is fully operational.

1. Initialize and Create Superuser

Ensure your virtual environment is active, then run:

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
# Enter a valid Myanmar phone number (e.g., 09791234567) and a password.


2. Configure the Django Admin

Start the server:

python manage.py runserver 0.0.0.0:8000


Open http://localhost:8000/admin/ in your browser and log in.

A. Setup Payment Methods

Go to Payments > Payment methods.

Click Add payment method.

Add a test bank (e.g., Bank Name: KPay, Bank Account: 09791234567, Account Name: Slopara Admin). Save it.

B. Setup Game Islands & GJP Pools

Go to Game > Islands. Click Add island.

Create Kyoto: Min Lifetime Deposit: 10000, Total Machines: 900. Save it.

Go to Game > GJP_Pools. Click Add gjp pool.

Link it to Kyoto. Set Current Value: 50000, Base Seed: 50000, Hot Trigger: 80000, Must Hit Value: 100000, Contribution Rate: 0.0100 (1%).

3. Test API Endpoints (via Postman or cURL)

A. Register a User

curl -X POST http://localhost:8000/api/users/register/ \
-H "Content-Type: application/json" \
-d '{"phone_number": "09441234567", "password": "securepassword123"}'


Expected: 201 Created with operator info (e.g., MPT).

B. Login (Get JWT Tokens)

curl -X POST http://localhost:8000/api/users/login/ \
-H "Content-Type: application/json" \
-d '{"phone_number": "09441234567", "password": "securepassword123"}'


Expected: 200 OK with access and refresh tokens.

C. Create a Deposit (Requires Auth)

Replace YOUR_ACCESS_TOKEN with the token from Step B.

curl -X POST http://localhost:8000/api/payments/deposit/ \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-F "amount=10000" \
-F "txd_id=123456" \
-F "payment_method=1"


D. Admin Approval Test

Go back to the Django Admin -> Payments > Transactions.

Select the Pending deposit you just created.

From the "Action" dropdown, select Approve selected pending deposits and click Go.

Verify the User's balance has increased by 10000 in the Users table.