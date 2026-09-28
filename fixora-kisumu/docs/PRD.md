# PRD — Fixora Kisumu MVP

## Product goal
Make booking a trusted Apple-device repair in Kisumu feel as simple and accountable as booking a ride.

## Personas
### Customer
Owns an iPhone/iPad, needs a repair, cares about price, privacy, technician quality and convenience.

### Technician
Independent repair professional or service provider who wants qualified demand, standardized workflows and faster payment.

### Admin / Trust operator
Verifies credentials, reviews disputes, manages service catalog and monitors quality.

## MVP use cases
### UC1 — Customer creates repair request
Device -> issue -> service mode -> address -> notes.

### UC2 — Technician sees available work
Available jobs -> quote -> accept -> status transitions.

### UC3 — Repair authorization
Technician submits a quote. Customer must explicitly accept before the job moves to authorized.

### UC4 — Inspection evidence
Technician records device condition before and after the repair.

### UC5 — Completion + warranty
Customer marks the repair complete. The API creates the warranty record and Repair Passport event.

## Non-goals for MVP
- automatic visual diagnosis;
- multi-country expansion;
- native iOS/Android release;
- Apple warranty adjudication;
- automated background-check provider integration;
- full parts supplier marketplace.

## Core metrics
- time to first technician acceptance;
- technician acceptance rate;
- quote acceptance rate;
- repair completion rate;
- repeat/referral rate;
- warranty claim rate;
- contribution margin per repair;
- NPS/CSAT (later).

## Acceptance criteria
- No repair can be completed without a recorded pre-repair inspection.
- No chargeable repair can move from quoted to authorized without customer acceptance.
- Technician certification claims are represented as verification states, never free-text trust claims.
- Passwords are hashed with Argon2id.
- API enforces role access.
- CORS is allow-list based.
- No production secrets are committed.
