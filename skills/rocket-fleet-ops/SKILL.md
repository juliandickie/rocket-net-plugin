---
name: rocket-fleet-ops
description: "Run bulk operations across many Rocket.net sites. Use when the user wants to apply an action (plugin update, cache purge, report pull, wp command) across multiple or all sites. Parallelizes CLI calls and presents a scope review before any batch change."
---

# Rocket.net fleet operations

Fleet ops apply a single action across many sites. The CLI does not have a native bulk command - Claude orchestrates parallel calls using the site list as input.

## Step 1 - get the site list

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" sites list
```

Parse the JSON response to extract site IDs and names. Confirm the target set with the user before proceeding.

## Step 2 - scope review before any batch change

Present:
- The action to apply
- The full list of target sites (IDs and names)
- Whether any site requires --yes
- Estimated time

Get explicit approval before running.

## Parallelizing with Python

For batch read operations (no approval needed):

```python
import json, subprocess, concurrent.futures, sys

# The running Python, so no python3 lookup (Windows-safe). Claude Code fills in the
# path when it loads this skill; CLAUDE_PLUGIN_ROOT is not in the Bash tool's environment.
CLI = [sys.executable, r"${CLAUDE_PLUGIN_ROOT}/bin/rocket.py"]

def run(site_id):
    r = subprocess.run([*CLI, "cache", "purge", site_id],
                       capture_output=True, text=True)
    return site_id, r.returncode, r.stdout.strip(), r.stderr.strip()

site_ids = ["123", "456", "789"]  # from sites list
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    results = list(ex.map(run, site_ids))

for sid, rc, out, err in results:
    status = "ok" if rc == 0 else "FAILED"
    print(f"{sid}: {status}  {err or out}")
```

## Common fleet patterns

Purge cache on all sites:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" cache purge <site_id>
# repeat per site (or parallelise as above)
```

Run the same WP-CLI command across all sites:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" wpcli <site_id> -- plugin update --all
```

Pull bandwidth report for all sites:

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.reporting_controller.reporting_sites_id_bandwidth_usage_get --param id=<site_id>
```

List plugins on all sites (audit):

```
"${CLAUDE_PLUGIN_ROOT}/bin/rocket" call app.controllers.plugins_controller.sites_id_plugins_get --param id=<site_id>
```

## Destructive batch ops

Never batch destructive operations (delete, restore, publish) without:
1. An individual scope review per site
2. Explicit --yes for each
3. User confirmation of the full list

Even with approval, run destructive fleet ops one site at a time, not concurrently.

## Safety summary

Read and cache purge: parallelise freely. Write, delete, restore, publish: sequential, one site at a time, with per-site scope review. Present results loudly - surface any failures immediately.
