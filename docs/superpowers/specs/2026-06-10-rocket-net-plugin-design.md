# rocket-net Plugin - Design Spec

Date - 2026-06-10
Status - approved design, pending spec review before implementation planning
Owner - Julian (Pro Marketing)

## 1. Purpose

A Claude Code plugin that manages Rocket.net WordPress hosting programmatically and conversationally. It lets Julian (and later, any Rocket.net customer) drive site lifecycle, staging and deploys, WP-CLI, backups, and the rest of the Rocket.net platform from inside Claude Code, with workflow knowledge baked in so an agent does the right thing safely.

This plugin manages HOSTING (the Rocket.net platform). It is NOT a WordPress content manager. Content and WordPress-REST work belong to the separate wp-index and planned wp-manager tools. The bridge between the two worlds is the WP-CLI passthrough (Section 4.3).

## 2. Locked Decisions

These were decided during brainstorming on 2026-06-10.

1. Architecture - Hybrid. Bundle Rocket.net's first-party MCP for conversational actions, PLUS a single-file Python REST CLI for scripted/bulk/async work, PLUS skills and commands as the workflow layer.

2. Audience - Internal-first (Pro Marketing and iDD fleet), built clean enough to publish later to the outfit and ai-loadout marketplaces.

3. Live testing - Available. Julian provides credentials via `~/.config/rocket-net/config.json`. Live tests run only against a throwaway or designated staging site, never production.

4. Scope - Full API surface (all 139 endpoints reachable), delivered via a spec-driven generic call plus ergonomic subcommands for the common paths. Not 139 hand-written commands.

5. CLI language - Python (standard library only). Chosen for zero-dependency single-file distribution and first-class subcommand ergonomics via argparse over a large endpoint surface.

6. MCP bundling - Yes, bundled so it auto-starts on enable.

7. MCP auth - Username and password headers (Rocket.net's MCP self-refreshes the JWT), via Claude Code userConfig stored in the OS keychain.

## 3. Architecture

Three layers, each with a distinct job.

### 3.1 Layer A - Rocket.net first-party MCP (bundled)

Rocket.net runs a remote MCP server at `https://mcp.rocket.net/mcp` over Streamable HTTP. It exposes "anything you can do through the Rocket.net API." The plugin bundles a `.mcp.json` pointing at it, so on enable the agent gains live Rocket.net tools with no local install.

Use it for - interactive, exploratory, natural-language actions. "Spin up a site", "what is eating disk on site X", "update this plugin across these three sites".

### 3.2 Layer B - Our REST CLI (bin/rocket.py)

A single-file Python stdlib program. It is the deterministic engine that skills call and that Julian can run directly or in cron or CI.

Use it for - repeatable scripted operations, bulk and fleet operations, async task polling with backoff, large list and report pulls that should not consume agent context, and resilience when the MCP is unavailable.

Why both B and A - the MCP is great for conversation but weak for deterministic scripting, polling long-running tasks, and not burning context on large outputs. The CLI fills exactly those gaps and gives skills a reliable scripted primitive. They are complementary, not redundant.

### 3.3 Layer C - Skills and commands (the workflow knowledge)

Skills encode HOW to do each workflow well and safely, composing Layer A and Layer B. Commands are explicit slash actions for the highest-frequency tasks. This is the real value-add over raw API or MCP access.

### 3.4 When-to-use matrix

| Task type | Use |
|---|---|
| Conversational one-off action | Layer A (MCP) |
| Scripted, repeatable, or scheduled | Layer B (CLI) |
| Bulk or fleet operation | Layer B (CLI), parallelized |
| Long-running task you must wait on | Layer B (CLI) with `--wait` |
| Large list or report (avoid context bloat) | Layer B (CLI), `--json` to a file |
| Guided multi-step workflow | Layer C (skill) orchestrating A or B |

## 4. Components

### 4.1 Manifest - .claude-plugin/plugin.json

Fields - `name` (rocket-net), `version`, `author`, `description`, and `userConfig` to prompt for credentials at enable time. userConfig values are masked and stored in the OS keychain, then substituted as `${user_config.KEY}` in the bundled MCP config.

userConfig keys - `rocketnet_username`, `rocketnet_password` (for the MCP). These are independent of the CLI's `~/.config/rocket-net/config.json`. Documented so the user knows both exist and why.

Note - the exact userConfig schema is a fast-moving plugin feature. Verify field names against the current code.claude.com plugins reference at build time before finalizing.

### 4.2 Bundled MCP - .mcp.json

```json
{
  "mcpServers": {
    "rocket-net": {
      "type": "http",
      "url": "https://mcp.rocket.net/mcp",
      "headers": {
        "ROCKETNET_USERNAME": "${user_config.rocketnet_username}",
        "ROCKETNET_PASSWORD": "${user_config.rocketnet_password}"
      }
    }
  }
}
```

Rationale for username/password over a Bearer token - Rocket.net JWTs expire in 7 days. Passing username/password headers lets Rocket's MCP mint and refresh tokens itself, so the connection never silently dies. Verify the exact header names and transport key against developers.rocket.net/mcp at build time.

### 4.3 REST CLI - bin/rocket.py

Single-file, Python 3 standard library only (`urllib`, `json`, `argparse`, `time`, `os`, `concurrent.futures`). Responsibilities -

Config and auth resolution (precedence, first match wins) -
1. Env `ROCKET_API_TOKEN` (a JWT supplied directly).
2. `~/.config/rocket-net/config.json` `api_token` (manual JWT).
3. `~/.config/rocket-net/config.json` `username` + `password` -> POST /v1/login -> JWT.

Token cache - on login, cache the JWT and its expiry to `~/.config/rocket-net/.token` (chmod 600). Reuse until near expiry. On any 401, re-login once and retry the request. Never log tokens.

Command surface -
- Ergonomic subcommands for common paths - `auth` (login/status/whoami), `sites` (list/get/create/clone/delete/lock/transfer), `staging` (create/publish/delete), `wpcli` (run a WP-CLI command on a site), `backup` (list/create/restore across manual, automated, cloud), `cache` (purge, purge-everything), `domains`, `ssl`, `ftp`, `ssh`, `files`, `plugins`, `themes`, `settings`, `users`, `reporting`, `billing`, `account`.
- Generic escape hatch - `rocket call <operationId> [--param k=v ...] [--data @body.json]` reaches all 139 endpoints using the operation map (Section 4.5).

Global flags -
- `--wait` poll the resulting background task to completion.
- `--yes` confirm a destructive operation non-interactively.
- `--json` emit raw JSON (for scripts and to keep large output out of agent context).
- `--dry-run` print the request that would be sent, send nothing.
- `--site <id>` target site.
- `--timeout <s>` per request and overall poll timeout.

### 4.4 Skills - skills/<name>/SKILL.md

Frontmatter per skill - `name` (lowercase, hyphenated, max 64) and `description` (third person, max 1024, states what it does and the trigger conditions). Keep each SKILL.md under about 500 lines, push detail into a sibling reference file, load on demand.

v1 skill set (full surface, tiered by depth) -
- `rocket-net` - router and overview. When to use MCP vs CLI, auth setup, safety rules. The entry point.
- `rocket-site-lifecycle` - create, clone, delete, lock, transfer sites.
- `rocket-staging-deploy` - staging create and refresh, publish staging to production with a scope review.
- `rocket-wp-cli` - run WP-CLI on a site safely (read vs write, dry-run for destructive WP-CLI).
- `rocket-backups` - manual, automated, and cloud backups and restores, with restore-direction confirmation.
- `rocket-fleet-ops` - bulk operations across many sites (parallelized CLI calls, scope review first).
- `rocket-domains-ssl` - domains, edge settings, SSL certificates.
- `rocket-plugins-themes` - plugin and theme install, search, updates.
- `rocket-cache-cdn` - cache purge and CDN cache management.
- `rocket-reporting-waf` - bandwidth, CDN, visitors, WAF event reporting.
- `rocket-users-access` - site users, roles, SSH keys, FTP accounts, password protection.
- `rocket-billing-account` - account info, usage, billing (read-first; payment mutations gated).

The first six are deep workflow skills. The last six are thinner wrappers over the generic CLI call plus a reference file, present so the full surface is covered without heavy authoring. Thin skills may be merged if they prove too granular.

### 4.5 Reference and build - reference/

- `reference/rocket-openapi.yaml` - the source of truth (already in place).
- `reference/endpoints.json` - generated map of operationId to method, path, parameters, and whether the operation is destructive or returns a task. The CLI loads this JSON at runtime (stdlib, no YAML dependency).
- `scripts/build-endpoints.py` - dev-time converter from the YAML spec to endpoints.json. Run when the spec updates. YAML parsing happens only here, at build time, never in the shipped CLI.

### 4.6 Commands - commands/*.md

v1 - `/rocket-sites` (list and inspect the fleet), `/rocket-deploy` (publish staging to production with scope review), `/rocket-stage` (create or refresh staging), `/rocket-backup` (create or restore), `/rocket-wp` (run a WP-CLI command).

## 5. Data Flow Example - /rocket-deploy

1. Skill resolves the target site and confirms a staging environment exists.
2. CLI fetches current production and staging state (read before change).
3. Skill presents a scope review - what will be overwritten, source and target, backup status.
4. On explicit approval, CLI calls staging publish, returns a task id.
5. CLI polls the task with `--wait` until success or failure with backoff.
6. CLI purges cache, verifies the site responds (wp/status), reports the outcome.

## 6. Auth and Secrets Design

- CLI credentials - `~/.config/rocket-net/config.json` (chmod 600, outside the repo, never committed). Supports username/password (auto-refresh) or a manual api_token.
- MCP credentials - Claude Code userConfig, masked, stored in the OS keychain, never written to a file in the repo.
- Token cache - `~/.config/rocket-net/.token`, chmod 600.
- The repo ships a `.env.example` and documents both credential paths in the README. The repo never contains a real secret. `.gitignore` excludes any `.token`, `.env`, and local config.

## 7. Async Task Handling

Create, clone, restore, and staging publish return a background task. The CLI `--wait` flag polls `/v1/sites/{id}/tasks` (or `/v1/account/tasks`) until the task reports done or failed, using exponential backoff and an overall timeout. On failure the CLI exits non-zero with the task error detail. endpoints.json flags which operations return tasks so skills know when to pass `--wait`.

## 8. Error Handling

- 401 - re-login once, retry once, then fail clearly (token likely revoked).
- 4xx - surface the API error message and the offending request summary (never the token).
- 429 - back off and retry with a cap.
- Network or timeout - retry with backoff up to a small limit, then fail.
- Task failure - non-zero exit, task error detail surfaced.
- All failures are loud. The CLI never reports success on partial completion.

## 9. Safety Rails

- Destructive operations - delete site, restore over an environment, publish staging to production, cancel a task, transfer a site - require `--yes` or an interactive confirmation. Skills present a scope review before any destructive or batched action.
- Read before change - skills fetch current state before mutating.
- Production protection - live tests and smoke tests refuse to run against a site unless an explicit staging or test site id is provided.
- This honors Julian's standing rules on scope check-in before destructive batched changes and read-before-change.

## 10. Testing Strategy

- `scripts/test-smoke.sh` - end-to-end live check gated behind an explicit `ROCKET_SMOKE_SITE` id and `--yes`. Flow - login, list sites, run a benign WP-CLI (wp option get blogname), create and verify a backup, purge cache, optionally create and then delete a throwaway test site. Never touches production.
- `--dry-run` - exercises destructive code paths without sending, for safe verification.
- Per Julian's verify-not-assume rule, no capability is claimed working until the smoke test passes against a real staging site.

## 11. Repo Structure

```
rocket-net-plugin/
  .claude-plugin/
    plugin.json
  .mcp.json
  bin/
    rocket.py
  skills/
    rocket-net/SKILL.md
    rocket-site-lifecycle/SKILL.md
    rocket-staging-deploy/SKILL.md
    rocket-wp-cli/SKILL.md
    rocket-backups/SKILL.md
    rocket-fleet-ops/SKILL.md
    rocket-domains-ssl/SKILL.md
    rocket-plugins-themes/SKILL.md
    rocket-cache-cdn/SKILL.md
    rocket-reporting-waf/SKILL.md
    rocket-users-access/SKILL.md
    rocket-billing-account/SKILL.md
  commands/
    rocket-sites.md
    rocket-deploy.md
    rocket-stage.md
    rocket-backup.md
    rocket-wp.md
  reference/
    rocket-openapi.yaml
    endpoints.json
  scripts/
    build-endpoints.py
    test-smoke.sh
  docs/                      (local-only dev notes, gap log, this spec)
  .env.example
  .gitignore
  README.md
```

## 12. Distribution

- Internal-first - develop in `~/code/rocket-net-plugin`, test with `claude --plugin-dir ./rocket-net-plugin` and `/reload-plugins`.
- Clean for public later - publish to the outfit and ai-loadout marketplaces (mirror both per the catalog-sync rule). `docs/` stays local-only and is scrubbed before any public push.
- README always reflects current state.

## 13. Out of Scope (YAGNI)

- Building our own MCP server. We use Rocket.net's.
- A GUI.
- Multi-host abstraction. This is Rocket.net specific.
- WordPress content management. That is wp-index and wp-manager. The WP-CLI passthrough is the only bridge.
- Billing mutations beyond reading. Payment actions stay manual.

## 14. Open Questions and Verify-at-Build

1. Exact userConfig schema and field names in the current Claude Code plugin reference.
2. Exact `.mcp.json` transport key and header names accepted by Rocket.net's MCP (http vs the mcp-remote bridge for clients that need a local process).
3. Whether any Rocket.net plan tier gates MCP or specific endpoints.
4. Confirm the operationId values in the spec are stable enough to key the generic `call` command on, or whether to key on method plus path.
