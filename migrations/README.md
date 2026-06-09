# Database Migrations

This directory contains the SQL Data Definition Language (DDL) and migration scripts required to bootstrap the persistent storage layer for the Svaani platform.

## Persistent Stores

Currently, the primary persistent SQL store is used for the **Patient Consent Module** to ensure strict adherence to HIPAA and DPDPA auditability and durability requirements.

## Applying Migrations

At present, migrations are structured as raw SQL scripts.

### Local Development
In a local Docker Compose environment, these scripts can be mounted directly into the Postgres initialization directory (`/docker-entrypoint-initdb.d/`) or executed manually via `psql`:

```bash
psql -h localhost -U postgres -d svaani_db -f 001_create_consents.sql
```

### Production Environments
For staging and production, it is highly recommended to integrate these scripts with a formal schema migration tool such as [golang-migrate](https://github.com/golang-migrate/migrate) or [Flyway](https://flywaydb.org/). This will allow version-controlled, automated, and roll-back capable schema updates during CI/CD pipeline deployments.

## Best Practices
- **Never modify existing migrations**: If a schema change is required (e.g., adding a column), create a *new* migration file (e.g., `002_add_consent_metadata.sql`).
- **Idempotency**: Whenever possible, write idempotent SQL using `IF NOT EXISTS` constructs.
- **Indexes**: Ensure appropriate indexes are created for columns frequently queried (e.g., `patient_id`, `status`).
