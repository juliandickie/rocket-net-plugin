---
name: rocket-domains-ssl
description: "Manage domains, edge settings, and SSL certificates on Rocket.net sites. Use when the user wants to add or inspect a domain, change edge settings, or review SSL certificates."
---

# Rocket.net domains and SSL

Covers custom domains, the main domain, edge (CDN/proxy) settings, and SSL certificates.

## Read current domains

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py domains list <site_id>
```

Or via generic call:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_get --param id=<site_id>
```

## Get main domain

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_get --param id=<site_id>
```

## Add a custom domain

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_post --param id=<site_id> --data '{"domain":"example.com"}'
```

## Check main domain DNS status

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_status_get --param id=<site_id>
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_recheck_get --param id=<site_id>
```

## Edge settings

Edge settings control CDN and proxy behaviour per domain.

Read edge settings for main domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_edge_settings_get --param id=<site_id>
```

Update edge settings for main domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_maindomain_edge_settings_patch --param id=<site_id> --data '{"ssl_mode":"full"}'
```

Read edge settings for a specific domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_domain_id_edge_settings_get --param id=<site_id> --param domain_id=<domain_id>
```

Update edge settings for a specific domain:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_domain_id_edge_settings_patch --param id=<site_id> --param domain_id=<domain_id> --data '{"ssl_mode":"full"}'
```

## Delete a domain

Requires --yes.

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.domains_controller.sites_id_domains_domain_id_delete --param id=<site_id> --param domain_id=<domain_id> --yes
```

## SSL certificates

List certificates:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py ssl list <site_id>
```

Or:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.custom_ssl_controller.sites_id_ssl_certificates_get --param id=<site_id>
```

Get a specific certificate:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.custom_ssl_controller.sites_id_ssl_certificates_id_get --param id=<site_id> --param certificate_id=<certificate_id>
```

Upload a custom SSL certificate:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.custom_ssl_controller.sites_id_ssl_certificates_post --param id=<site_id> --data '{"certificate":"...","private_key":"..."}'
```

Delete a certificate - requires --yes:

```
python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py call app.controllers.custom_ssl_controller.sites_id_ssl_certificates_id_delete --param id=<site_id> --param certificate_id=<certificate_id> --yes
```

## Safety summary

Reads: safe. Domain/cert deletes: require --yes. Edge setting changes: non-destructive but affect live traffic - read before patching.
