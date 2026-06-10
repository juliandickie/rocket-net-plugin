---
name: rocket-backups
description: "Manage manual, automated, and cloud backups and restores on Rocket.net. Use when the user wants to take a backup, list backups, download one, or restore files or database. Confirms restore direction and target before acting."
---

# Rocket.net backups

Three backup types: manual (on-demand), automated (scheduled by Rocket.net), and cloud backups (stored externally).

## List manual backups

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup list <site_id>
```

## Create a manual backup

Non-destructive. Returns a task; use --wait to block until complete. A `--label` is required. By default both files and database are included; use `--no-files` or `--no-database` to exclude a part.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup create <site_id> --label "<label>" --wait
```

## Get a specific backup

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_backup_id_get --param id=<site_id> --param backup_id=<backup_id>
```

## Delete a manual backup

Requires --yes.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_backup_id_delete --param id=<site_id> --param backup_id=<backup_id> --yes
```

## Restore - scope review required

Before restoring, present a scope review:
- Which backup (ID, date, type)
- What will be overwritten (files, database, or both)
- Current site state
- Confirm target site ID

Restore full backup (files + database) - requires --yes. Use `--no-files` or `--no-database` to restore only one part:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup restore <site_id> <backup_id> --yes --wait
```

## Automated backups

List automated backups managed by Rocket.net:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_automated_get --param id=<site_id>
```

Restore database only from automated backup - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_automated_restore_id_restore_database_post --param id=<site_id> --param restore_id=<restore_id> --yes --wait
```

Restore files only from automated backup - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_automated_restore_id_restore_files_post --param id=<site_id> --param restore_id=<restore_id> --yes --wait
```

Restore both from automated backup - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.backups_controller.sites_id_backup_automated_restore_id_restore_post --param id=<site_id> --param restore_id=<restore_id> --yes --wait
```

## Cloud backups

List cloud backups:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.cloud_backups_controller.sites_id_cloud_backups_get --param id=<site_id>
```

Download a cloud backup:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.cloud_backups_controller.sites_id_cloud_backups_backup_id_download_get --param id=<site_id> --param backup_id=<backup_id>
```

Restore from cloud backup - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.cloud_backups_controller.sites_id_cloud_backups_backup_id_restore_post --param id=<site_id> --param backup_id=<backup_id> --yes --wait
```

## Safety summary

Create backup: safe. All restore operations: require --yes and a scope review. Delete backup: requires --yes.
