---
name: rocket-net
description: "Overview and router for managing Rocket.net WordPress hosting. Use when the user wants to manage Rocket.net sites, staging, deploys, backups, WP-CLI, domains, SSL, plugins, themes, caching, or hosting reporting. Explains when to use the bundled Rocket.net MCP versus the rocket CLI, and how credentials are set up."
---

# Rocket.net hosting

This plugin manages the Rocket.net HOSTING platform. It is not a WordPress content manager (use wp-index or wp-manager for content).

## Two tools, when to use each

- Bundled MCP (rocket-net server): conversational one-off actions. "Spin up a site", "what is using disk on site X".
- CLI `bin/rocket.py`: deterministic, scripted, bulk, or anything you must wait on. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py <command>`.

## Credentials

CLI reads ~/.config/rocket-net/config.json (username+password recommended, or api_token; tokens are 7-day JWTs). The MCP uses the plugin's userConfig (keychain). Never put credentials in the repo.

## Safety

Destructive actions (delete site, publish staging to production, restore, transfer) require --yes and a scope review. Always read current state before changing it. Never run live actions against production when a staging or test site is available.

## Common entry points

- /rocket-sites, /rocket-deploy, /rocket-stage, /rocket-backup, /rocket-wp
- Skills: rocket-site-lifecycle, rocket-staging-deploy, rocket-wp-cli, rocket-backups, rocket-fleet-ops, and surface skills for domains-ssl, plugins-themes, cache-cdn, reporting-waf, users-access, billing-account.
