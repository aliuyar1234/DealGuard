# Backup and Restore Runbook

This runbook covers automated backups for Postgres and MinIO and the restore workflow for production Compose.

## Backup Overview
- Postgres backups are written to `pg_backups` (volume) by `pg-backup`.
- MinIO backups are mirrored to `minio_backups` (volume) by `minio-backup` when the `minio` profile is enabled.

### Scheduling and Retention
- Postgres: `PG_BACKUP_INTERVAL_SECONDS`, `PG_BACKUP_RETENTION_DAYS`
- MinIO: `MINIO_BACKUP_INTERVAL_SECONDS`, `MINIO_BACKUP_RETENTION_DAYS`

## Restore: Postgres
1. Stop write traffic:
   - `docker compose -f docker-compose.prod.yml stop backend worker`
2. Pick a backup file:
   - `docker compose -f docker-compose.prod.yml exec pg-backup ls -1 /backups`
3. Restore into the database (drops/replaces objects):
   - `docker compose -f docker-compose.prod.yml exec postgres sh -c "pg_restore --clean --if-exists -U $DB_USER -d $DB_NAME /backups/pg_<db>_<timestamp>.dump"`
4. Bring services back:
   - `docker compose -f docker-compose.prod.yml start backend worker`

## Restore: MinIO (self-hosted)
1. Stop backend writes:
   - `docker compose -f docker-compose.prod.yml stop backend worker`
2. Mirror backup back into the bucket:
   - `docker compose -f docker-compose.prod.yml exec minio-backup sh -c "mc alias set restore $S3_ENDPOINT $S3_ACCESS_KEY $S3_SECRET_KEY && mc mirror --overwrite /backups/$S3_BUCKET/<timestamp> restore/$S3_BUCKET"`
3. Start backend:
   - `docker compose -f docker-compose.prod.yml start backend worker`

## Validation
- Postgres: `docker compose -f docker-compose.prod.yml exec postgres psql -U $DB_USER -d $DB_NAME -c "SELECT 1;"`
- MinIO: `docker compose -f docker-compose.prod.yml exec minio-backup mc ls backup/$S3_BUCKET`

## Notes
- Backups are only as durable as the volume; copy `pg_backups` and `minio_backups` off-host for true disaster recovery.
- For managed Postgres/S3, use provider-native PITR and object lifecycle policies instead of local backups.
