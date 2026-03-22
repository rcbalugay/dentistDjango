# Dashboard App

This is now a legacy Django app kept mainly for:

- existing model ownership
- admin registration
- migrations
- URL compatibility wrapper

Active staff-facing application code has moved to:

- `apps.staff`

Do not add new views, templates, static assets, or business logic here unless the change is specifically about legacy model ownership or migration safety.
