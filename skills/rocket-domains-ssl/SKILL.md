---
name: rocket-domains-ssl
description: "Manage domains, edge settings, and SSL certificates on Rocket.net sites. Use when the user wants to add or inspect a domain, change edge settings, or review SSL certificates."
---

# Rocket.net domains and SSL

Covers custom domains, the main domain, edge (CDN and proxy) settings, and SSL certificates. Domains, main domain reads, and SSL have subcommands; edge settings and the DNS recheck stay on generic `call`. Global flags (`--json`, `--yes`) go AFTER the subcommand.

## Domains

List domains on a site:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py domains list <site_id>
```

Add a custom domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py domains add <site_id> --domain example.com
```

Remove a domain - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py domains remove <site_id> <domain_id> --yes
```

## Main domain

Get the primary domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py maindomain get <site_id>
```

DNS status of the primary domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py maindomain status <site_id>
```

Force a DNS recheck (generic call):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_recheck_get --param id=<site_id>
```

## Edge settings (generic call)

Edge settings control CDN and proxy behaviour per domain. Read before patching; changes affect live traffic.

Main domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_edge_settings_get --param id=<site_id>
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_edge_settings_patch --param id=<site_id> --data '{"ssl_mode":"full"}'
```

A specific additional domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_domain_id_edge_settings_get --param id=<site_id> --param domain_id=<domain_id>
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_domain_id_edge_settings_patch --param id=<site_id> --param domain_id=<domain_id> --data '{"ssl_mode":"full"}'
```

## SSL certificates

List certificates (returns an empty list when the site uses only the platform certificate):

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssl list <site_id>
```

Get one certificate:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssl get <site_id> <certificate_id>
```

Upload a custom certificate. Domains are comma-separated; certificate and key are paths to PEM files, read locally and sent in the body:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssl upload <site_id> --domains example.com,www.example.com --certificate-file ./cert.pem --key-file ./key.pem
```

Delete a certificate - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssl delete <site_id> <certificate_id> --yes
```

## Safety summary

Reads: safe. Domain and certificate deletes: require --yes. Edge setting changes and certificate uploads: non-destructive but affect live traffic, read before changing.
