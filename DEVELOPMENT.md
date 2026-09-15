# rocket-net plugin - developer handoff

Context for any future Claude Code session continuing this plugin, including on a different machine. Read this first. User-facing usage is in README.md. The design spec and implementation plan are in docs/superpowers/ (local-only, scrub before any public publish).

## What this is

A Claude Code plugin to manage Rocket.net WordPress hosting. Hybrid architecture, three layers:

1. Bundled Rocket.net remote MCP (`.mcp.json`, points at `https://mcp.rocket.net/mcp`, auth via plugin `userConfig` stored in the OS keychain). For conversational actions.

2. A zero-dependency Python stdlib CLI at `bin/rocket.py`. The deterministic engine. Reaches all 198 API operations via a generic `call <operationId>` plus ergonomic subcommands. This is where almost all the logic lives.

3. 12 skills + 5 commands (markdown) as the workflow layer.

## Live-API gotchas (the important part - these are NOT obvious and cost real debugging)

These were discovered during a live smoke test on 2026-05-20-era WordPress 7.0 hosting accounts. They are partly encoded in the code, but consolidated here because they will bite anyone extending the plugin.

- Cloudflare blocks the default user-agent. The API (api.rocket.net) sits behind Cloudflare, which returns HTTP 403 "error 1010 browser_signature_banned" for the default `Python-urllib` user-agent. ANY other UA passes (even `python-requests`). The CLI sends `rocket-net-cli/0.1.0` (constant `USER_AGENT`, override with env `ROCKET_USER_AGENT`). Expect this on any Cloudflare-fronted API.

- Two-factor authentication does NOT block the API. Account 2FA gates only the web dashboard. `POST /v1/login {username, password}` returns `{token}` (a JWT, 7-day expiry) even with 2FA enabled. There is no permanent API key; a 401 means the token expired, re-login.

- Every response is wrapped in an envelope: `{success, errors, messages, result, metadata}`. Real data is under `result`. A few endpoints return a bare array instead (e.g. `ssl list` returns `[]` when empty). The CLI has `_result()` to unwrap; use it for any new response parsing.

- Async task polling. clone, staging create, backup create, and backup restore return `result.task_id` (a UUID) plus `task_level`. Poll `GET /v1/sites/{id}/tasks` (its `result` is a LIST). Task item keys: `id` (the UUID), `task_status` (seen: DONE and IN_PROGRESS; expect FAILED), `perc`, `task_type`, `site_id`. The status field is `task_status`, NOT `status`. IMPORTANT - `site create` is different: it returns the new `{id, domain}` directly (no task_id) and provisions in the background, so `--wait` must NOT poll it. The `--wait` extraction uses `task_id` only and never falls back to `id`. All of clone, staging publish, backup create, and backup restore `--wait` are validated end to end.

- Many POST endpoints REQUIRE a request body or they 400 with "RequestBody is required". Known ones and the bodies the CLI sends:
  - `cache/purge` needs `{files: [...]}` (this is the file-specific purge). `cache/purge_everything` needs no body. So the CLI maps `cache purge` to purge_everything (the common intent) and `cache purge-files <urls>` to the file purge.
  - `backup` create needs `{label, backup_directory, backup_database}` (label required). CLI: `backup create <site> --label X [--no-files] [--no-database]`.
  - `backup` restore needs `{backup_directory, backup_database}`.
  - `staging` create needs `{vanity_domain}` (nullable body). CLI flag `--vanity-domain`.
  - site create needs `{name, location, admin_username, admin_email}` at runtime. The OpenAPI schema marks only `name` required, but the API 400s on missing location or admin fields unless `template_id` is used. CLI: `site create --name X --location <id> --admin-username U --admin-email E [--admin-password ...] [--install-plugins a,b] [--multisite]`. Location ids come from operationId `...sites_locations_get` (they are regions; e.g. 16/20/27 are Asia Pacific). site clone body is all-optional: `site clone <id> [--label L] [--location <id>]`. Both also accept `--data '{...}'` as a full override.
  - Long-tail runtime requirements found live: FTP create needs ALL of username/password/homedir/quota/domain; SSH import needs name+key; SSL upload needs domains (an array) + certificate + key (PEM file contents). plugins/themes install and delete take a COMMA-SEPARATED STRING (not an array) under `plugins`/`themes`. reporting visitors and requests require a `duration` query param (enum 30m, 1h, 6h, 12h, 24h, 72h, 7d, 30d).
  - Before adding any new POST subcommand, check `has_body` in `bin/rocket_endpoints.json` and read the request schema in `reference/rocket-openapi.yaml`.

## CLI conventions

- Global flags go AFTER the subcommand (e.g. `rocket sites list --json`, `rocket site delete 99 --yes`). They are attached to each subcommand via an argparse parent parser. Putting a flag before the subcommand errors loudly (intentional, to avoid silently dropping it).

- Destructive guard is genuine-destructive-only. `--yes` is required for delete, restore, publish-to-production, transfer, reset, deauthorize, cancel. Clone and cache purge are NOT guarded (additive/safe), so a confirmation always means something. The destructive flag is computed at build time in `scripts/build_endpoints.py` (DESTRUCTIVE_HINTS) and baked into `bin/rocket_endpoints.json`.

- `main()` catches `RocketError` and prints a clean one-line message; do not let tracebacks reach the user.

- `_run_op()` is the shared subcommand helper (resolve op, dry-run, destructive guard, call, optional task wait). New subcommands should route through it.

## Setup on a new machine

1. Credentials. Create `~/.config/rocket-net/config.json` (chmod 600) with the Rocket.net account `username` + `password` (recommended; the CLI mints and refreshes the JWT) OR a manual `api_token`. This file is never committed. See `.env.example`. The values are account-specific and are NOT in this repo - provide them per machine.

2. Python 3 (developed and tested on 3.14). No third-party deps for the CLI itself.

3. Regenerating the endpoint map needs PyYAML (build-time only): `python3 scripts/build_endpoints.py`. The shipped CLI never imports yaml.

4. Load the plugin locally: `claude --plugin-dir ./rocket-net-plugin`, then `/reload-plugins`. Validate with `claude plugin validate ./rocket-net-plugin --strict`.

## Testing

- Unit tests (offline, no network, no creds): `python3 -m unittest tests.test_rocket -v`. 34 tests covering config/auth/http/envelope/task-find/op-constants/subcommands/guards/create-and-wait/long-tail.

- Live smoke test (needs creds + a real site): `ROCKET_SMOKE_SITE=<id> ./scripts/test-smoke.sh`. Only ever run against a throwaway or staging site, never production.

## State as of the last session (2026-06-10)

Live-validated against the real API (the full CLI surface): authentication, all read endpoints, `wpcli`, `cache purge`, `backup create`/`restore`/`delete`, `site create`, `site clone`, `staging create`, `staging publish`, and `site delete` - the complete create/clone/staging/restore/delete lifecycle, with `--wait` task polling where applicable. Validated by creating a throwaway site, exercising every op on it (and on its clone), then deleting both. The bundled MCP is configured but its end-to-end connection through the plugin enable flow was NOT separately exercised - only the CLI was live-tested.

Gotcha confirmed live: the API locks a site while it is being cloned, so a concurrent op such as `staging publish` returns a 400 "site is currently locked" until the clone task finishes. Wait for the clone, then retry.

## Known gaps and v0.2 TODOs

- Most of the full surface now has ergonomic subcommands (users, ssh, ftp, settings, reporting, pwprotect, credentials, access-logs, maindomain, plus install/update/delete for plugins/themes/domains/ssl/backup). A few niche endpoints remain generic-`call`-only: file manager, domain and maindomain edge_settings, activity log, automated/cloud backup restore variants, billing, WAF detail reports, shop_shield. Wrap them if a workflow needs them.
- Refresh the skills (rocket-users-access, rocket-reporting-waf, rocket-plugins-themes, rocket-domains-ssl) to use the new ergonomic subcommands instead of generic `call` (they still work via `call`, just verbose).
- Exercise the bundled MCP through a real plugin enable on a machine that supports it.
- Distribution: push to a remote repo and publish to the outfit + ai-loadout marketplaces. Scrub docs/ (spec, plan, any local dev notes) from history before any public push.

## House style

This repo follows the user's text hygiene: no em or en dashes, no colons in markdown headings (use " - "), straight quotes only. Keep it consistent in any new files.

## wpcli API findings - 2026-07-04 (client incident diagnosis)

Discovered while diagnosing production errors on a client site through the API wpcli channel.

- The API maintains a command blocklist. `wp eval` (and by implication eval-file) returns 400 "sorry, the wp command is not available via API. If you need to use this command, you can SSH into your account and run WP CLI directly". Standard reads (plugin list, option get/pluck/patch, config list, theme list, db query) all pass.

- Quote flattening. cmd_wpcli joins wp_args with spaces into one command string and the server re-splits it, so shell quoting from the local side is lost. To pass a quoted argument (eg SQL), embed literal double quotes that survive the local shell: `wpcli <site_id> -- db query "\"SELECT ... WHERE x='y'\""`. Without this, `db query` errors with "Too many positional arguments".

- Response pollution. The `data` payload inside result.response is a JSON-encoded string that PREPENDS any PHP notices emitted during WP boot (eg _load_textdomain_just_in_time notices) before the actual command output. Strip notice lines before parsing. result.response itself is a JSON string inside the JSON envelope - double decode.

- `credentials <site>` returns plaintext SFTP username and password. In Claude Code auto mode the permission classifier blocks materializing these (printing or writing to a file), so file-level work (mu-plugins, wp-config edits) needs an interactively-approved session or manual upload via the Rocket.net dashboard File Manager. Plan workflows accordingly.

- `db query` permits writes as well as reads (used successfully for option-free schema checks; treat with the same care as any production SQL).
