---
description: Create or refresh a Rocket.net staging environment for a site.
---

# /rocket-stage

Create or refresh a staging environment for a Rocket.net site.

Steps:
1. Identify the target site (ask if not given). Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` if you need to find it.
2. Check whether a staging environment already exists by running `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites get <site_id>` and reviewing staging state.
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py staging create <site_id> --wait` to create or refresh the staging environment.
4. Report the staging URL and status once the task completes.
