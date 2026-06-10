---
name: rocket-wp-cli
description: "Run WP-CLI commands on a Rocket.net site through the API. Use when the user wants to run wp commands (plugin updates, option get/set, search-replace, user management) on a hosted site. Distinguishes read from write and dry-runs destructive wp commands."
---

# WP-CLI on Rocket.net

Rocket.net exposes WP-CLI via the API. Commands run on the server without SSH access.

## Basic usage

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- <wp-cli args>
```

The `--` separator passes everything after it as the WP-CLI command string.

## Read-only examples (safe, no confirmation needed)

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- option get blogname
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- option get siteurl
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- plugin list
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- theme list
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- user list --fields=ID,user_login,user_email,roles
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- core version
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- cron event list
```

## Write commands - dry-run first

For any command that changes data, show the user a dry-run output first and confirm before executing.

Dry-run example for search-replace:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- search-replace 'http://old.com' 'https://new.com' --dry-run --all-tables
```

Then on confirmation:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- search-replace 'http://old.com' 'https://new.com' --all-tables
```

## Plugin and core updates

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- plugin update --all --dry-run
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- plugin update --all
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- core update
```

## User management

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- user create editor@example.com editor --role=editor
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- user update 1 --user_pass=newpass
```

## Underlying operationId

The CLI wpcli subcommand uses `app.controllers.wordpress_controller.sites_id_wpcli_post` (POST /v1/sites/{id}/wpcli). You can also call it directly:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.wordpress_controller.sites_id_wpcli_post --param id=<site_id> --data '{"command":"option get blogname"}'
```

## Safety summary

Read commands: run directly. Write or delete commands: dry-run first, confirm, then execute. Always prefer staging over production for destructive wp operations.
