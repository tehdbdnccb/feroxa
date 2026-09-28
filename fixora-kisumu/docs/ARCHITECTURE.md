# Architecture

## Boundaries
apps/web -> HTTP API -> application services -> repositories -> PostgreSQL

Payment integration is behind a gateway interface so business rules do not depend on Daraja SDK details.

## Domain objects
User, TechnicianProfile, Provider, Credential, Device, RepairRequest, Quote, RepairInspection, RepairJob, Warranty, PaymentIntent, RepairPassportEvent.

## Why this split
The marketplace's long-term moat is operational data: technician credentials, repair outcomes, device history, warranty claims and evidence. Those concepts belong to the domain and should not be encoded into UI components.

## Native mobile plan
Once the Kisumu operating model is validated, the customer and technician journeys can be extracted into Flutter 3.47+ clients while preserving the API and domain boundaries. Current Flutter documentation is at https://docs.flutter.dev/ and lists 3.47 as the Aug 2026 stable release.
