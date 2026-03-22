# Website App

This is now a legacy Django app kept mainly for:

- migration history
- compatibility imports
- app continuity during the modular refactor

Active application code has moved to:

- `apps.public`
- `apps.appointments`
- `apps.patients`
- `apps.shared`

Real model ownership for appointment and patient code now lives in:

- `apps.appointments.models`
- `apps.patients.models`

Do not add new views, forms, templates, or business logic here unless the change is specifically about compatibility or migration safety.
