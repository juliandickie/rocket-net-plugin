#!/usr/bin/env python3
"""rocket - CLI for Rocket.net hosting management. Python 3 stdlib only."""
import os, json, time, sys, base64, argparse, urllib.request, urllib.error

# --- Constants ---

DEFAULT_CONFIG = os.path.expanduser("~/.config/rocket-net/config.json")
TOKEN_CACHE = os.path.expanduser("~/.config/rocket-net/.token")
DEFAULT_BASE = "https://api.rocket.net"
# Rocket.net is behind Cloudflare, which 403-bans the default Python-urllib UA (CF error 1010).
# Any non-default User-Agent passes; use an honest one. Overridable via env for flexibility.
USER_AGENT = os.environ.get("ROCKET_USER_AGENT", "rocket-net-cli/0.1.0")

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

def _run_op(op_id, path_args, args, cfg, endpoints, body=None):
    """Resolve op, guard destructive, call, optionally wait. Used by all subcommands."""
    url, meta = resolve_op(endpoints, op_id, path_args)
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

    # --- ssl ---
    sl = add(sub, "ssl", help="manage SSL certificates")
    slsub = sl.add_subparsers(dest="ssl_cmd", required=True)
    sllist = add(slsub, "list", help="list SSL certificates for a site")
    sllist.add_argument("site_id")
    sllist.set_defaults(func=cmd_ssl_list)

    # --- plugins ---
    pl = add(sub, "plugins", help="manage WordPress plugins")
    plsub = pl.add_subparsers(dest="plugins_cmd", required=True)
    pllist = add(plsub, "list", help="list plugins for a site")
    pllist.add_argument("site_id")
    pllist.set_defaults(func=cmd_plugins_list)

    # --- themes ---
    th = add(sub, "themes", help="manage WordPress themes")
    thsub = th.add_subparsers(dest="themes_cmd", required=True)
    thlist = add(thsub, "list", help="list themes for a site")
    thlist.add_argument("site_id")
    thlist.set_defaults(func=cmd_themes_list)

    # --- account ---
    ac = add(sub, "account", help="account information")
    acsub = ac.add_subparsers(dest="account_cmd", required=True)
    add(acsub, "me", help="get current account info").set_defaults(func=cmd_account_me)
    add(acsub, "usage", help="get account usage").set_defaults(func=cmd_account_usage)

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

def cmd_account_me(args, cfg, endpoints):
    return _run_op(OP_ACCOUNT_ME, {}, args, cfg, endpoints)

def cmd_account_usage(args, cfg, endpoints):
    return _run_op(OP_ACCOUNT_USAGE, {}, args, cfg, endpoints)


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
