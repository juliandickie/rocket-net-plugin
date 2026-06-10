---
description: Run a WP-CLI command on a Rocket.net site (dry-run destructive wp commands first).
---

# /rocket-wp

Run a WP-CLI command on a Rocket.net site via the hosting API.

Steps:
1. Identify the target site (ask if not given). Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` if you need to find it.
2. Assess whether the WP-CLI command is read-only (option get, plugin list, user list) or potentially destructive (search-replace, plugin activate/deactivate, user create/delete, db reset).
3. For read-only commands, run directly: `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py wpcli <site_id> -- <wp-cli-command>`.
4. For potentially destructive commands, present the exact command to the user for confirmation before running it. Then run with the confirmed command.
5. Report the WP-CLI output verbatim.
