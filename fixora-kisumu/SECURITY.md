# Security controls

## Authentication

Browser sessions use a short-lived JWT in a Secure/HttpOnly cookie with a separate CSRF token cookie. The API also accepts bearer tokens for non-browser clients.

Passwords are hashed with Argon2.

## Device privacy

Only the last four characters of IMEI/serial identifiers are stored by the MVP. Do not collect Apple Account passwords, device passcodes or private content as part of repair intake.

## Authorization

Technician job visibility is restricted to matching open jobs and jobs assigned to the technician. Quote submission requires assignment. Repair status transitions are enforced server-side.

Job claiming is implemented as an atomic conditional update to prevent double assignment races.

## Evidence

Evidence is validated by content type and size, hashed with SHA-256, and stored through a storage abstraction. Production should use a private S3-compatible bucket, signed downloads, malware/content scanning, retention rules and immutable audit logs.

## Payments

M-Pesa callback processing uses a configured random callback token and idempotent payment records keyed by the Daraja checkout request ID. Successful payments create a payout queue entry rather than automatically disbursing funds.

## Remaining production controls

- edge/API rate limiting
- bot/abuse controls
- centralized audit logging
- database backups and restore drills
- secret manager integration
- content scanning for uploaded evidence
- payment reconciliation
- background-check provider integration where required
