# Go Live, main domain and object cache notes - 2026-10-04

From moving a production WordPress site onto Rocket.net, additive to `2026-09-23-htaccess-redirect-host-notes.md`.

- Go Live through the API is `sites_id_maindomain_put` with `{"active_wordpress_domain": "live_domain"}` only. Sending `domain` as well returns 400 "You can only choose 'domain' or 'active_wordpress_domain'".
- On a 14 GB site it returned 500 "Failed to Update Domain in WordPress" after writing `home` and `siteurl` but before replacing the CDN host in postmeta, options and other tables. `maindomain get` then reported `active_wordpress_domain: live_domain` although WordPress still served the CDN URL.
- Object Cache Pro (Rocket.net support installs it when asked to enable Redis, replacing Redis Object Cache) kept serving the old `home` and `siteurl` until `wp cache flush`. `wp option update home` reported "Could not update option" because the database already held the new value. `WP_REDIS_PATH` and `WP_REDIS_SCHEME` are not defined in wp-config with Object Cache Pro.
- The migration had rewritten every `wp_posts.guid` to the CDN host, so the RSS feed published CDN-host GUIDs until they were replaced.
- Finishing by hand: `wp search-replace <cdn host> <live domain> --all-tables-with-prefix --skip-columns=guid`, then the same on `wp_posts --include-columns=guid`, then `wp cache flush`, WP Rocket clear, `cache purge --wait`. Both ran in under a minute through the API channel.
- Apex DNS is one A record, `104.19.154.92` (support article 4404045615387). Never the site's `ftp_ip_address`, which answers no HTTPS for the custom domain. `104.19.155.92` also served the site when tested but is not documented.
- `maindomain status` lists an optional DCV CNAME for `www` (`_acme-challenge.www` to `<host>.<id>.dcv.cloudflare.com`) that pre-validates the `www` certificate before the CNAME moves.
- Redis cannot be enabled through the API or WP-CLI: `wp redis enable` fails with "Connection refused" until support sets it up.
