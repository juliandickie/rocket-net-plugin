---
description: Create or restore a backup for a Rocket.net site (restore is destructive and confirms first).
---

# /rocket-backup

Create a manual backup or restore from a backup for a Rocket.net site.

Steps:
1. Identify the target site (ask if not given). Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` if you need to find it.
2. If listing backups, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup list <site_id>` and present the results (backup ID, date, type, size).
3. To create a backup, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup create <site_id> --wait` and report the outcome.
4. To restore a backup, this is destructive - it overwrites the current site. Present a scope review: which site, which backup, what will be overwritten. On explicit approval, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup restore <site_id> <backup_id> --yes --wait`.
5. Report the outcome clearly (success or any partial failure).
