# Operations

## Local

```bash
cd services/api
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

SQLite is used for local development and test runs.

## Production database

Use PostgreSQL and apply migrations explicitly:

```bash
alembic upgrade head
```

Do not rely on application startup for schema creation in production.

## Bootstrap an administrator

Set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`, then run:

```bash
python -m app.cli bootstrap-admin
```

Remove those bootstrap variables immediately after provisioning.

## Technician onboarding

1. Technician creates an account.
2. Trust operator verifies identity.
3. Trust operator verifies business relationship/ownership.
4. Optional Apple credential/provider status is recorded separately.
5. Trust operator approves network access.
6. Technician adds a Kisumu operating location and service radius.
7. Technician can then go online.

A technician cannot become available solely by self-declaring an Apple certification.

## Evidence storage

For development, evidence is stored below `MEDIA_ROOT`.

For production, configure a private S3-compatible bucket with:

- `STORAGE_BUCKET`
- `STORAGE_REGION`
- `STORAGE_ENDPOINT_URL` when using R2/MinIO/another S3-compatible service
- `STORAGE_ACCESS_KEY_ID`
- `STORAGE_SECRET_ACCESS_KEY`

The API stores object metadata and SHA-256, and authenticated downloads use short-lived signed URLs when object storage is configured.

## M-Pesa

Set the Daraja environment and credentials. The callback URL must be publicly reachable over HTTPS and should include the configured random callback token:

```text
https://api.example.com/v1/payments/mpesa/callback/<random-token>
```

Customer payment is accepted only after a successful callback. A successful payment queues a technician payout record; automated B2C payout is intentionally not enabled in this pilot release.

## Production hardening still required before broad public launch

- Managed edge/API rate limiting and bot protection.
- Centralized logs, alerting and audit retention.
- Private object storage with malware/content scanning.
- Database backups and recovery drills.
- Secrets in a managed secret store.
- Payment reconciliation against Daraja records.
- Automated technician background-check provider integration where required.
- Automated technician B2C payout after finance controls are approved.
- Legal/privacy review for retention periods and dispute handling.
