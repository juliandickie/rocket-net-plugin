---
name: rocket-reporting-waf
description: "Pull bandwidth, CDN, visitor, and WAF event reporting from Rocket.net. Use when the user wants hosting analytics, traffic or bandwidth figures, or web application firewall event data for a site."
---

# Rocket.net reporting and WAF

All reporting endpoints are read-only. No --yes required.

## Bandwidth

Site-level bandwidth usage:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_bandwidth_usage_get --param id=<site_id>
```

Top bandwidth consumers:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_bandwidth_top_usage_get --param id=<site_id>
```

Site-level bandwidth (alternate path):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.bandwidth_controller.sites_id_reporting_bandwidth_get --param id=<site_id>
```

Account-level bandwidth:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.bandwidth_controller.account_bandwidth_get
```

## Visitors

Site visitor counts:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_visitors_get --param id=<site_id>
```

Account-level visitors:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.visitors_controller.account_visitors_get
```

## CDN reporting

CDN request volume:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_requests_get --param id=<site_id>
```

Cache status breakdown:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_status_get --param id=<site_id>
```

Cache content types:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_content_get --param id=<site_id>
```

Top cached URLs:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_top_get --param id=<site_id>
```

## WAF events

WAF event list (paginated):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_eventlist_get --param id=<site_id>
```

WAF events by service:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_services_get --param id=<site_id>
```

WAF events by source (IP, country):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_source_get --param id=<site_id>
```

WAF events over time:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_events_time_get --param id=<site_id>
```

Firewall events:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_waf_firewall_events_get --param id=<site_id>
```

## Access logs

For raw request-level logs see the access_logs_controller:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.access_logs_controller.sites_id_access_logs_get --param id=<site_id>
```

## Safety summary

All reporting endpoints are read-only. Safe to run without confirmation.
