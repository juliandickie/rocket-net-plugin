#!/usr/bin/env python3
"""rocket - CLI for Rocket.net hosting management. Python 3 stdlib only."""
import os, json, time, sys, base64, argparse, urllib.request, urllib.error

# --- Constants ---

DEFAULT_CONFIG = os.path.expanduser("~/.config/rocket-net/config.json")
TOKEN_CACHE = os.path.expanduser("~/.config/rocket-net/.token")
DEFAULT_BASE = "https://api.rocket.net"
# Rocket.net is behind Cloudflare, which 403-bans the default Python-urllib UA (CF error 1010).
# Any non-default User-Agent passes; use an honest one. Overridable via env for flexibility.
USER_AGENT = os.environ.get("ROCKET_USER_AGENT", "rocket-net-cli/0.1.1")

# --- Config ---

def load_config(path=DEFAULT_CONFIG):
    cfg = {}
    if os.path.exists(path):
        with open(path) as f:
            cfg = json.load(f)
    cfg["base_url"] = os.environ.get("ROCKET_BASE_URL", cfg.get("base_url", DEFAULT_BASE))
    if os.environ.get("ROCKETNET_USERNAME"):
        cfg["username"] = os.environ["ROCKETNET_USERNAME"]
    if os.environ.get("ROCKETNET_PASSWORD"):
        cfg["password"] = os.environ["ROCKETNET_PASSWORD"]
    return cfg

# --- Errors ---

class RocketError(Exception): pass
class AuthError(RocketError): pass
class APIError(RocketError):
    def __init__(self, status, message): super().__init__(f"{status}: {message}"); self.status = status

# --- HTTP helper ---

def http_request(method, url, token=None, body=None, timeout=30):
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if token: headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raise RocketError(f"non-JSON response from {url}: {raw[:200].decode(errors='replace')}")
    except urllib.error.HTTPError as e:
        msg = ""
        try: msg = e.read().decode()
        except Exception: pass
        if e.code == 401:
            raise AuthError(msg or "Unauthorized")
        raise APIError(e.code, msg or e.reason)
    except urllib.error.URLError as e:
        raise RocketError(f"network error: {e}")

# --- Auth and token cache ---

def jwt_exp(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))
    except Exception:
        return 0

def login(cfg):
    if not cfg.get("username") or not cfg.get("password"):
        raise AuthError("No api_token and no username/password in config. See ~/.config/rocket-net/config.json")
    base = cfg["base_url"]
    if not base.startswith("https://"):
        raise RocketError(f"refusing to send credentials over a non-HTTPS base_url: {base}")
    data = http_request("POST", base + "/v1/login",
                        body={"username": cfg["username"], "password": cfg["password"]})
    if "token" not in data:
        raise AuthError("login response missing token")
    return data["token"]

def _write_cache(path, token):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"token": token, "exp": jwt_exp(token)}, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)

def get_token(cfg, cache_path=TOKEN_CACHE, force=False):
    if os.environ.get("ROCKET_API_TOKEN"):
        return os.environ["ROCKET_API_TOKEN"]
    if not force and os.path.exists(cache_path):
        try:
            with open(cache_path) as fh:
                c = json.load(fh)
            if c.get("exp", 0) > time.time() + 60:
                return c["token"]
        except Exception:
            pass
    if cfg.get("api_token"):
        return cfg["api_token"]
    token = login(cfg)
    _write_cache(cache_path, token)
    return token

# --- Endpoint map (Task 2.1) ---

def load_endpoints(path=None):
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "rocket_endpoints.json")
    with open(path) as f:
        return json.load(f)

def resolve_op(endpoints, op_id, path_args):
    ops = endpoints["operations"]
    if op_id not in ops:
        raise RocketError(f"unknown operationId: {op_id}")
    meta = ops[op_id]
    path = meta["path"]
    for p in meta["path_params"]:
        if p not in path_args:
            raise RocketError(f"missing path param: {p}")
        path = path.replace("{" + p + "}", str(path_args[p]))
    return endpoints["base_url"].rstrip("/") + path, meta

# --- Auto-retry on 401 (Task 2.2) ---

def call_api(cfg, method, url, body=None, cache_path=TOKEN_CACHE, timeout=30):
    token = get_token(cfg, cache_path=cache_path)
    try:
        return http_request(method, url, token=token, body=body, timeout=timeout)
    except AuthError:
        token = get_token(cfg, cache_path=cache_path, force=True)  # re-login
        return http_request(method, url, token=token, body=body, timeout=timeout)

# --- Task polling with backoff (Task 2.3) ---

def _result(resp):
    """Unwrap the Rocket.net response envelope {success, result, ...}; return result if present."""
    if isinstance(resp, dict):
        if "result" in resp:
            return resp["result"]
        if "data" in resp:
            return resp["data"]
    return resp

def _find_task(data, task_id):
    items = _result(data)
    if isinstance(items, list):
        for t in items:
            if str(t.get("id")) == str(task_id):
                return t
        return None
    if isinstance(items, dict):
        return items if str(items.get("id")) == str(task_id) else None
    return None

def wait_for_task(cfg, site_id, task_id, interval=3.0, max_wait=600):
    base = cfg["base_url"].rstrip("/")
    url = f"{base}/v1/sites/{site_id}/tasks"
    waited, delay = 0.0, interval
    while waited < max_wait:
        data = call_api(cfg, "GET", url)
        task = _find_task(data, task_id)
        status = ((task or {}).get("task_status") or (task or {}).get("status") or "").lower()
        if status in ("complete", "completed", "done", "success"):
            return task
        if status in ("failed", "error"):
            raise RocketError(f"task {task_id} failed: {(task or {}).get('error', 'unknown')}")
        time.sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 15)
    raise RocketError(f"task {task_id} did not complete within {max_wait}s")

# --- Safety guards (Task 2.4) ---

def confirm_destructive(meta, assume_yes, interactive=True):
    if not meta.get("destructive"):
        return True
    if assume_yes:
        return True
    if interactive and sys.stdin.isatty():
        ans = input("This is a destructive operation. Type 'yes' to proceed: ")
        if ans.strip().lower() == "yes":
            return True
    sys.exit("Refused: destructive operation requires --yes (or interactive 'yes').")

def build_dry_run(method, url, body):
    return {"method": method, "url": url, "body": body}

# --- Shared subcommand helper (Phase 3) ---

def _run_op(op_id, path_args, args, cfg, endpoints, body=None, query=None):
    """Resolve op, guard destructive, call, optionally wait. Used by all subcommands."""
    url, meta = resolve_op(endpoints, op_id, path_args)
    if query:
        from urllib.parse import urlencode
        q = {k: v for k, v in query.items() if v is not None}
        if q:
            url = url + "?" + urlencode(q)
    if getattr(args, "dry_run", False):
        return build_dry_run(meta["method"], url, body)
    confirm_destructive(meta, getattr(args, "yes", False))
    result = call_api(cfg, meta["method"], url, body=body,
                      timeout=getattr(args, "timeout", 30))
    if getattr(args, "wait", False) and meta.get("returns_task"):
        site_id = path_args.get("id")
        payload = _result(result)
        # Only poll when a real task_id is returned. Some "create" ops (e.g. site create)
        # return the new resource id instead, which is not a task and must not be polled.
        tid = payload.get("task_id") if isinstance(payload, dict) else None
        if site_id and tid:
            result = wait_for_task(cfg, site_id, tid)
    return result

# --- Argparse and generic call command (Task 2.4) ---

def build_parser():
    # Global flags go AFTER the subcommand (e.g. `rocket sites list --json`,
    # `rocket site delete 99 --yes`). They live on a parent parser attached to each
    # subcommand. Placing them before the subcommand is not supported and errors loudly.
    flagp = argparse.ArgumentParser(add_help=False)
    flagp.add_argument("--config", default=DEFAULT_CONFIG)
    flagp.add_argument("--json", action="store_true", help="raw JSON output")
    flagp.add_argument("--yes", action="store_true", help="confirm destructive ops")
    flagp.add_argument("--dry-run", action="store_true")
    flagp.add_argument("--wait", action="store_true", help="poll resulting task to completion")
    flagp.add_argument("--timeout", type=int, default=30)

    p = argparse.ArgumentParser(prog="rocket", description="Rocket.net hosting CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(parent_sub, name, **kw):
        # every (sub)command also accepts the global flags after it
        return parent_sub.add_parser(name, parents=[flagp], **kw)

    c = add(sub, "call", help="invoke any endpoint by operationId")
    c.add_argument("op_id")
    c.add_argument("--param", action="append", default=[], help="path/query param k=v")
    c.add_argument("--data", help="JSON body, inline or @file.json")
    c.set_defaults(func=cmd_call)

    # --- sites ---
    s = add(sub, "sites", help="list or inspect sites")
    ssub = s.add_subparsers(dest="sites_cmd", required=True)
    add(ssub, "list", help="list all sites").set_defaults(func=cmd_sites_list)
    sg = add(ssub, "get", help="get a single site")
    sg.add_argument("site_id")
    sg.set_defaults(func=cmd_sites_get)

    # --- site (create / clone / delete) ---
    si = add(sub, "site", help="create, clone, or delete a site")
    sisub = si.add_subparsers(dest="site_cmd", required=True)

    sicr = add(sisub, "create", help="create a new site (returns the new site id)")
    sicr.add_argument("--name", help="WordPress site title (required unless --data)")
    sicr.add_argument("--location", type=int, help="location id (required unless --restricted-location or --data)")
    sicr.add_argument("--restricted-location", type=int, help="dedicated location id (instead of --location)")
    sicr.add_argument("--admin-username", help="WP admin username (required unless --template-id or --data)")
    sicr.add_argument("--admin-email", help="WP admin email (required unless --template-id or --data)")
    sicr.add_argument("--admin-password", help="WP admin password (auto-generated if omitted)")
    sicr.add_argument("--template-id", help="optional site template id")
    sicr.add_argument("--install-plugins", help="comma-separated plugin slugs to install")
    sicr.add_argument("--multisite", action="store_true", help="create as a multisite")
    sicr.add_argument("--data", dest="data", default=None, help="raw JSON body (overrides the flags above)")
    sicr.set_defaults(func=cmd_site_create)

    sicl = add(sisub, "clone", help="clone a site (returns task)")
    sicl.add_argument("site_id")
    sicl.add_argument("--label", help="label for the cloned site")
    sicl.add_argument("--location", type=int, help="location id for the clone")
    sicl.add_argument("--data", dest="data", default=None, help="raw JSON body (overrides the flags above)")
    sicl.set_defaults(func=cmd_site_clone)

    sidel = add(sisub, "delete", help="delete a site (destructive)")
    sidel.add_argument("site_id")
    sidel.set_defaults(func=cmd_site_delete)

    # --- staging ---
    st = add(sub, "staging", help="manage staging environments")
    stsub = st.add_subparsers(dest="staging_cmd", required=True)

    stcr = add(stsub, "create", help="create staging for a site (returns task)")
    stcr.add_argument("site_id")
    stcr.add_argument("--vanity-domain", action="store_true", help="use a vanity domain for staging")
    stcr.set_defaults(func=cmd_staging_create)

    stpub = add(stsub, "publish",
                help="publish staging to production (destructive, returns task)")
    stpub.add_argument("site_id")
    stpub.set_defaults(func=cmd_staging_publish)

    # --- wpcli ---
    wp = add(sub, "wpcli", help="run a WP-CLI command on a site")
    wp.add_argument("site_id")
    wp.add_argument("wp_args", nargs=argparse.REMAINDER,
                    help="WP-CLI args after --  e.g. wpcli 42 -- option get blogname")
    wp.set_defaults(func=cmd_wpcli)

    # --- backup ---
    bk = add(sub, "backup", help="manage backups")
    bksub = bk.add_subparsers(dest="backup_cmd", required=True)

    bklist = add(bksub, "list", help="list backups for a site")
    bklist.add_argument("site_id")
    bklist.set_defaults(func=cmd_backup_list)

    bkcr = add(bksub, "create", help="create a backup (returns task)")
    bkcr.add_argument("site_id")
    bkcr.add_argument("--label", required=True, help="a label for the backup")
    bkcr.add_argument("--no-files", action="store_true", help="exclude site files from the backup")
    bkcr.add_argument("--no-database", action="store_true", help="exclude the database from the backup")
    bkcr.set_defaults(func=cmd_backup_create)

    bkre = add(bksub, "restore",
               help="restore a backup (destructive, returns task)")
    bkre.add_argument("site_id")
    bkre.add_argument("backup_id")
    bkre.add_argument("--no-files", action="store_true", help="do not restore site files")
    bkre.add_argument("--no-database", action="store_true", help="do not restore the database")
    bkre.set_defaults(func=cmd_backup_restore)
    x = add(bksub, "get", help="get a backup"); x.add_argument("site_id"); x.add_argument("backup_id"); x.set_defaults(func=cmd_backup_get)
    x = add(bksub, "delete", help="delete a backup (destructive)"); x.add_argument("site_id"); x.add_argument("backup_id"); x.set_defaults(func=cmd_backup_delete)
    x = add(bksub, "automated", help="list automated backups"); x.add_argument("site_id"); x.set_defaults(func=cmd_backup_automated)
    x = add(bksub, "cloud-list", help="list cloud backups"); x.add_argument("site_id"); x.set_defaults(func=cmd_cloud_backup_list)

    # --- cache ---
    ca = add(sub, "cache", help="manage site cache")
    casub = ca.add_subparsers(dest="cache_cmd", required=True)

    capu = add(casub, "purge", help="purge ALL cached files for a site")
    capu.add_argument("site_id")
    capu.set_defaults(func=cmd_cache_purge)

    capf = add(casub, "purge-files", help="purge specific file URLs from cache")
    capf.add_argument("site_id")
    capf.add_argument("files", nargs="+", help="one or more file URLs to purge")
    capf.set_defaults(func=cmd_cache_purge_files)

    # --- domains ---
    dm = add(sub, "domains", help="manage site domains")
    dmsub = dm.add_subparsers(dest="domains_cmd", required=True)
    dmlist = add(dmsub, "list", help="list domains for a site")
    dmlist.add_argument("site_id")
    dmlist.set_defaults(func=cmd_domains_list)
    x = add(dmsub, "add", help="add an additional domain"); x.add_argument("site_id"); x.add_argument("--domain", required=True); x.set_defaults(func=cmd_domains_add)
    x = add(dmsub, "remove", help="remove a domain (destructive)"); x.add_argument("site_id"); x.add_argument("domain_id"); x.set_defaults(func=cmd_domains_remove)

    # --- ssl ---
    sl = add(sub, "ssl", help="manage SSL certificates")
    slsub = sl.add_subparsers(dest="ssl_cmd", required=True)
    sllist = add(slsub, "list", help="list SSL certificates for a site")
    sllist.add_argument("site_id")
    sllist.set_defaults(func=cmd_ssl_list)
    x = add(slsub, "get", help="get a certificate"); x.add_argument("site_id"); x.add_argument("certificate_id"); x.set_defaults(func=cmd_ssl_get)
    x = add(slsub, "upload", help="upload a custom SSL certificate"); x.add_argument("site_id"); x.add_argument("--domains", required=True, help="comma-separated domains"); x.add_argument("--certificate-file", required=True, help="path to the certificate PEM"); x.add_argument("--key-file", required=True, help="path to the private key PEM"); x.set_defaults(func=cmd_ssl_upload)
    x = add(slsub, "delete", help="delete a certificate (destructive)"); x.add_argument("site_id"); x.add_argument("certificate_id"); x.set_defaults(func=cmd_ssl_delete)

    # --- plugins ---
    pl = add(sub, "plugins", help="manage WordPress plugins")
    plsub = pl.add_subparsers(dest="plugins_cmd", required=True)
    pllist = add(plsub, "list", help="list plugins for a site")
    pllist.add_argument("site_id")
    pllist.set_defaults(func=cmd_plugins_list)
    x = add(plsub, "install", help="install plugins"); x.add_argument("site_id"); x.add_argument("--plugins", required=True, help="comma-separated slugs"); x.add_argument("--activate", action="store_true"); x.add_argument("--custom-url"); x.set_defaults(func=cmd_plugins_install)
    x = add(plsub, "update", help="update a plugin"); x.add_argument("site_id"); x.add_argument("--plugin", required=True); x.set_defaults(func=cmd_plugins_update)
    x = add(plsub, "set-status", help="activate or deactivate a plugin"); x.add_argument("site_id"); x.add_argument("--plugin", required=True); x.add_argument("--status", required=True, choices=["active", "inactive"]); x.set_defaults(func=cmd_plugins_status)
    x = add(plsub, "delete", help="delete plugins (destructive)"); x.add_argument("site_id"); x.add_argument("--plugins", required=True, help="comma-separated slugs"); x.set_defaults(func=cmd_plugins_delete)
    x = add(plsub, "search", help="search the plugin directory"); x.add_argument("site_id"); x.add_argument("--query", required=True); x.set_defaults(func=cmd_plugins_search)

    # --- themes ---
    th = add(sub, "themes", help="manage WordPress themes")
    thsub = th.add_subparsers(dest="themes_cmd", required=True)
    thlist = add(thsub, "list", help="list themes for a site")
    thlist.add_argument("site_id")
    thlist.set_defaults(func=cmd_themes_list)
    x = add(thsub, "install", help="install themes"); x.add_argument("site_id"); x.add_argument("--themes", required=True, help="comma-separated slugs"); x.add_argument("--activate", action="store_true"); x.add_argument("--custom-url"); x.set_defaults(func=cmd_themes_install)
    x = add(thsub, "update", help="update a theme"); x.add_argument("site_id"); x.add_argument("--theme", required=True); x.set_defaults(func=cmd_themes_update)
    x = add(thsub, "set-status", help="activate a theme"); x.add_argument("site_id"); x.add_argument("--theme", required=True); x.add_argument("--status", required=True); x.set_defaults(func=cmd_themes_status)
    x = add(thsub, "delete", help="delete themes (destructive)"); x.add_argument("site_id"); x.add_argument("--themes", required=True, help="comma-separated slugs"); x.set_defaults(func=cmd_themes_delete)
    x = add(thsub, "search", help="search the theme directory"); x.add_argument("site_id"); x.add_argument("--query", required=True); x.set_defaults(func=cmd_themes_search)

    # --- account ---
    ac = add(sub, "account", help="account information")
    acsub = ac.add_subparsers(dest="account_cmd", required=True)
    add(acsub, "me", help="get current account info").set_defaults(func=cmd_account_me)
    add(acsub, "usage", help="get account usage").set_defaults(func=cmd_account_usage)

    # --- mcp headers helper ---
    mh = add(sub, "mcp-headers", help="print {\"Authorization\": \"Bearer <jwt>\"} for Claude Code's headersHelper (refreshes the token when under 24h left)")
    mh.set_defaults(func=cmd_mcp_headers)

    # --- users ---
    u = add(sub, "users", help="manage site users")
    usub = u.add_subparsers(dest="users_cmd", required=True)
    x = add(usub, "list", help="list site users"); x.add_argument("site_id"); x.set_defaults(func=cmd_users_list)
    x = add(usub, "add", help="invite a user"); x.add_argument("site_id"); x.add_argument("--name", required=True); x.add_argument("--email", required=True); x.set_defaults(func=cmd_users_add)
    x = add(usub, "remove", help="remove a user (destructive)"); x.add_argument("site_id"); x.add_argument("user_id"); x.set_defaults(func=cmd_users_remove)

    # --- ssh ---
    sh = add(sub, "ssh", help="manage SSH keys")
    shsub = sh.add_subparsers(dest="ssh_cmd", required=True)
    x = add(shsub, "list", help="list SSH keys"); x.add_argument("site_id"); x.set_defaults(func=cmd_ssh_list)
    x = add(shsub, "add", help="import an SSH key"); x.add_argument("site_id"); x.add_argument("--name", required=True); x.add_argument("--key", help="public key text"); x.add_argument("--key-file", help="read the public key from a file"); x.add_argument("--passphrase"); x.set_defaults(func=cmd_ssh_add)
    x = add(shsub, "remove", help="delete an SSH key (destructive)"); x.add_argument("site_id"); x.add_argument("--name", required=True); x.set_defaults(func=cmd_ssh_remove)
    x = add(shsub, "authorize", help="authorize an SSH key"); x.add_argument("site_id"); x.add_argument("--name", required=True); x.set_defaults(func=cmd_ssh_authorize)
    x = add(shsub, "deauthorize", help="deauthorize an SSH key (destructive)"); x.add_argument("site_id"); x.add_argument("--name", required=True); x.set_defaults(func=cmd_ssh_deauthorize)

    # --- ftp ---
    ft = add(sub, "ftp", help="manage FTP accounts")
    ftsub = ft.add_subparsers(dest="ftp_cmd", required=True)
    x = add(ftsub, "list", help="list FTP accounts"); x.add_argument("site_id"); x.set_defaults(func=cmd_ftp_list)
    x = add(ftsub, "add", help="create an FTP account"); x.add_argument("site_id"); x.add_argument("--username", required=True); x.add_argument("--password", required=True); x.add_argument("--homedir", required=True); x.add_argument("--quota", type=int, required=True); x.add_argument("--domain", required=True); x.set_defaults(func=cmd_ftp_add)
    x = add(ftsub, "update", help="update an FTP account"); x.add_argument("site_id"); x.add_argument("--password"); x.add_argument("--quota", type=int); x.add_argument("--homedir"); x.set_defaults(func=cmd_ftp_update)
    x = add(ftsub, "remove", help="delete an FTP account (destructive)"); x.add_argument("site_id"); x.add_argument("--username", required=True); x.set_defaults(func=cmd_ftp_remove)

    # --- settings ---
    se = add(sub, "settings", help="site settings")
    sesub = se.add_subparsers(dest="settings_cmd", required=True)
    x = add(sesub, "get", help="get site settings"); x.add_argument("site_id"); x.set_defaults(func=cmd_settings_get)
    x = add(sesub, "schema", help="get the settings schema"); x.add_argument("site_id"); x.set_defaults(func=cmd_settings_schema)
    x = add(sesub, "update", help="update site settings"); x.add_argument("site_id"); x.add_argument("--php-version"); x.add_argument("--data", help="raw JSON settings body"); x.set_defaults(func=cmd_settings_update)

    # --- reporting ---
    rp = add(sub, "reporting", help="site reporting")
    rpsub = rp.add_subparsers(dest="reporting_cmd", required=True)
    x = add(rpsub, "bandwidth", help="bandwidth usage"); x.add_argument("site_id"); x.set_defaults(func=cmd_report_bandwidth)
    _DUR = ["30m", "1h", "6h", "12h", "24h", "72h", "7d", "30d"]
    x = add(rpsub, "visitors", help="visitor stats"); x.add_argument("site_id"); x.add_argument("--duration", default="7d", choices=_DUR); x.set_defaults(func=cmd_report_visitors)
    x = add(rpsub, "requests", help="total request counts"); x.add_argument("site_id"); x.add_argument("--duration", default="7d", choices=_DUR); x.set_defaults(func=cmd_report_requests)

    # --- password protection ---
    pw = add(sub, "pwprotect", help="site password protection")
    pwsub = pw.add_subparsers(dest="pwprotect_cmd", required=True)
    x = add(pwsub, "status", help="protection status"); x.add_argument("site_id"); x.set_defaults(func=cmd_pwp_status)
    x = add(pwsub, "enable", help="enable protection"); x.add_argument("site_id"); x.set_defaults(func=cmd_pwp_enable)
    x = add(pwsub, "disable", help="disable protection (destructive)"); x.add_argument("site_id"); x.set_defaults(func=cmd_pwp_disable)
    x = add(pwsub, "users", help="list protection users"); x.add_argument("site_id"); x.set_defaults(func=cmd_pwp_users)
    x = add(pwsub, "add-user", help="add a protection user"); x.add_argument("site_id"); x.add_argument("--username", required=True); x.add_argument("--password", required=True); x.set_defaults(func=cmd_pwp_add_user)
    x = add(pwsub, "remove-user", help="remove a protection user (destructive)"); x.add_argument("site_id"); x.add_argument("user_id"); x.set_defaults(func=cmd_pwp_remove_user)

    # --- single-shot reads ---
    x = add(sub, "credentials", help="get SFTP/SSH credentials for a site"); x.add_argument("site_id"); x.set_defaults(func=cmd_credentials)
    x = add(sub, "access-logs", help="get access logs for a site"); x.add_argument("site_id"); x.set_defaults(func=cmd_access_logs)
    md = add(sub, "maindomain", help="primary domain info")
    mdsub = md.add_subparsers(dest="maindomain_cmd", required=True)
    x = add(mdsub, "get", help="get the primary domain"); x.add_argument("site_id"); x.set_defaults(func=cmd_maindomain_get)
    x = add(mdsub, "status", help="primary domain status"); x.add_argument("site_id"); x.set_defaults(func=cmd_maindomain_status)

    return p

def _parse_params(pairs):
    out = {}
    for kv in pairs:
        k, _, v = kv.partition("=")
        out[k] = v
    return out

def _load_data(data):
    if not data: return None
    if data.startswith("@"):
        with open(data[1:]) as fh:
            return json.load(fh)
    return json.loads(data)

def _read_file(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError as ex:
        sys.exit(f"rocket: cannot read {path}: {ex}")

def cmd_call(args, cfg, endpoints):
    params = _parse_params(args.param)
    url, meta = resolve_op(endpoints, args.op_id, params)
    body = _load_data(args.data)
    query = {k: v for k, v in params.items() if k in meta.get("query_params", [])}
    if query:
        from urllib.parse import urlencode
        url = url + "?" + urlencode(query)
    if args.dry_run:
        return build_dry_run(meta["method"], url, body)
    confirm_destructive(meta, args.yes)
    result = call_api(cfg, meta["method"], url, body=body, timeout=args.timeout)
    if args.wait and meta.get("returns_task") and "id" in params:
        payload = _result(result)
        tid = payload.get("task_id") if isinstance(payload, dict) else None
        if tid:
            result = wait_for_task(cfg, params["id"], tid)
    return result

# --- Subcommand implementations (Phase 3) ---

OP_SITES_LIST    = "app.controllers.sites_controller.sites_get"
OP_SITES_GET     = "app.controllers.sites_controller.sites_id_get"
OP_SITE_CREATE   = "app.controllers.sites_controller.sites_post"
OP_SITE_CLONE    = "app.controllers.sites_controller.sites_id_clone_post"
OP_SITE_DELETE   = "app.controllers.sites_controller.sites_id_delete"
OP_STAGING_CREATE  = "app.controllers.sites_controller.sites_id_staging_post"
OP_STAGING_PUBLISH = "app.controllers.sites_controller.sites_id_staging_publish_post"
OP_WPCLI         = "app.controllers.wordpress_controller.sites_id_wpcli_post"
OP_BACKUP_LIST   = "app.controllers.backups_controller.sites_id_backup_get"
OP_BACKUP_CREATE = "app.controllers.backups_controller.sites_id_backup_post"
OP_BACKUP_RESTORE = "app.controllers.backups_controller.sites_id_backup_backup_id_restore_post"
OP_CACHE_PURGE   = "app.controllers.cdn_cache_controller.sites_id_cache_purge_post"
OP_CACHE_PURGE_ALL = "app.controllers.cdn_cache_controller.sites_id_cache_purge_everything_post"
OP_DOMAINS_LIST  = "app.controllers.domains_controller.sites_id_domains_get"
OP_SSL_LIST      = "app.controllers.custom_ssl_controller.sites_id_ssl_certificates_get"
OP_PLUGINS_LIST  = "app.controllers.plugins_controller.sites_id_plugins_get"
OP_THEMES_LIST   = "app.controllers.themes_controller.sites_id_themes_get"
OP_ACCOUNT_ME    = "app.controllers.account_controller.account_me_get"
OP_ACCOUNT_USAGE = "app.controllers.account_controller.account_usage_get"

# Long-tail operationIds (Phase 7)
OP_USERS_LIST = "app.controllers.site_users_controller.sites_id_users_get"
OP_USERS_ADD = "app.controllers.site_users_controller.sites_id_users_post"
OP_USERS_REMOVE = "app.controllers.site_users_controller.sites_id_users_user_id_delete"
OP_SSH_LIST = "app.controllers.ssh_keys_controller.sites_id_ssh_keys_get"
OP_SSH_ADD = "app.controllers.ssh_keys_controller.sites_id_ssh_keys_post"
OP_SSH_REMOVE = "app.controllers.ssh_keys_controller.sites_id_ssh_keys_delete"
OP_SSH_AUTHORIZE = "app.controllers.ssh_keys_controller.sites_id_ssh_keys_authorize_post"
OP_SSH_DEAUTHORIZE = "app.controllers.ssh_keys_controller.sites_id_ssh_keys_deauthorize_post"
OP_FTP_LIST = "app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_get"
OP_FTP_ADD = "app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_post"
OP_FTP_UPDATE = "app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_patch"
OP_FTP_REMOVE = "app.controllers.ftp_accounts_controller.sites_id_ftp_accounts_delete"
OP_PLUGINS_INSTALL = "app.controllers.plugins_controller.sites_id_plugins_post"
OP_PLUGINS_UPDATE = "app.controllers.plugins_controller.sites_id_plugins_put"
OP_PLUGINS_STATUS = "app.controllers.plugins_controller.sites_id_plugins_patch"
OP_PLUGINS_DELETE = "app.controllers.plugins_controller.sites_id_plugins_delete"
OP_PLUGINS_SEARCH = "app.controllers.plugins_controller.sites_id_plugins_search_get"
OP_THEMES_INSTALL = "app.controllers.themes_controller.sites_id_themes_post"
OP_THEMES_UPDATE = "app.controllers.themes_controller.sites_id_themes_put"
OP_THEMES_STATUS = "app.controllers.themes_controller.sites_id_themes_patch"
OP_THEMES_DELETE = "app.controllers.themes_controller.sites_id_themes_delete"
OP_THEMES_SEARCH = "app.controllers.themes_controller.sites_id_themes_search_get"
OP_DOMAINS_ADD = "app.controllers.domains_controller.sites_id_domains_post"
OP_DOMAINS_REMOVE = "app.controllers.domains_controller.sites_id_domains_domain_id_delete"
OP_SSL_GET = "app.controllers.custom_ssl_controller.sites_id_ssl_certificates_id_get"
OP_SSL_UPLOAD = "app.controllers.custom_ssl_controller.sites_id_ssl_certificates_post"
OP_SSL_DELETE = "app.controllers.custom_ssl_controller.sites_id_ssl_certificates_id_delete"
OP_SETTINGS_GET = "app.controllers.site_settings_controller.sites_id_settings_get"
OP_SETTINGS_SCHEMA = "app.controllers.site_settings_controller.sites_id_settings_schema_get"
OP_SETTINGS_UPDATE = "app.controllers.site_settings_controller.sites_id_settings_patch"
OP_BACKUP_GET = "app.controllers.backups_controller.sites_id_backup_backup_id_get"
OP_BACKUP_DELETE = "app.controllers.backups_controller.sites_id_backup_backup_id_delete"
OP_BACKUP_AUTOMATED = "app.controllers.backups_controller.sites_id_backup_automated_get"
OP_CLOUD_BACKUP_LIST = "app.controllers.cloud_backups_controller.sites_id_cloud_backups_get"
OP_CREDENTIALS = "app.controllers.sites_controller.sites_id_credentials_get"
OP_ACCESS_LOGS = "app.controllers.access_logs_controller.sites_id_access_logs_get"
OP_MAINDOMAIN_GET = "app.controllers.domains_controller.sites_id_maindomain_get"
OP_MAINDOMAIN_STATUS = "app.controllers.domains_controller.sites_id_maindomain_status_get"
OP_PWP_STATUS = "app.controllers.password_protection_controller.sites_id_password_protection_get"
OP_PWP_ENABLE = "app.controllers.password_protection_controller.sites_id_password_protection_post"
OP_PWP_DISABLE = "app.controllers.password_protection_controller.sites_id_password_protection_delete"
OP_PWP_USERS = "app.controllers.password_protection_controller.sites_id_password_protection_users_get"
OP_PWP_ADD_USER = "app.controllers.password_protection_controller.sites_id_password_protection_users_post"
OP_PWP_REMOVE_USER = "app.controllers.password_protection_controller.sites_id_password_protection_users_user_id_delete"
OP_REPORT_BANDWIDTH = "app.controllers.bandwidth_controller.sites_id_reporting_bandwidth_get"
OP_REPORT_VISITORS = "app.controllers.reporting_controller.reporting_sites_id_visitors_get"
OP_REPORT_REQUESTS = "app.controllers.reporting_controller.sites_id_reporting_total_requests_get"


def cmd_sites_list(args, cfg, endpoints):
    return _run_op(OP_SITES_LIST, {}, args, cfg, endpoints)

def cmd_sites_get(args, cfg, endpoints):
    return _run_op(OP_SITES_GET, {"id": args.site_id}, args, cfg, endpoints)

def cmd_site_create(args, cfg, endpoints):
    if getattr(args, "data", None):
        body = _load_data(args.data)
    else:
        if not args.name:
            sys.exit("rocket: site create requires --name (or --data). The API also needs "
                     "--location and (--admin-username + --admin-email) unless --template-id is used.")
        body = {"name": args.name}
        opt = {"location": args.location, "restricted_location": args.restricted_location,
               "admin_username": args.admin_username, "admin_email": args.admin_email,
               "admin_password": args.admin_password, "template_id": args.template_id,
               "install_plugins": args.install_plugins}
        for k, v in opt.items():
            if v is not None:
                body[k] = v
        if args.multisite:
            body["multisite"] = True
    return _run_op(OP_SITE_CREATE, {}, args, cfg, endpoints, body=body)

def cmd_site_clone(args, cfg, endpoints):
    # Clone is additive (creates a new site) and reversible, so it is not guarded.
    if getattr(args, "data", None):
        body = _load_data(args.data)
    else:
        body = {}
        if args.label:
            body["label"] = args.label
        if args.location is not None:
            body["location"] = args.location
    return _run_op(OP_SITE_CLONE, {"id": args.site_id}, args, cfg, endpoints, body=body)

def cmd_site_delete(args, cfg, endpoints):
    return _run_op(OP_SITE_DELETE, {"id": args.site_id}, args, cfg, endpoints)

def cmd_staging_create(args, cfg, endpoints):
    body = {"vanity_domain": bool(getattr(args, "vanity_domain", False))}
    return _run_op(OP_STAGING_CREATE, {"id": args.site_id}, args, cfg, endpoints, body=body)

def cmd_staging_publish(args, cfg, endpoints):
    return _run_op(OP_STAGING_PUBLISH, {"id": args.site_id}, args, cfg, endpoints)

def cmd_wpcli(args, cfg, endpoints):
    # Strip a leading '--' separator if present (e.g. wpcli 42 -- option get blogname)
    wp_args = args.wp_args
    if wp_args and wp_args[0] == "--":
        wp_args = wp_args[1:]
    command = " ".join(wp_args)
    body = {"command": command}
    return _run_op(OP_WPCLI, {"id": args.site_id}, args, cfg, endpoints, body=body)

def cmd_backup_list(args, cfg, endpoints):
    return _run_op(OP_BACKUP_LIST, {"id": args.site_id}, args, cfg, endpoints)

def cmd_backup_create(args, cfg, endpoints):
    body = {"label": args.label,
            "backup_directory": not args.no_files,
            "backup_database": not args.no_database}
    return _run_op(OP_BACKUP_CREATE, {"id": args.site_id}, args, cfg, endpoints, body=body)

def cmd_backup_restore(args, cfg, endpoints):
    body = {"backup_directory": not args.no_files,
            "backup_database": not args.no_database}
    return _run_op(OP_BACKUP_RESTORE,
                   {"id": args.site_id, "backup_id": args.backup_id},
                   args, cfg, endpoints, body=body)

def cmd_cache_purge(args, cfg, endpoints):
    # "purge" clears everything (the common intent); use purge-files for specific URLs.
    return _run_op(OP_CACHE_PURGE_ALL, {"id": args.site_id}, args, cfg, endpoints)

def cmd_cache_purge_files(args, cfg, endpoints):
    return _run_op(OP_CACHE_PURGE, {"id": args.site_id}, args, cfg, endpoints,
                   body={"files": args.files})

def cmd_domains_list(args, cfg, endpoints):
    return _run_op(OP_DOMAINS_LIST, {"id": args.site_id}, args, cfg, endpoints)

def cmd_ssl_list(args, cfg, endpoints):
    return _run_op(OP_SSL_LIST, {"id": args.site_id}, args, cfg, endpoints)

def cmd_plugins_list(args, cfg, endpoints):
    return _run_op(OP_PLUGINS_LIST, {"id": args.site_id}, args, cfg, endpoints)

def cmd_themes_list(args, cfg, endpoints):
    return _run_op(OP_THEMES_LIST, {"id": args.site_id}, args, cfg, endpoints)

def cmd_mcp_headers(args, cfg, endpoints):
    """Claude Code runs this on every MCP connect and again after a 401. Reuse the
    CLI's cache and login so the MCP and CLI share one credential file. Refresh
    early (under 24h left) so a long session never straddles the 7-day expiry."""
    token = get_token(cfg)
    if not os.environ.get("ROCKET_API_TOKEN") and jwt_exp(token) < time.time() + 24 * 3600:
        token = get_token(cfg, force=True)
    return {"Authorization": f"Bearer {token}"}

def cmd_account_me(args, cfg, endpoints):
    return _run_op(OP_ACCOUNT_ME, {}, args, cfg, endpoints)

def cmd_account_usage(args, cfg, endpoints):
    return _run_op(OP_ACCOUNT_USAGE, {}, args, cfg, endpoints)

# --- Long-tail subcommand implementations (Phase 7) ---

def cmd_users_list(a, c, e): return _run_op(OP_USERS_LIST, {"id": a.site_id}, a, c, e)
def cmd_users_add(a, c, e): return _run_op(OP_USERS_ADD, {"id": a.site_id}, a, c, e, body={"name": a.name, "email": a.email})
def cmd_users_remove(a, c, e): return _run_op(OP_USERS_REMOVE, {"id": a.site_id, "user_id": a.user_id}, a, c, e)

def cmd_ssh_list(a, c, e): return _run_op(OP_SSH_LIST, {"id": a.site_id}, a, c, e)
def cmd_ssh_add(a, c, e):
    key = a.key
    if getattr(a, "key_file", None):
        key = _read_file(a.key_file).strip()
    if not key:
        sys.exit("rocket: ssh add requires --key or --key-file")
    body = {"name": a.name, "key": key}
    if a.passphrase:
        body["passphrase"] = a.passphrase
    return _run_op(OP_SSH_ADD, {"id": a.site_id}, a, c, e, body=body)
def cmd_ssh_remove(a, c, e): return _run_op(OP_SSH_REMOVE, {"id": a.site_id}, a, c, e, body={"name": a.name})
def cmd_ssh_authorize(a, c, e): return _run_op(OP_SSH_AUTHORIZE, {"id": a.site_id}, a, c, e, body={"name": a.name})
def cmd_ssh_deauthorize(a, c, e): return _run_op(OP_SSH_DEAUTHORIZE, {"id": a.site_id}, a, c, e, body={"name": a.name})

def cmd_ftp_list(a, c, e): return _run_op(OP_FTP_LIST, {"id": a.site_id}, a, c, e)
def cmd_ftp_add(a, c, e):
    body = {"username": a.username, "password": a.password, "homedir": a.homedir,
            "quota": a.quota, "domain": a.domain}
    return _run_op(OP_FTP_ADD, {"id": a.site_id}, a, c, e, body=body)
def cmd_ftp_update(a, c, e):
    body = {}
    if a.password: body["new_password"] = a.password
    if a.quota is not None: body["quota"] = a.quota
    if a.homedir: body["homedir"] = a.homedir
    return _run_op(OP_FTP_UPDATE, {"id": a.site_id}, a, c, e, body=body)
def cmd_ftp_remove(a, c, e): return _run_op(OP_FTP_REMOVE, {"id": a.site_id}, a, c, e, body={"username": a.username})

def cmd_plugins_install(a, c, e):
    body = {"plugins": a.plugins}
    if a.activate: body["activate"] = True
    if getattr(a, "custom_url", None): body["custom_url"] = a.custom_url
    return _run_op(OP_PLUGINS_INSTALL, {"id": a.site_id}, a, c, e, body=body)
def cmd_plugins_update(a, c, e): return _run_op(OP_PLUGINS_UPDATE, {"id": a.site_id}, a, c, e, body={"plugin": a.plugin})
def cmd_plugins_status(a, c, e): return _run_op(OP_PLUGINS_STATUS, {"id": a.site_id}, a, c, e, body={"plugin": a.plugin, "status": a.status})
def cmd_plugins_delete(a, c, e): return _run_op(OP_PLUGINS_DELETE, {"id": a.site_id}, a, c, e, body={"plugins": a.plugins})
def cmd_plugins_search(a, c, e): return _run_op(OP_PLUGINS_SEARCH, {"id": a.site_id}, a, c, e, query={"query": a.query})

def cmd_themes_install(a, c, e):
    body = {"themes": a.themes}
    if a.activate: body["activate"] = True
    if getattr(a, "custom_url", None): body["custom_url"] = a.custom_url
    return _run_op(OP_THEMES_INSTALL, {"id": a.site_id}, a, c, e, body=body)
def cmd_themes_update(a, c, e): return _run_op(OP_THEMES_UPDATE, {"id": a.site_id}, a, c, e, body={"theme": a.theme})
def cmd_themes_status(a, c, e): return _run_op(OP_THEMES_STATUS, {"id": a.site_id}, a, c, e, body={"theme": a.theme, "status": a.status})
def cmd_themes_delete(a, c, e): return _run_op(OP_THEMES_DELETE, {"id": a.site_id}, a, c, e, body={"themes": a.themes})
def cmd_themes_search(a, c, e): return _run_op(OP_THEMES_SEARCH, {"id": a.site_id}, a, c, e, query={"query": a.query})

def cmd_domains_add(a, c, e): return _run_op(OP_DOMAINS_ADD, {"id": a.site_id}, a, c, e, body={"domain": a.domain})
def cmd_domains_remove(a, c, e): return _run_op(OP_DOMAINS_REMOVE, {"id": a.site_id, "domain_id": a.domain_id}, a, c, e)

def cmd_ssl_get(a, c, e): return _run_op(OP_SSL_GET, {"id": a.site_id, "certificate_id": a.certificate_id}, a, c, e)
def cmd_ssl_upload(a, c, e):
    cert = _read_file(a.certificate_file)
    key = _read_file(a.key_file)
    body = {"domains": [d.strip() for d in a.domains.split(",") if d.strip()],
            "certificate": cert, "key": key}
    return _run_op(OP_SSL_UPLOAD, {"id": a.site_id}, a, c, e, body=body)
def cmd_ssl_delete(a, c, e): return _run_op(OP_SSL_DELETE, {"id": a.site_id, "certificate_id": a.certificate_id}, a, c, e)

def cmd_settings_get(a, c, e): return _run_op(OP_SETTINGS_GET, {"id": a.site_id}, a, c, e)
def cmd_settings_schema(a, c, e): return _run_op(OP_SETTINGS_SCHEMA, {"id": a.site_id}, a, c, e)
def cmd_settings_update(a, c, e):
    if getattr(a, "data", None):
        body = _load_data(a.data)
    else:
        body = {}
        if a.php_version:
            body["new_php_version"] = a.php_version
        if not body:
            sys.exit("rocket: settings update requires --php-version or --data")
    return _run_op(OP_SETTINGS_UPDATE, {"id": a.site_id}, a, c, e, body=body)

def cmd_backup_get(a, c, e): return _run_op(OP_BACKUP_GET, {"id": a.site_id, "backup_id": a.backup_id}, a, c, e)
def cmd_backup_delete(a, c, e): return _run_op(OP_BACKUP_DELETE, {"id": a.site_id, "backup_id": a.backup_id}, a, c, e)
def cmd_backup_automated(a, c, e): return _run_op(OP_BACKUP_AUTOMATED, {"id": a.site_id}, a, c, e)
def cmd_cloud_backup_list(a, c, e): return _run_op(OP_CLOUD_BACKUP_LIST, {"id": a.site_id}, a, c, e)

def cmd_credentials(a, c, e): return _run_op(OP_CREDENTIALS, {"id": a.site_id}, a, c, e)
def cmd_access_logs(a, c, e): return _run_op(OP_ACCESS_LOGS, {"id": a.site_id}, a, c, e)
def cmd_maindomain_get(a, c, e): return _run_op(OP_MAINDOMAIN_GET, {"id": a.site_id}, a, c, e)
def cmd_maindomain_status(a, c, e): return _run_op(OP_MAINDOMAIN_STATUS, {"id": a.site_id}, a, c, e)

def cmd_pwp_status(a, c, e): return _run_op(OP_PWP_STATUS, {"id": a.site_id}, a, c, e)
def cmd_pwp_enable(a, c, e): return _run_op(OP_PWP_ENABLE, {"id": a.site_id}, a, c, e)
def cmd_pwp_disable(a, c, e): return _run_op(OP_PWP_DISABLE, {"id": a.site_id}, a, c, e)
def cmd_pwp_users(a, c, e): return _run_op(OP_PWP_USERS, {"id": a.site_id}, a, c, e)
def cmd_pwp_add_user(a, c, e): return _run_op(OP_PWP_ADD_USER, {"id": a.site_id}, a, c, e, body={"username": a.username, "password": a.password})
def cmd_pwp_remove_user(a, c, e): return _run_op(OP_PWP_REMOVE_USER, {"id": a.site_id, "user_id": a.user_id}, a, c, e)

def cmd_report_bandwidth(a, c, e): return _run_op(OP_REPORT_BANDWIDTH, {"id": a.site_id}, a, c, e)
def cmd_report_visitors(a, c, e): return _run_op(OP_REPORT_VISITORS, {"id": a.site_id}, a, c, e, query={"duration": a.duration})
def cmd_report_requests(a, c, e): return _run_op(OP_REPORT_REQUESTS, {"id": a.site_id}, a, c, e, query={"duration": a.duration})


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    endpoints = load_endpoints()
    try:
        out = args.func(args, cfg, endpoints)
    except RocketError as e:
        sys.exit(f"rocket: {e}")
    print(json.dumps(out, indent=2) if not args.json else json.dumps(out))

if __name__ == "__main__":
    main()
