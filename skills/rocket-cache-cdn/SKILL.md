---
name: rocket-cache-cdn
description: "Purge cache and manage CDN cache settings on Rocket.net. Use when the user wants to clear a site cache, purge everything, or manage CDN cache behavior."
---

# Rocket.net cache and CDN

Rocket.net uses a CDN cache layer in front of each site. Purging is non-destructive and safe to run without --yes.

## Purge the entire cache

`cache purge` clears the whole CDN cache for the site. Non-destructive (content is unaffected; cache rebuilds on next request). This is the common case.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py cache purge <site_id>
```

## Purge specific file URLs

`cache purge-files` purges only the listed URLs (the underlying endpoint requires a file list).

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py cache purge-files <site_id> https://example.com/page/ https://example.com/style.css
```

## When to purge

Purge after:
- Publishing staging to production
- Deploying a theme or plugin update
- Changing site settings that affect rendered output
- A search-replace that changes URLs

## CDN cache reporting

View cache status breakdown:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_status_get --param id=<site_id>
```

View top cached content:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_cache_top_get --param id=<site_id>
```

View CDN request volume:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.reporting_controller.reporting_sites_id_cdn_requests_get --param id=<site_id>
```

## Fleet cache purge

To purge cache across multiple sites, run purge per site. See rocket-fleet-ops for a parallelised approach.

## Safety summary

Cache purge and purge-files are safe - no --yes required. They affect delivery speed only, not site content.
