# rocket-net

A Claude Code plugin to manage Rocket.net WordPress hosting two ways - conversationally through Rocket.net's bundled MCP server, and deterministically through a zero-dependency Python CLI. Skills and commands add the workflow knowledge on top.

Status - v0.1.1. Build complete and validated (34 unit tests, `claude plugin validate --strict`). Live-tested end to end against the real API - the full lifecycle (site create, clone, staging create and publish, WP-CLI, cache purge, backup create / restore / delete, site delete) is confirmed working, validated by spinning up a throwaway site, exercising every operation on it and its clone, then deleting both. The bundled MCP is live-verified through Claude Code's own client (headersHelper ran, Bearer accepted, tool calls returned real data).

Continuing development, or running on another machine? Read DEVELOPMENT.md first - it captures the live-API gotchas (Cloudflare user-agent, response envelope, task polling, which POST endpoints need bodies) and machine setup.

## What is in the box

- A bundled MCP server (`.mcp.json`) pointing at Rocket.net's hosted MCP at `https://mcp.rocket.net/mcp`. Best for conversational, one-off actions.

- A CLI at `bin/rocket.py` (Python 3 standard library only). Best for scripted, bulk, and async work, and for anything you must wait on. Reaches all 198 API operations.

- 12 skills and 5 commands that encode how to run common workflows safely.

This plugin manages the Rocket.net HOSTING platform. It is not a WordPress content manager. For content and WordPress-REST work, use a separate tool. The bridge between the two is the WP-CLI passthrough (`rocket wpcli`).

## Credentials

One credential file feeds both tools.

- CLI - create `~/.config/rocket-net/config.json` (chmod 600) with either Rocket.net `username` and `password` (recommended, the CLI auto-mints and refreshes the token) or a manual `api_token`. See `.env.example`. Note - Rocket.net has no permanent API key; tokens are JWTs that expire after 7 days, which is why username and password is the low-maintenance choice.

- MCP - the bundled server needs an `Authorization: Bearer <JWT>` header on every call. The plugin supplies it through Claude Code's `headersHelper`, which runs `rocket.py mcp-headers` on each connection (and again after any 401). That command reads the SAME config file as the CLI, so there is one credential store, and it refreshes the token when under 24 hours remain.

Note - Rocket.net sits behind Cloudflare, which blocks the default Python user-agent (error 1010). The CLI sends its own `rocket-net-cli/0.1.0` User-Agent so requests pass; override it with the `ROCKET_USER_AGENT` env var if needed. Two-factor authentication on your account does not block the API login (2FA gates only the web dashboard).

## Team setup guide

Read this if someone has asked you to install the plugin so you can work on the team's Rocket.net sites.

### Which credentials it uses

The plugin logs in with the same email and password you use at the Rocket.net web dashboard. There is no separate API key to create or copy from a settings page. Rocket.net has no permanent API keys at all; the API issues a 7-day token from a login call, and the plugin mints and refreshes that token on its own, which is why it asks for your login rather than a token.

Two things to know about that login.

- Two-factor authentication does not get in the way. If your account has 2FA on, the web dashboard asks for the code but the plugin does not, because the API login does not enforce it.
- Changing your dashboard password breaks the plugin until you update the config file described below. Both the CLI and the bundled MCP read that one file.

### Get a login

Ask the account owner to invite you as a user on the Rocket.net account, or to the specific sites you work on, from the dashboard. Use your own login where you can. The plugin acts with whatever permissions your user has, so a collaborator with a limited role gets a limited plugin. A shared owner login gives everyone full account power, including site delete, and the only brake at that point is the `--yes` guard on destructive commands.

### Install the plugin

Add the marketplace, then install.

```bash
claude plugin marketplace add juliandickie/outfit
```

```bash
claude plugin install rocket-net@outfit
```

Nothing prompts for a login. Both the bundled MCP server and the CLI read the config file created in the next step, so that step is required.

### Create the config file (required)

Replace the two values and run:

```bash
mkdir -p ~/.config/rocket-net && printf '{"username":"you@example.com","password":"YOUR_PASSWORD","base_url":"https://api.rocket.net"}\n' > ~/.config/rocket-net/config.json && chmod 600 ~/.config/rocket-net/config.json
```

The chmod step matters. It makes the file readable only by your user. Claude Code mints a 7-day API token from this login when it connects the MCP server, and the CLI does the same on its first call. The token is cached at `~/.config/rocket-net/.token`, also chmod 600.

### Check it works

List the sites your login can see. This is read-only.

```bash
python3 ~/.claude/plugins/cache/outfit/rocket-net/*/bin/rocket.py sites list
```

If it returns your sites, you are done. If it returns a 401, the email or password is wrong. If it returns a Cloudflare error 1010, something has overridden the CLI's User-Agent; unset `ROCKET_USER_AGENT` and try again.

### When your password changes

Update the config file above with the new password and delete `~/.config/rocket-net/.token`. The next MCP connection or CLI call logs in again.

## The two tools, when to use each

| Task | Use |
|---|---|
| Conversational one-off action | the bundled MCP |
| Scripted, repeatable, or scheduled | the CLI |
| Bulk or fleet operation | the CLI, parallelized |
| Long-running task you must wait on | the CLI with `--wait` |
| Large list or report (keep it out of context) | the CLI with `--json` to a file |

## CLI usage

Run it as `python3 bin/rocket.py <command>` (or `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py` inside the plugin).

Ergonomic subcommands (run any with `--help`) - `sites list|get`, `site create|clone|delete`, `staging create|publish`, `wpcli`, `backup list|create|restore|get|delete|automated|cloud-list`, `cache purge|purge-files`, `domains list|add|remove`, `ssl list|get|upload|delete`, `plugins list|install|update|set-status|delete|search`, `themes list|install|update|set-status|delete|search`, `users list|add|remove`, `ssh list|add|remove|authorize|deauthorize`, `ftp list|add|update|remove`, `settings get|schema|update`, `reporting bandwidth|visitors|requests`, `pwprotect status|enable|disable|users|add-user|remove-user`, `credentials`, `access-logs`, `maindomain get|status`, `account me|usage`.

Notes - `cache purge` clears the entire cache, `cache purge-files` purges specific URLs. `backup create` requires `--label`. `site create` requires `--name`, `--location`, `--admin-username`, and `--admin-email`. `reporting visitors|requests` take `--duration` (30m, 1h, 6h, 12h, 24h, 72h, 7d, 30d; default 7d). A handful of niche endpoints (file manager, edge settings, activity log, billing, WAF detail reports) remain available via the generic `call`.

Generic escape hatch (reaches all 198 operations) - `rocket call <operationId> --param key=value --data '{...}'`.

Global flags go AFTER the subcommand - `--wait` (poll the resulting task to completion), `--yes` (confirm a destructive op), `--json` (raw JSON output), `--dry-run` (print the request, send nothing), `--timeout <s>`, `--config <path>`.

Examples.

```
python3 bin/rocket.py sites list
python3 bin/rocket.py wpcli 12345 -- option get blogname
python3 bin/rocket.py cache purge 12345
python3 bin/rocket.py backup create 12345 --label nightly --wait
python3 bin/rocket.py staging publish 12345 --yes --wait
python3 bin/rocket.py call <operationId> --param id=12345 --data '{...}' --wait
```

## Safety model

Only genuinely destructive or irreversible operations require `--yes` - delete, restore, publish staging to production, transfer, reset, deauthorize, cancel. Additive and safe operations (clone, cache purge, create) run without a prompt, so a confirmation always means something. The workflow skills present a scope review before any destructive or batched action, and read current state before changing it.

## Skills and commands

Skills (auto-triggered by task context) - `rocket-net` (router and overview), `rocket-site-lifecycle`, `rocket-staging-deploy`, `rocket-wp-cli`, `rocket-backups`, `rocket-fleet-ops`, `rocket-domains-ssl`, `rocket-plugins-themes`, `rocket-cache-cdn`, `rocket-reporting-waf`, `rocket-users-access`, `rocket-billing-account`.

Commands - `/rocket-sites`, `/rocket-deploy`, `/rocket-stage`, `/rocket-backup`, `/rocket-wp`.

## Updating the endpoint map

The CLI loads `bin/rocket_endpoints.json`, generated from `reference/rocket-openapi.yaml`. If the spec changes, regenerate it.

```
python3 scripts/build_endpoints.py
```

PyYAML is needed only for this build step. The shipped CLI never imports it.

## Testing

- Unit tests (offline, no network) - `python3 -m unittest tests.test_rocket -v`.

- Live smoke test (against a throwaway or staging site only, never production) - set credentials in `~/.config/rocket-net/config.json`, then `ROCKET_SMOKE_SITE=<id> ./scripts/test-smoke.sh`.

## Local development

```
claude --plugin-dir ./rocket-net-plugin
```

Then `/reload-plugins` to hot-reload after changes. Validate with `claude plugin validate ./rocket-net-plugin --strict`.

## Layout

```
.claude-plugin/plugin.json   manifest (defaultEnabled false)
.mcp.json                    bundled Rocket.net remote MCP
bin/rocket.py                the CLI engine
bin/rocket_endpoints.json    generated operationId map
scripts/build_endpoints.py   spec to map converter (build-time)
scripts/test-smoke.sh        live smoke test
skills/                      12 workflow skills
commands/                    5 slash commands
reference/rocket-openapi.yaml  source of truth
tests/test_rocket.py         unit tests
docs/                        design spec and plan (local)
```
