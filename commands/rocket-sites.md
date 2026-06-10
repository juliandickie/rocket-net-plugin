---
description: List and inspect Rocket.net sites in the account.
---

# /rocket-sites

List and inspect sites in your Rocket.net account.

Steps:
1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` to retrieve all sites.
2. If the user asked about a specific site, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites get <site_id>` to fetch its details.
3. Present the results clearly - site name, ID, URL, status, and any other relevant fields.
