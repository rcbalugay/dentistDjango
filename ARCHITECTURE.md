# Architecture

## Overview

This project has been refactored into a modular monolith structure and will continue to be refined incrementally.

Active application code lives under `apps/`:

- `apps.public`
- `apps.appointments`
- `apps.patients`
- `apps.staff`
- `apps.shared`

Legacy Django apps still exist:

- `website`
- `dashboard`

Those legacy apps now mainly remain for migration history, legacy admin compatibility, and app continuity during the refactor.

## Module Responsibilities

### `apps.public`
Owns public-facing pages and contact flow.

Examples:
- home
- about
- services
- blog
- contact

### `apps.appointments`
Owns appointment booking and tracking behavior.

Examples:
- appointment forms
- booking rules
- tracking flow
- appointment templates
- appointment constants

### `apps.patients`
Owns patient lookup and patient record update/create logic.

Examples:
- patient selectors
- patient services

### `apps.staff`
Owns staff-only dashboard behavior.

Examples:
- dashboard views
- staff templates
- staff static assets
- dashboard services/utilities

### `apps.shared`
Owns cross-cutting helpers that are not business-domain specific.

Examples:
- context processors
- shared integrations
- common helper code

## Current Model Ownership

Model ownership has now been moved into the modular apps:

- `apps.appointments.models.Appointment`
- `apps.patients.models.Patient`

Legacy compatibility imports remain in `website.models` so older imports do not break immediately.

`dashboard.models` is still a legacy app module and has not been given any new model ownership.

## Dependency Rules

Use these rules when adding new code:

- `apps.public` may depend on `apps.appointments`, `apps.patients`, and `apps.shared`
- `apps.staff` may depend on `apps.appointments`, `apps.patients`, and `apps.shared`
- `apps.appointments` must not depend on `apps.public` or `apps.staff`
- `apps.patients` must not depend on `apps.public` or `apps.staff`
- `apps.shared` must not contain business rules

## Templates And Static Files

Module-owned templates and static files should live with the module:

- `apps/public/templates/public/...`
- `apps/appointments/templates/appointments/...`
- `apps/staff/templates/staff/...`

- `apps/staff/static/staff/...`

## Tests

Tests should live with the module they cover:

- `apps/appointments/tests/...`
- `apps/staff/tests/...`

Additional module test packages should be added as those modules gain direct test coverage.

## Phase Status

### Phase 1
Completed:

- create modular app structure
- move public code into `apps.public`
- move appointment code into `apps.appointments`
- move patient logic into `apps.patients`
- move staff views/services/templates/static into `apps.staff`
- move shared context processor into `apps.shared`
- move model ownership for `Appointment` and `Patient` into modular apps
- remove stale `website` content types and permissions for moved models

### Phase 2
Planned:

- clean legacy app boundaries further
- reduce confusion around `website` and `dashboard`
- keep enforcing module dependency rules

### Phase 3
Planned separately:

- evaluate further legacy app reduction
- decide whether `website` and `dashboard` can be slimmed down further
- plan future infrastructure changes, such as PostgreSQL migration, as separate projects

### Next Steps: Security and Performance Hardening
(Derived from backend review)

**Immediate Security Actions:**
- **Rotate Exposed Secrets:** Rotate `SECRET_KEY`, `WEATHERAPI_KEY`, and `GOOGLE_MAPS_API_KEY` due to `.env` exposure in Git history. Remove `.env` from tracking.
- **Secure Patient Documents:** Migrate `PatientDocument` storage from public `MEDIA_ROOT` to a private cloud bucket (e.g., S3 with signed URLs) or a protected view with `staff_only` access control.

**Performance Improvements:**
- **Cache Global Site Content:** Implement caching for `SiteContent` to prevent DB reads and writes on every public page load.
- **Paginate Staff Views:** Add date limits and pagination to dashboard queries (e.g., `upcoming` appointments and `get_latest_appointments()`) to prevent unbounded memory usage.
- **Optimize Queries:** Introduce `select_related` and `prefetch_related` to eliminate N+1 query patterns in staff views.

**Refactoring & Tech Debt:**
- **Normalize SiteContent:** Extract the 24 hardcoded `service_N_*` fields into a related `ClinicService` model.
- **Service Layer Expansion:** Move scheduling and conflict-resolution logic entirely out of `apps/appointments/views.py` into `apps/appointments/services.py`.
- **Remove Data Fixups from Views:** Move the string-replacement logic in `get_site_content()` into a Django data migration.
