---
name: rocket-plugins-themes
description: "Install, search, and update WordPress plugins and themes via the Rocket.net API. Use when the user wants to manage plugins or themes on a hosted site at the hosting-platform level."
---

# WordPress plugins and themes on Rocket.net

Manage plugins and themes through the Rocket.net API. This is the hosting-platform layer; for WP-CLI-level operations see rocket-wp-cli.

## Plugins

List installed plugins:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py plugins list <site_id>
```

Or:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_get --param id=<site_id>
```

Search the plugin directory:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_search_get --param id=<site_id> --param search=<query>
```

List featured plugins:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_featured_plugins_get --param id=<site_id>
```

Install a plugin:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_post --param id=<site_id> --data '{"slug":"woocommerce"}'
```

Update a plugin:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_patch --param id=<site_id> --data '{"slug":"woocommerce"}'
```

Update all plugins (PUT):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_put --param id=<site_id>
```

Delete a plugin - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_delete --param id=<site_id> --data '{"slug":"old-plugin"}' --yes
```

## Rocket CDN cache management plugin settings

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.plugins_controller.sites_id_plugins_rocket_cdn_cache_management_post --param id=<site_id> --data '{}'
```

## Themes

List installed themes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py themes list <site_id>
```

Or:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_get --param id=<site_id>
```

Search the theme directory:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_search_get --param id=<site_id> --param search=<query>
```

Install a theme:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_post --param id=<site_id> --data '{"slug":"twentytwentyfive"}'
```

Update a theme:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_patch --param id=<site_id> --data '{"slug":"twentytwentyfive"}'
```

Update all themes (PUT):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_put --param id=<site_id>
```

Delete a theme - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.themes_controller.sites_id_themes_delete --param id=<site_id> --data '{"slug":"old-theme"}' --yes
```

## Safety summary

List and search: safe. Install and update: non-destructive. Delete plugin/theme: requires --yes. Always list before deleting to confirm the slug.
