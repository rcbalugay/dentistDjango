# Architecture

## Overview

This project is being refactored into a modular monolith.

Active application code lives under `apps/`:

- `apps.public`
- `apps.appointments`
- `apps.patients`
- `apps.staff`
- `apps.shared`

Legacy Django apps still exist:

- `website`
- `dashboard`

For now, those legacy apps mainly remain to preserve model ownership, admin registration, and migrations.

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

Models have not been moved yet.

Current model ownership remains in legacy apps:

- `website.models`
- `dashboard.models`

This is intentional to avoid risky migration churn during Phase 1.

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

## Phase Status

### Phase 1
Completed or in progress:

- create modular app structure
- move public code into `apps.public`
- move appointment code into `apps.appointments`
- move patient logic into `apps.patients`
- move staff views/services/templates/static into `apps.staff`
- move shared context processor into `apps.shared`

### Phase 2
Planned:

- clean legacy app boundaries further
- reduce confusion around `website` and `dashboard`
- keep enforcing module dependency rules

### Phase 3
Planned separately:

- evaluate moving models out of legacy apps
- plan migrations carefully before changing model ownership
