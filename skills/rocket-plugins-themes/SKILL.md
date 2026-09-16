---
name: rocket-plugins-themes
description: "Install, search, and update WordPress plugins and themes via the Rocket.net API. Use when the user wants to manage plugins or themes on a hosted site at the hosting-platform level."
---

# WordPress plugins and themes on Rocket.net

Manage plugins and themes through the Rocket.net API. This is the hosting-platform layer; for WP-CLI-level operations see rocket-wp-cli. Every operation has a subcommand except the two noted at the end. Global flags (`--json`, `--yes`) go AFTER the subcommand.

Slugs for install and delete are a comma-separated string, because that is what the API expects (not a JSON array).

## Plugins

List installed plugins:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins list <site_id>
```

Search the WordPress plugin directory:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins search <site_id> --query woocommerce
```

Install one or more plugins, optionally activating:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins install <site_id> --plugins woocommerce,wordfence --activate
```

Install from a custom zip URL:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins install <site_id> --plugins my-plugin --custom-url https://example.com/my-plugin.zip
```

Update a plugin:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins update <site_id> --plugin woocommerce
```

Activate or deactivate a plugin:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins set-status <site_id> --plugin woocommerce --status inactive
```

Delete plugins - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins delete <site_id> --plugins old-plugin --yes
```

## Themes

List installed themes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes list <site_id>
```

Search the theme directory:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes search <site_id> --query astra
```

Install one or more themes, optionally activating:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes install <site_id> --themes twentytwentyfive --activate
```

Update a theme:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes update <site_id> --theme twentytwentyfive
```

Activate a theme:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes set-status <site_id> --theme twentytwentyfive --status active
```

Delete themes - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes delete <site_id> --themes old-theme --yes
```

## Without a subcommand (generic call)

Featured plugins list:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_featured_plugins_get --param id=<site_id>
```

Update ALL plugins or ALL themes in one call:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_put --param id=<site_id>
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_put --param id=<site_id>
```

Rocket CDN cache management plugin settings:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_rocket_cdn_cache_management_post --param id=<site_id> --data '{}'
```

## Safety summary

List and search: safe. Install, update, set-status: non-destructive but change the live site. Delete: requires --yes. Always list before deleting to confirm the slug.
