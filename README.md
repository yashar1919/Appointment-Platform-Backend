# Appointment Platform Backend

Phase 1/2 modular monolith for multi-tenant appointment booking, SMS notifications, reminders, and protected administration.

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
# Set DATABASE_URL, DATABASE_SYNC_URL, and ADMIN_API_KEY in .env.
pip install -r requirements.txt
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE appointment_platform;"
& .\.venv\Scripts\python.exe -c "from alembic.config import CommandLine; CommandLine().main(['-c','alembic.ini','upgrade','head'])"
& .\.venv\Scripts\python.exe -m scripts.seed
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Admin API

```powershell
$headers = @{ "X-Admin-Key" = "the-value-from-.env" }
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8000/api/v1/admin/yasaman-raesi/services"
Invoke-RestMethod -Headers $headers -Uri "http://127.0.0.1:8000/api/v1/admin/yasaman-raesi/appointments?status=confirmed"
```

SMS credentials are optional for local development. Provider errors are stored as failed rows in `notification_logs` and do not fail bookings.
