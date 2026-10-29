# .htaccess redirect hosts on Rocket.net, and three API behaviors (2026-09-23)

Found while building a dedicated redirect-only install for a retired subdomain whose DNS stays at an external provider. Additive to the earlier dev-docs notes; nothing here changes the CLI.

## An ErrorDocument re-enters .htaccess

Rocket.net's server serves its own error page for 410 through an internal request. That request runs back through the site's `.htaccess`. A redirect block ending in a catch-all (`RewriteRule ^.*$ <target> [R=301,L]`) therefore turned every `[G]` (410) rule into a 301 to the catch-all target. A local Apache 2.4 without an `ErrorDocument` did not reproduce it until `ErrorDocument 410 /gone.html` was added.

The fix is a guard at the top of the block, so no rule touches an internal request:

```apache
RewriteCond %{ENV:REDIRECT_STATUS} !^$
RewriteRule ^ - [L]
```

Any skill or recipe that writes redirect rules into a Rocket.net `.htaccess` should carry that guard, and should test a 410 path live after a purge rather than trusting a local run.

## Three API behaviors confirmed live

- `site create` returns `{id, domain}` directly and the site reported `active` within a minute (Sydney, location 16). The new site's `onrocket.site` host sends `x-robots-tag: noindex, noarchive, nosnippet`, the platform's standard for temporary hosts.
- `sites_id_files_view_get` reads a site-root file with `directory` set to `/`, `.` or empty; all three returned the same `.htaccess`. `files_put` with a root path wrote `.htaccess` and read back with a matching MD5.
- `sites_id_maindomain_post` accepts `{"domain": ..., "keep_cdn_url": true}` (schema `SetMainDomainRequest`): it returns two TXT validation records (`_acme-challenge.<host>` for the certificate, `_cf-custom-hostname.<host>` for the hostname) while WordPress stays on the CDN URL, which is the API route to SSL pre-validation before a DNS switch. Exercised live the same night: once both TXT records and the CNAME were in, `maindomain status` listed them under `found_dns_records` but stayed pending until `sites_id_maindomain_recheck_get` was called; SSL then went active within a minute (Google Trust Services, 90 days) and the hostname a minute later. In between, the custom domain answered HTTP 409 from the edge, so poll `maindomain status` for `active active` before testing. The custom domain did not carry the temporary host's `x-robots-tag` header, and a redirect-only install worked without the dashboard's Go Live step.
