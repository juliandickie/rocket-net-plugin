---
name: rocket-staging-deploy
description: "Manage Rocket.net staging environments and publish staging to production. Use when the user wants to create or refresh a staging site, preview changes, or deploy staging to live. Always runs a scope review before publishing."
---

# Rocket.net staging and deploy

Staging is a full copy of the production site isolated from live traffic. Publishing pushes staging over production - this is irreversible without a restore.

## Read current state first

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites get <site_id>
```

Check whether staging already exists before creating it.

## Create staging

Non-destructive. Returns an async task.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py staging create <site_id> --wait
```

## Delete staging

Removes the staging environment (not production). Requires --yes.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_id_staging_delete --param id=<site_id> --yes
```

## Scope review before publishing

Before running publish, present a scope review containing:

- Site ID and name
- What staging contains (last push or fresh clone date if known)
- Last backup taken and when
- Confirmation that the user wants to overwrite production

Recommend taking a backup before publishing:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py backup create <site_id> --wait
```

## Publish staging to production

Destructive - overwrites production. Requires --yes and explicit user approval after scope review.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py staging publish <site_id> --yes --wait
```

## After publishing

Purge cache to ensure visitors see the new version:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py cache purge <site_id>
```

Verify the site responds and report the outcome.

## Safety summary

`staging create` is safe. `staging publish` and `staging delete` require --yes. Never publish without completing the scope review.
