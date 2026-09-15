# WP-CLI subcommand gotchas found during live incident work - 2026-08-20

Found while diagnosing a WP Rocket outage on a client production site. All are additive observations; no code changed in this session.

## 1. Global flags before `--` break the wp command

`rocket.py wpcli <site_id> --json -- "plugin get wp-rocket --field=version"` fails remotely with `Error: '--' is not a registered wp command`. The argparse REMAINDER capture includes the literal `--` token when a global flag precedes it, and the wrapper forwards it to WP-CLI as the first argument.

Working form: put global flags AFTER the command string, `rocket.py wpcli <site_id> -- "plugin get wp-rocket --field=version" --json`. DEVELOPMENT.md documents "global flags go AFTER the subcommand" but wpcli's `--` separator makes this uniquely easy to get wrong. Candidate fix: strip a leading `--` element from wp_args in the wpcli handler.

## 2. Rocket.net API bans shell metacharacters in wpcli commands

The API rejects any command containing backtick, `&`, `|`, `;`, newline, `$`, or `$(` with a 400 ("You can run wp cli via SSH if you need these characters"). This makes `wp eval` unusable for any multi-statement PHP (statements need `;`), including the base64 `eval(base64_decode(...));` workaround. Reading arbitrary remote files therefore is not possible via wpcli; use SFTP credentials (`credentials` subcommand) or fetch vendor source from GitHub instead.

## 3. Exit status is opaque

The response envelope's `status` field was `1` even for successful commands with clean output (e.g. `plugin get wp-rocket --field=version` returning `3.23.2.2`). Do not treat `status` as a failure signal on its own; parse `data` and look for `Error:` lines.

## 4. Plugin fatals poison plain wpcli calls

When a site has a fatal at plugins_loaded/init, most wpcli commands die with the same fatal. `--skip-plugins --skip-themes` inside the command string works and is the reliable diagnostic mode on a broken site (used for `plugin list` and `option get` during the incident).
