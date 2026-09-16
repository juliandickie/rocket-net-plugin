---
name: rocket-reporting-waf
description: "Pull bandwidth, CDN, visitor, and WAF event reporting from Rocket.net. Use when the user wants hosting analytics, traffic or bandwidth figures, or web application firewall event data for a site."
---

# Rocket.net reporting and WAF

All reporting endpoints are read-only. No --yes required. Three common reads have subcommands; the CDN and WAF breakdowns stay on the generic `call` form. Global flags (`--json`) go AFTER the subcommand.

## Subcommands

Site bandwidth usage:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py reporting bandwidth <site_id>
```

Site visitors over a window (default 7d; choices 30m, 1h, 6h, 12h, 24h, 72h, 7d, 30d):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py reporting visitors <site_id> --duration 30d
```

Total requests over a window (same choices):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py reporting requests <site_id> --duration 24h
```

Raw request-level access logs:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py access-logs <site_id>
```

## Account-level (generic call)

Account bandwidth:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.bandwidth_controller.account_bandwidth_get
```

Account visitors:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.visitors_controller.account_visitors_get
```

Top bandwidth consumers for a site (by IP, URL, country):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_bandwidth_top_usage_get --param id=<site_id>
```

## CDN reporting (generic call)

CDN request volume:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_requests_get --param id=<site_id>
```

Cache status breakdown (hit, miss, expired, bypass):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_status_get --param id=<site_id>
```

Cached versus uncached by content type:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_content_get --param id=<site_id>
```

The `cdn_cache_top` endpoint is deprecated upstream; use the request-volume endpoint above.

## WAF events (generic call)

Event list (paginated):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_eventlist_get --param id=<site_id>
```

Events by source (IP, URL, country):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_source_get --param id=<site_id>
```

Events over time:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_time_get --param id=<site_id>
```

Events by service:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_services_get --param id=<site_id>
```

Firewall events:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_firewall_events_get --param id=<site_id>
```

Rocket.net's hosted MCP exposes a newer `waf/events-stats` tool (`get_v1_reporting_sites_id_waf_events-stats`) that supersedes the two above. It is not in the public OpenAPI spec, so the CLI cannot reach it; use the bundled MCP for that one.

## Safety summary

All reporting endpoints are read-only. Safe to run without confirmation.
