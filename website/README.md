# Website App

This is now a legacy Django app kept mainly for:

- existing model ownership
- admin registration
- migrations

Active application code has moved to:

- `apps.public`
- `apps.appointments`
- `apps.patients`
- `apps.shared`

Do not add new views, forms, templates, or business logic here unless the change is specifically about legacy model ownership or migration safety.
