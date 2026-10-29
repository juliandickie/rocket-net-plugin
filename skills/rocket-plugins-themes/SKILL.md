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
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins list <site_id>
```

Search the WordPress plugin directory:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins search <site_id> --query woocommerce
```

Install one or more plugins, optionally activating:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins install <site_id> --plugins woocommerce,wordfence --activate
```

Install from a custom zip URL:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins install <site_id> --plugins my-plugin --custom-url https://example.com/my-plugin.zip
```

Update a plugin:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins update <site_id> --plugin woocommerce
```

Activate or deactivate a plugin:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins set-status <site_id> --plugin woocommerce --status inactive
```

Delete plugins - requires --yes:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" plugins delete <site_id> --plugins old-plugin --yes
```

## Themes

List installed themes:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes list <site_id>
```

Search the theme directory:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes search <site_id> --query astra
```

Install one or more themes, optionally activating:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes install <site_id> --themes twentytwentyfive --activate
```

Update a theme:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes update <site_id> --theme twentytwentyfive
```

Activate a theme:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes set-status <site_id> --theme twentytwentyfive --status active
```

Delete themes - requires --yes:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" themes delete <site_id> --themes old-theme --yes
```

## Without a subcommand (generic call)

Featured plugins list:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.plugins_controller.sites_id_featured_plugins_get --param id=<site_id>
```

Update ALL plugins or ALL themes in one call:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.plugins_controller.sites_id_plugins_put --param id=<site_id>
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.themes_controller.sites_id_themes_put --param id=<site_id>
```

Rocket CDN cache management plugin settings:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.plugins_controller.sites_id_plugins_rocket_cdn_cache_management_post --param id=<site_id> --data '{}'
```

## Safety summary

List and search: safe. Install, update, set-status: non-destructive but change the live site. Delete: requires --yes. Always list before deleting to confirm the slug.
