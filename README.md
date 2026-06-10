# rocket-net

A Claude Code plugin to manage Rocket.net WordPress hosting two ways - conversationally through Rocket.net's bundled MCP server, and deterministically through a zero-dependency Python CLI. Skills and commands add the workflow knowledge on top.

Status - v0.1.0. Build complete and validated (25 unit tests, `claude plugin validate --strict`). Live smoke test PASSED against a real site - authentication, all read endpoints, WP-CLI, cache purge, and the async backup-task polling are confirmed working against the live API. Mutating operations that change a whole site (site create and clone, staging create and publish, backup restore) are built from the spec but not yet live-tested.

## What is in the box

- A bundled MCP server (`.mcp.json`) pointing at Rocket.net's hosted MCP at `https://mcp.rocket.net/mcp`. Best for conversational, one-off actions.

- A CLI at `bin/rocket.py` (Python 3 standard library only). Best for scripted, bulk, and async work, and for anything you must wait on. Reaches all 198 API operations.

- 12 skills and 5 commands that encode how to run common workflows safely.

This plugin manages the Rocket.net HOSTING platform. It is not a WordPress content manager. For content and WordPress-REST work, use a separate tool. The bridge between the two is the WP-CLI passthrough (`rocket wpcli`).

## Credentials

Two independent credential paths.

- CLI - create `~/.config/rocket-net/config.json` (chmod 600) with either Rocket.net `username` and `password` (recommended, the CLI auto-mints and refreshes the token) or a manual `api_token`. See `.env.example`. Note - Rocket.net has no permanent API key; tokens are JWTs that expire after 7 days, which is why username and password is the low-maintenance choice.

- MCP - when you enable the plugin, Claude Code prompts for your Rocket.net email and password and stores them in your OS keychain (never in a file). Rocket.net's MCP refreshes its own token.

Note - Rocket.net sits behind Cloudflare, which blocks the default Python user-agent (error 1010). The CLI sends its own `rocket-net-cli/0.1.0` User-Agent so requests pass; override it with the `ROCKET_USER_AGENT` env var if needed. Two-factor authentication on your account does not block the API login (2FA gates only the web dashboard).

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

Ergonomic subcommands - `sites list|get`, `site create|clone|delete`, `staging create|publish`, `wpcli`, `backup list|create|restore`, `cache purge|purge-files`, `domains list`, `ssl list`, `plugins list`, `themes list`, `account me|usage`. Note - `cache purge` clears the entire cache; `cache purge-files` purges specific URLs. `backup create` requires `--label`.

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
.claude-plugin/plugin.json   manifest (userConfig for MCP creds, defaultEnabled false)
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
