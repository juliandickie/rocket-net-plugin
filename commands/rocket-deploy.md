---
description: Publish a Rocket.net staging site to production with a scope review.
---

# /rocket-deploy

Publish staging to production for a Rocket.net site. This is destructive (overwrites production).

Steps:
1. Identify the target site (ask if not given). Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` if you need to find it.
2. Fetch current production and staging state and confirm staging exists.
3. Present a scope review: site, what will be overwritten, last backup time. Recommend taking a backup first.
4. On explicit approval, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py staging publish <site_id> --yes --wait`.
5. Purge cache and verify the site responds. Report the outcome loudly (success or partial failure).
