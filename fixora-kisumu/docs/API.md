# Fixora API surface

Base path: `/v1`

## Public
- `GET /healthz`
- `GET /technicians`

## Auth
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /me`

## Customer
- `POST /devices`
- `GET /devices`
- `POST /repair-requests`
- `GET /repair-requests`
- `GET /repair-requests/{request_id}/matches`
- `GET /repair-requests/{request_id}/quotes`
- `POST /quotes/{quote_id}/accept`
- `POST /repair-requests/{request_id}/payments/mpesa`
- `GET /repair-requests/{request_id}/payment`
- `GET /repair-requests/{request_id}/evidence`
- `GET /evidence/{evidence_id}/download`
- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`
- `GET /devices/{device_id}/passport`
- `POST /repair-requests/{request_id}/review`
- `POST /repair-requests/{request_id}/dispute`
- `PATCH /repair-requests/{request_id}/status` for final handover confirmation

## Technician
- `GET /repair-requests` — only matching open jobs and own assigned jobs
- `POST /repair-requests/{request_id}/claim`
- `POST /repair-requests/{request_id}/quotes`
- `POST /repair-requests/{request_id}/inspections`
- `POST /repair-requests/{request_id}/evidence`
- `GET /repair-requests/{request_id}/evidence`
- `GET /evidence/{evidence_id}/download`
- `PATCH /repair-requests/{request_id}/status`
- `GET /technicians/me`
- `PATCH /technicians/me`
- `POST /repair-requests/{request_id}/dispute`

## Admin / trust
- `GET /admin/technicians`
- `POST /admin/technicians/{technician_id}/credentials`
- `PATCH /admin/technicians/{technician_id}/approval`
- `GET /admin/disputes`
- `PATCH /admin/disputes/{dispute_id}`
- `GET /admin/payouts`
- `PATCH /admin/payouts/{payout_id}`

## Payment callback
- `POST /payments/mpesa/callback/{callback_token}`

All authenticated browser mutations use the CSRF double-submit token. Bearer-authenticated API clients do not need a CSRF header.
