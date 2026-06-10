---
name: rocket-site-lifecycle
description: "Create, clone, delete, lock, and transfer Rocket.net sites. Use when the user wants to provision a new site, duplicate one, remove one, lock a site, or transfer ownership. Covers async task polling for create and clone."
---

# Rocket.net site lifecycle

Covers the full lifecycle of a Rocket.net site from creation through deletion or transfer.

## Read before you change

Always fetch current state before any mutation:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites get <site_id>
```

## Create a site

Requires --name, --location (a numeric id), --admin-username, and --admin-email. The new site id is returned immediately; creation finishes in the background, so --wait is not used for create.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py site create --name "My Site" --location <id> --admin-username admin --admin-email you@example.com
```

Optional flags: --admin-password (auto-generated if omitted), --install-plugins a,b,c, --multisite, --template-id. List location ids (they are regions, e.g. Asia Pacific, United States, Europe):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_locations_get
```

## Clone a site

Clone is safe (non-destructive) and does not require --yes. It returns an async task; use --wait to poll until the clone finishes. The source site is LOCKED during a clone, so other operations on it return a 400 "site is currently locked" until it completes.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py site clone <site_id> --label "my-site-copy" --wait
```

## Update site metadata

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_id_patch --param id=<site_id> --data '{"name":"new-name"}'
```

## Lock and unlock a site

Locking prevents changes. Useful before a deploy or handover.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_id_lock_post --param id=<site_id>
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_id_lock_delete --param id=<site_id>
```

## Transfer a site

Transfer requires --yes. Present a scope review first: confirm target email, what access moves, and that the sender loses ownership.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.customer_site_transfers_controller.customer_site_transfers_post --param id=<site_id> --data '{"email":"recipient@example.com"}' --yes
```

## Delete a site

Destructive. Requires --yes. Confirm the site name and ID. Recommend a backup first.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py site delete <site_id> --yes
```

## View site tasks

All async operations produce tasks. Poll status here:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.sites_controller.sites_id_tasks_get --param id=<site_id>
```

## Safety summary

Operations requiring --yes: delete, transfer. Clone and create do NOT require --yes.
