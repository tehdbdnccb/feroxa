# Fixora — Kisumu Repair Network

Fixora is a production-oriented trust and workflow platform for Apple-device repair in Kisumu, Kenya. The customer experience is intentionally simple: describe the problem, see a structured repair workflow, approve the quote, track the work, pay by M-Pesa, and keep the repair in a persistent Repair Passport.

## What is in this build

### Customer
- Customer registration/login with browser session cookies + CSRF protection.
- iPhone/iPad device registration using last-four identifiers only.
- Repair request creation with service mode and optional browser geolocation.
- Ranked verified-technician matching by proximity, rating, experience and service radius.
- Quote review and explicit customer acceptance.
- In-app notifications.
- M-Pesa STK Push integration and callback processing.
- Payment-aware handover confirmation.
- Repair Passport timeline.
- Post-completion review and repair dispute workflow.

### Technician
- Technician registration/login.
- Admin-controlled network approval.
- Identity/business/Apple credential verification states.
- Location + service radius profile.
- Online/offline availability.
- Atomic job claiming to avoid double assignment.
- Quote submission with one quote enforced per repair.
- Strict repair status machine.
- Pre/post inspection checklist.
- Repair evidence upload with SHA-256 digest and private storage abstraction.
- Payout queue generation after successful customer payment.

### Trust / Admin
- Technician approval and suspension.
- Credential verification records with expiry support.
- Dispute queue and resolution.
- Technician payout queue with manual paid/held states.

## Stack
- Web: Next.js 16.3.3 + React 19.3.0 + TypeScript + responsive PWA UI.
- API: FastAPI 0.141.1 + SQLAlchemy 2.0.54 + Alembic 1.20.0.
- Database: PostgreSQL in production, SQLite for tests/local quick-start.
- Auth: JWT session token in Secure/HttpOnly cookie for browser clients, CSRF double-submit cookie, Argon2 password hashing. Bearer authentication remains available for API/mobile clients.
- Payments: M-Pesa Daraja STK Push adapter.
- Evidence: local storage for development, S3-compatible private object storage in production.
- Infra: Docker Compose for PostgreSQL/Redis; GitHub Actions CI.

The dependency choices were refreshed against the official release channels available on September 17, 2026: Next.js 16.3.3 is in the Active LTS line, React 19.3.0 was released September 9, 2026, FastAPI 0.141.1 is the latest release shown in the official release notes, SQLAlchemy 2.0.54 is current, and Alembic 1.20.0 was released September 11, 2026.

## Local API

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Local web

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

The web client expects `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## Local infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Production database

Run migrations explicitly:

```bash
cd services/api
alembic upgrade head
```

Do not use application startup schema creation in production.

## Bootstrap administrator

Set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`, then run:

```bash
python -m app.cli bootstrap-admin
```

Remove the bootstrap environment variables after the account exists.

## M-Pesa production configuration

Set the Daraja consumer key/secret, shortcode, passkey, a public HTTPS callback URL and a long random callback token. The callback route is:

```text
POST /v1/payments/mpesa/callback/{MPESA_CALLBACK_TOKEN}
```

## Evidence storage

For production, configure the S3-compatible variables in `services/api/.env.example`. Keep the bucket private and expose evidence only through authenticated, short-lived download links.

## Tests / validation

```bash
cd services/api
pytest -q
python -m compileall app tests
alembic upgrade head
```

The current local validation passes 6 API tests, Python compilation, and migrations through the current head revision. The web source is syntax-transpiled across 14 TypeScript/TSX files in this environment; a full `next build` requires installing the npm dependency graph from the registry.

## No seed data

There is intentionally no production seed/demo data. The pilot should be populated with real technicians that have been verified by the trust operator.
