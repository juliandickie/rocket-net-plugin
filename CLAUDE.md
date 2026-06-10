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

- Async task polling. create/clone/backup return `result.task_id` (a UUID) and `task_level`. Poll `GET /v1/sites/{id}/tasks` (its `result` is a LIST). Task item keys: `id` (the UUID), `task_status` (seen: DONE; expect IN_PROGRESS/FAILED), `perc`, `task_type`, `site_id`. The status field is `task_status`, NOT `status`. `--wait` is wired to this; `backup create --wait` is validated end to end.

- Many POST endpoints REQUIRE a request body or they 400 with "RequestBody is required". Known ones and the bodies the CLI sends:
  - `cache/purge` needs `{files: [...]}` (this is the file-specific purge). `cache/purge_everything` needs no body. So the CLI maps `cache purge` to purge_everything (the common intent) and `cache purge-files <urls>` to the file purge.
  - `backup` create needs `{label, backup_directory, backup_database}` (label required). CLI: `backup create <site> --label X [--no-files] [--no-database]`.
  - `backup` restore needs `{backup_directory, backup_database}`.
  - `staging` create needs `{vanity_domain}` (nullable body). CLI flag `--vanity-domain`.
  - site create and clone need bodies (CreateSiteRequest etc.) - the CLI currently only exposes `--data '{...}'` for these; friendly args are a v0.2 TODO.
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

- Unit tests (offline, no network, no creds): `python3 -m unittest tests.test_rocket -v`. 25 tests covering config/auth/http/envelope/task-find/op-constants/subcommands/guards.

- Live smoke test (needs creds + a real site): `ROCKET_SMOKE_SITE=<id> ./scripts/test-smoke.sh`. Only ever run against a throwaway or staging site, never production.

## State as of the last session (2026-06-10)

Live-validated against the real API: authentication, all read endpoints, `wpcli` (read), `cache purge` (everything), and `backup create --wait` (full async task-polling). The bundled MCP is configured but its end-to-end connection through the plugin enable flow was NOT separately exercised - only the CLI was live-tested.

NOT yet live-tested (they mutate whole sites, so they were deliberately left alone): `site create`, `site clone`, `staging create`, `staging publish`, `backup restore`. They are coded from the spec and dry-run-correct, but unproven against the live API. The user will provide a dedicated test site for this later. Do not test these against a production site.

## Known gaps and v0.2 TODOs

- Friendly args for `site create` / `site clone` (currently `--data` only) - read CreateSiteRequest / clone request schemas.
- Ergonomic subcommands for the rest of the full surface currently reachable only via generic `call`: users, SSH keys, FTP, file manager, reporting/WAF, billing, automated/cloud backups, password protection, domains add/edit, SSL upload, plugin/theme install.
- Live-test the mutating ops on a staging site (staging publish, backup restore, site clone) once a safe target is available.
- Exercise the bundled MCP through a real plugin enable on a machine that supports it.
- Distribution: push to a remote repo and publish to the outfit + ai-loadout marketplaces. Scrub docs/ (spec, plan, any local dev notes) from history before any public push.

## House style

This repo follows the user's text hygiene: no em or en dashes, no colons in markdown headings (use " - "), straight quotes only. Keep it consistent in any new files.
