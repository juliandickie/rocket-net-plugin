# rocket-net Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin that manages Rocket.net WordPress hosting both conversationally (bundled remote MCP) and via a deterministic single-file Python CLI, with skills and commands as the workflow layer.

**Architecture:** Hybrid. Layer A bundles Rocket.net's remote HTTP MCP (`https://mcp.rocket.net/mcp`) via `.mcp.json`. Layer B is `bin/rocket.py`, a zero-dependency Python stdlib CLI that authenticates (JWT with caching and refresh), reaches all 139 endpoints through a spec-driven generic `call` plus ergonomic subcommands, and polls async background tasks. Layer C is 12 skills and 5 commands that orchestrate A and B with safety rails.

**Tech Stack:** Python 3 standard library only (`urllib`, `json`, `argparse`, `unittest`, `concurrent.futures`). Markdown for skills and commands. JSON for manifest, MCP config, and the generated endpoint map.

**Spec:** `docs/superpowers/specs/2026-06-10-rocket-net-plugin-design.md`

---

## Git and commit policy

Per Julian's standing rule, commits happen ONLY when Julian asks. The repo is not yet git-initialized. The commit steps below mark where a commit belongs; when executing, complete the task and PAUSE at the commit step for Julian's go-ahead rather than committing unprompted. Once Julian approves committing for the session, run the commit steps as written.

## Verified facts (resolved from official docs on 2026-06-10)

- Manifest `.claude-plugin/plugin.json`: only `name` required (kebab-case). Optional `displayName`, `version`, `description`, `author{name,email,url}`, `homepage`, `repository`, `license`, `keywords`, `defaultEnabled`, plus component-path and `userConfig` fields.
- `defaultEnabled: false` (Claude Code v2.1.154+) ships the plugin installed-but-disabled, intended for plugins that connect to an external service. We use it.
- `userConfig` option fields: `type` (string/number/boolean/directory/file), `title` (req), `description` (req), `sensitive` (masks input, stores in OS keychain), `required`, `default`. Referenced as `${user_config.KEY}` in `.mcp.json` and exported as `CLAUDE_PLUGIN_OPTION_<KEY>` to subprocesses.
- `.mcp.json` remote HTTP server: `{ "type": "http", "url": "...", "headers": { ... } }`. `streamable-http` is an accepted alias for `http`. `${user_config.KEY}` substitution works in `headers`.
- Rocket.net auth: `POST /v1/login` with `{username, password}` returns `{token}` (JWT, 7-day expiry). 401 means expired or revoked.
- Spec has 198 operations across 139 paths, all operationIds unique, so the generic `call` keys on operationId.
- Local testing: `claude --plugin-dir ./rocket-net-plugin` then `/reload-plugins`. Validate with `claude plugin validate ./rocket-net-plugin --strict`.

## File structure (what each file is responsible for)

| File | Responsibility |
|---|---|
| `.claude-plugin/plugin.json` | Manifest, metadata, `userConfig` for MCP creds, `defaultEnabled:false` |
| `.mcp.json` | Bundles Rocket.net remote HTTP MCP |
| `bin/rocket.py` | The CLI: config/auth, HTTP client, error handling, generic `call`, task polling, subcommands |
| `bin/rocket_endpoints.json` | Generated operationId -> {method, path, params, destructive, returns_task} map (runtime artifact) |
| `scripts/build_endpoints.py` | Dev-time YAML spec -> endpoints JSON converter (only place YAML is parsed) |
| `scripts/test-smoke.sh` | Gated live end-to-end check against a staging/test site |
| `tests/test_rocket.py` | unittest suite for the CLI core (auth, token cache, http, call, polling, safety) |
| `skills/<name>/SKILL.md` | Workflow knowledge (12 skills) |
| `commands/*.md` | 5 slash actions |
| `reference/rocket-openapi.yaml` | Source of truth (already present) |
| `.gitignore`, `.env.example`, `README.md` | Hygiene, credential template, current-state docs |

---

## Phase 0 - Scaffold

### Task 0.1 - Initialize repo skeleton and git

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `bin/`, `tests/`, `scripts/`, `skills/`, `commands/` (directories)

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Secrets and local config (creds live in ~/.config/rocket-net/, never here)
*.token
.env
.env.local
# Local-only dev notes
docs/dev/
# Python
__pycache__/
*.pyc
.pytest_cache/
# OS
.DS_Store
```

- [ ] **Step 2: Create `README.md` skeleton**

```markdown
# rocket-net

A Claude Code plugin to manage Rocket.net WordPress hosting - conversationally via Rocket.net's bundled MCP, and deterministically via a Python CLI.

Status: in development. See `docs/superpowers/specs/2026-06-10-rocket-net-plugin-design.md`.

## Credentials
Create `~/.config/rocket-net/config.json` (chmod 600) with either Rocket.net `username`+`password` (recommended, auto-refreshes the 7-day JWT) or a manual `api_token`. See `.env.example`.
```

- [ ] **Step 3: Create directories**

Run: `mkdir -p bin tests scripts skills commands`
Expected: directories exist.

- [ ] **Step 4: Initialize git (PAUSE for Julian before committing)**

Run: `git init`
Then PAUSE. Do not commit until Julian approves. When approved:
```bash
git add .gitignore README.md
git commit -m "chore: scaffold rocket-net plugin skeleton"
```

### Task 0.2 - Manifest and bundled MCP

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.mcp.json`
- Create: `.env.example`

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "rocket-net",
  "displayName": "Rocket.net Hosting",
  "version": "0.1.0",
  "description": "Manage Rocket.net WordPress hosting - site lifecycle, staging and deploys, WP-CLI, backups, and more.",
  "author": { "name": "Pro Marketing", "url": "https://promarketing.co" },
  "license": "MIT",
  "keywords": ["rocket.net", "wordpress", "hosting", "wp-cli", "deployment"],
  "defaultEnabled": false,
  "userConfig": {
    "rocketnet_username": {
      "type": "string",
      "title": "Rocket.net email",
      "description": "Email for your Rocket.net account. Used by the bundled MCP to mint and refresh API tokens.",
      "required": true
    },
    "rocketnet_password": {
      "type": "string",
      "title": "Rocket.net password",
      "description": "Password for your Rocket.net account. Stored in your OS keychain, never written to a file.",
      "sensitive": true,
      "required": true
    }
  }
}
```

- [ ] **Step 2: Create `.mcp.json`**

```json
{
  "mcpServers": {
    "rocket-net": {
      "type": "http",
      "url": "https://mcp.rocket.net/mcp",
      "headers": {
        "ROCKETNET_USERNAME": "${user_config.rocketnet_username}",
        "ROCKETNET_PASSWORD": "${user_config.rocketnet_password}"
      }
    }
  }
}
```

- [ ] **Step 3: Create `.env.example`**

```bash
# rocket-net CLI credentials template.
# Real credentials live in ~/.config/rocket-net/config.json (chmod 600), NOT in the repo.
# Option 1 (recommended): username + password (auto-refreshes the 7-day JWT)
#   ROCKETNET_USERNAME=you@example.com
#   ROCKETNET_PASSWORD=...
# Option 2: a JWT you minted yourself (expires in 7 days)
#   ROCKET_API_TOKEN=eyJ...
# Optional override:
#   ROCKET_BASE_URL=https://api.rocket.net
```

- [ ] **Step 4: Validate the manifest**

Run: `claude plugin validate ./rocket-net-plugin --strict`
Expected: passes (no errors). If `defaultEnabled` or `userConfig` warns, the local Claude Code is older than v2.1.154 - note it and continue; the plugin still loads.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add .claude-plugin/plugin.json .mcp.json .env.example
git commit -m "feat: add plugin manifest and bundled Rocket.net MCP"
```

### Task 0.3 - Generate the endpoint map

**Files:**
- Create: `scripts/build_endpoints.py`
- Create: `bin/rocket_endpoints.json` (generated output)

- [ ] **Step 1: Write `scripts/build_endpoints.py`**

The spec is large YAML. This dev script parses it and emits a compact JSON map. It is the ONLY place YAML is parsed, so it may use PyYAML if available, else fall back to a vendored parse. Prefer PyYAML at build time (developer machine), since the output JSON is committed and the shipped CLI never needs YAML.

```python
#!/usr/bin/env python3
"""Convert reference/rocket-openapi.yaml into bin/rocket_endpoints.json.
Run on the dev machine whenever the spec changes. Requires PyYAML at build time only."""
import json, os, sys
try:
    import yaml
except ImportError:
    sys.exit("Install PyYAML to run the build: pip install pyyaml (build-time only)")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "reference", "rocket-openapi.yaml")
OUT = os.path.join(ROOT, "bin", "rocket_endpoints.json")

DESTRUCTIVE_HINTS = ("delete", "cancel", "restore", "publish", "purge", "reset", "transfer", "deauthorize")

def main():
    with open(SPEC) as f:
        spec = yaml.safe_load(f)
    ops = {}
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            opid = op.get("operationId")
            if not opid:
                continue
            params = [p.get("name") for p in op.get("parameters", []) if "name" in p]
            has_body = "requestBody" in op
            summary = op.get("summary", "")
            destructive = method == "delete" or any(h in (opid + " " + summary).lower() for h in DESTRUCTIVE_HINTS)
            returns_task = any(k in (opid + " " + summary).lower() for k in ("create", "clone", "restore", "publish"))
            ops[opid] = {
                "method": method.upper(),
                "path": path,
                "path_params": [seg.strip("{}") for seg in path.split("/") if seg.startswith("{")],
                "query_params": params,
                "has_body": has_body,
                "summary": summary,
                "destructive": destructive,
                "returns_task": returns_task,
            }
    with open(OUT, "w") as f:
        json.dump({"base_url": "https://api.rocket.net", "operations": ops}, f, indent=2, sort_keys=True)
    print(f"Wrote {len(ops)} operations to {OUT}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the build**

Run: `cd <plugin-root> && python3 scripts/build_endpoints.py`
Expected: `Wrote 198 operations to .../bin/rocket_endpoints.json` (or close to 198).

- [ ] **Step 3: Sanity check the output**

Run: `python3 -c "import json; d=json.load(open('bin/rocket_endpoints.json')); print(len(d['operations'])); print(d['operations'].get('app.controllers.authentication_controller.login_post'))"`
Expected: count near 198 and a dict for the login op with method POST and path /v1/login.

- [ ] **Step 4: Commit (PAUSE for Julian)**

```bash
git add scripts/build_endpoints.py bin/rocket_endpoints.json
git commit -m "feat: generate operationId endpoint map from OpenAPI spec"
```

---

## Phase 1 - CLI core (config, auth, HTTP)

All Phase 1 and 2 tasks are TDD. Tests use `unittest` and `unittest.mock` to patch the HTTP layer so no network is hit. Run the suite with `python3 -m unittest tests.test_rocket -v`.

### Task 1.1 - Config loading with env precedence

**Files:**
- Create: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
import os, json, tempfile, unittest
from unittest import mock
import importlib.util

def load_module():
    spec = importlib.util.spec_from_file_location("rocket", os.path.join(os.path.dirname(__file__), "..", "bin", "rocket.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as d:
            cfgpath = os.path.join(d, "config.json")
            json.dump({"username": "file@x.com", "password": "filepw", "base_url": "https://api.rocket.net"}, open(cfgpath, "w"))
            with mock.patch.dict(os.environ, {"ROCKET_BASE_URL": "https://override.example"}):
                cfg = self.rocket.load_config(cfgpath)
        self.assertEqual(cfg["username"], "file@x.com")
        self.assertEqual(cfg["base_url"], "https://override.example")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestConfig -v`
Expected: FAIL (module has no `load_config`).

- [ ] **Step 3: Write minimal implementation in `bin/rocket.py`**

```python
#!/usr/bin/env python3
"""rocket - CLI for Rocket.net hosting management. Python 3 stdlib only."""
import os, json, time, sys, base64, argparse, urllib.request, urllib.error

DEFAULT_CONFIG = os.path.expanduser("~/.config/rocket-net/config.json")
TOKEN_CACHE = os.path.expanduser("~/.config/rocket-net/.token")
DEFAULT_BASE = "https://api.rocket.net"

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestConfig -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): config loading with env precedence"
```

### Task 1.2 - HTTP request helper with JSON and error mapping

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestHttp(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_request_parses_json(self):
        fake = mock.MagicMock()
        fake.read.return_value = b'{"ok": true}'
        fake.__enter__.return_value = fake
        with mock.patch("urllib.request.urlopen", return_value=fake):
            out = self.rocket.http_request("GET", "https://api.rocket.net/v1/sites", token="t")
        self.assertEqual(out, {"ok": True})

    def test_401_raises_autherror(self):
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(self.rocket.AuthError):
                self.rocket.http_request("GET", "https://api.rocket.net/v1/sites", token="t")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestHttp -v`
Expected: FAIL (no `http_request` / `AuthError`).

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
class RocketError(Exception): pass
class AuthError(RocketError): pass
class APIError(RocketError):
    def __init__(self, status, message): super().__init__(f"{status}: {message}"); self.status = status

def http_request(method, url, token=None, body=None, timeout=30):
    headers = {"Accept": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = ""
        try: msg = e.read().decode()
        except Exception: pass
        if e.code == 401:
            raise AuthError(msg or "Unauthorized")
        raise APIError(e.code, msg or e.reason)
    except urllib.error.URLError as e:
        raise RocketError(f"network error: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestHttp -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): http helper with json parsing and error mapping"
```

### Task 1.3 - Login, JWT expiry decode, and token cache

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestAuth(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_jwt_exp_decoded(self):
        # payload {"exp": 9999999999}
        import base64, json as j
        payload = base64.urlsafe_b64encode(j.dumps({"exp": 9999999999}).encode()).rstrip(b"=").decode()
        tok = f"h.{payload}.s"
        self.assertEqual(self.rocket.jwt_exp(tok), 9999999999)

    def test_get_token_uses_env_token_first(self):
        with mock.patch.dict(os.environ, {"ROCKET_API_TOKEN": "envtok"}):
            self.assertEqual(self.rocket.get_token({}, cache_path="/nonexistent"), "envtok")

    def test_get_token_logs_in_when_needed(self):
        cfg = {"username": "u", "password": "p", "base_url": "https://api.rocket.net"}
        with mock.patch.object(self.rocket, "http_request", return_value={"token": "fresh"}) as hr, \
             tempfile.TemporaryDirectory() as d:
            tok = self.rocket.get_token(cfg, cache_path=os.path.join(d, ".token"))
        self.assertEqual(tok, "fresh")
        hr.assert_called_once()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestAuth -v`
Expected: FAIL.

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
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
    data = http_request("POST", cfg["base_url"] + "/v1/login",
                        body={"username": cfg["username"], "password": cfg["password"]})
    if "token" not in data:
        raise AuthError("login response missing token")
    return data["token"]

def _write_cache(path, token):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"token": token, "exp": jwt_exp(token)}, f)
    os.chmod(path, 0o600)

def get_token(cfg, cache_path=TOKEN_CACHE, force=False):
    if os.environ.get("ROCKET_API_TOKEN"):
        return os.environ["ROCKET_API_TOKEN"]
    if not force and os.path.exists(cache_path):
        try:
            c = json.load(open(cache_path))
            if c.get("exp", 0) > time.time() + 60:
                return c["token"]
        except Exception:
            pass
    if cfg.get("api_token"):
        return cfg["api_token"]
    token = login(cfg)
    _write_cache(cache_path, token)
    return token
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestAuth -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): login, jwt expiry decode, token cache"
```

---

## Phase 2 - Generic call, task polling, safety

### Task 2.1 - Generic `call` resolving operationId from the endpoint map

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestCall(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()
        self.ops = {"operations": {
            "sites_get": {"method": "GET", "path": "/v1/sites", "path_params": [], "query_params": ["page"], "has_body": False, "destructive": False, "returns_task": False},
            "site_clone": {"method": "POST", "path": "/v1/sites/{id}/clone", "path_params": ["id"], "query_params": [], "has_body": True, "destructive": True, "returns_task": True}
        }, "base_url": "https://api.rocket.net"}

    def test_builds_url_with_path_params(self):
        url, meta = self.rocket.resolve_op(self.ops, "site_clone", {"id": "42"})
        self.assertEqual(url, "https://api.rocket.net/v1/sites/42/clone")
        self.assertTrue(meta["destructive"])

    def test_unknown_op_errors(self):
        with self.assertRaises(self.rocket.RocketError):
            self.rocket.resolve_op(self.ops, "nope", {})
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestCall -v`
Expected: FAIL.

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestCall -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): resolve operationId to url and metadata"
```

### Task 2.2 - 401 auto-refresh-and-retry wrapper

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestRetry(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_call_api_retries_once_on_401(self):
        cfg = {"username": "u", "password": "p", "base_url": "https://api.rocket.net"}
        seq = [self.rocket.AuthError("expired"), {"ok": True}]
        def fake_http(method, url, token=None, body=None, timeout=30):
            r = seq.pop(0)
            if isinstance(r, Exception): raise r
            return r
        with mock.patch.object(self.rocket, "http_request", side_effect=fake_http), \
             mock.patch.object(self.rocket, "get_token", side_effect=["t1", "t2"]):
            out = self.rocket.call_api(cfg, "GET", "https://api.rocket.net/v1/sites")
        self.assertEqual(out, {"ok": True})
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestRetry -v`
Expected: FAIL.

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
def call_api(cfg, method, url, body=None, cache_path=TOKEN_CACHE, timeout=30):
    token = get_token(cfg, cache_path=cache_path)
    try:
        return http_request(method, url, token=token, body=body, timeout=timeout)
    except AuthError:
        token = get_token(cfg, cache_path=cache_path, force=True)  # re-login
        return http_request(method, url, token=token, body=body, timeout=timeout)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestRetry -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): auto re-login and retry once on 401"
```

### Task 2.3 - Task polling with backoff

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestPoll(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_polls_until_complete(self):
        cfg = {"base_url": "https://api.rocket.net"}
        states = [{"status": "running"}, {"status": "running"}, {"status": "complete"}]
        with mock.patch.object(self.rocket, "call_api", side_effect=states), \
             mock.patch("time.sleep"):
            out = self.rocket.wait_for_task(cfg, site_id="1", task_id="9", interval=0.01, max_wait=5)
        self.assertEqual(out["status"], "complete")

    def test_raises_on_failed(self):
        cfg = {"base_url": "https://api.rocket.net"}
        with mock.patch.object(self.rocket, "call_api", return_value={"status": "failed", "error": "boom"}), \
             mock.patch("time.sleep"):
            with self.assertRaises(self.rocket.RocketError):
                self.rocket.wait_for_task(cfg, site_id="1", task_id="9", interval=0.01, max_wait=5)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestPoll -v`
Expected: FAIL.

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
def wait_for_task(cfg, site_id, task_id, interval=3.0, max_wait=600):
    base = cfg["base_url"].rstrip("/")
    url = f"{base}/v1/sites/{site_id}/tasks"
    waited, delay = 0.0, interval
    while waited < max_wait:
        data = call_api(cfg, "GET", url)
        task = _find_task(data, task_id)
        status = (task or {}).get("status", "").lower()
        if status in ("complete", "completed", "done", "success"):
            return task
        if status in ("failed", "error"):
            raise RocketError(f"task {task_id} failed: {(task or {}).get('error', 'unknown')}")
        time.sleep(delay)
        waited += delay
        delay = min(delay * 1.5, 15)
    raise RocketError(f"task {task_id} did not complete within {max_wait}s")

def _find_task(data, task_id):
    items = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(items, list):
        for t in items:
            if str(t.get("id")) == str(task_id):
                return t
        return None
    return items if str(items.get("id")) == str(task_id) else items
```

Note: `_find_task` shape may need adjustment once we see a real `/tasks` response in Task 6.1. The unit test fixes the contract; the smoke test validates against reality.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestPoll -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): background task polling with backoff"
```

### Task 2.4 - argparse skeleton, generic `call` command, global flags, destructive guard

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestGuard(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_destructive_requires_yes(self):
        meta = {"destructive": True}
        with self.assertRaises(SystemExit):
            self.rocket.confirm_destructive(meta, assume_yes=False, interactive=False)

    def test_dry_run_returns_request_dict(self):
        out = self.rocket.build_dry_run("POST", "https://api.rocket.net/v1/sites/1/clone", {"name": "x"})
        self.assertEqual(out["method"], "POST")
        self.assertIn("clone", out["url"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestGuard -v`
Expected: FAIL.

- [ ] **Step 3: Write implementation in `bin/rocket.py`**

```python
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

def build_parser():
    p = argparse.ArgumentParser(prog="rocket", description="Rocket.net hosting CLI")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--json", action="store_true", help="raw JSON output")
    p.add_argument("--yes", action="store_true", help="confirm destructive ops")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--wait", action="store_true", help="poll resulting task to completion")
    p.add_argument("--timeout", type=int, default=30)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("call", help="invoke any endpoint by operationId")
    c.add_argument("op_id")
    c.add_argument("--param", action="append", default=[], help="path/query param k=v")
    c.add_argument("--data", help="JSON body, inline or @file.json")
    c.set_defaults(func=cmd_call)
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
        return json.load(open(data[1:]))
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
        tid = result.get("task_id") or result.get("id")
        if tid:
            result = wait_for_task(cfg, params["id"], tid)
    return result

def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    endpoints = load_endpoints()
    out = args.func(args, cfg, endpoints)
    print(json.dumps(out, indent=2) if not args.json else json.dumps(out))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestGuard -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m unittest tests.test_rocket -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): argparse, generic call command, dry-run, destructive guard"
```

---

## Phase 3 - Ergonomic subcommands

Each subcommand is a thin wrapper that maps friendly args to a `cmd_call`-style invocation against a known operationId, reusing the Phase 2 plumbing. Add them to `build_parser` and give each a `cmd_*` function. Pattern shown for `sites`; the table lists the rest with their operationIds.

### Task 3.1 - `sites` subcommand (the canonical pattern)

**Files:**
- Modify: `bin/rocket.py`
- Test: `tests/test_rocket.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSites(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()
        self.endpoints = self.rocket.load_endpoints()

    def test_sites_list_calls_get(self):
        cfg = {"base_url": "https://api.rocket.net"}
        with mock.patch.object(self.rocket, "call_api", return_value={"data": []}) as ca:
            args = self.rocket.build_parser().parse_args(["sites", "list"])
            out = args.func(args, cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "GET")
        self.assertTrue(url.endswith("/v1/sites"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest tests.test_rocket.TestSites -v`
Expected: FAIL.

- [ ] **Step 3: Implement `sites` in `bin/rocket.py`**

Add to `build_parser` before `return p`:

```python
    s = sub.add_parser("sites", help="manage sites")
    ssub = s.add_subparsers(dest="sites_cmd", required=True)
    ssub.add_parser("list").set_defaults(func=cmd_sites_list)
    g = ssub.add_parser("get"); g.add_argument("site_id"); g.set_defaults(func=cmd_sites_get)
```

Add functions:

```python
def cmd_sites_list(args, cfg, endpoints):
    url, _ = resolve_op(endpoints, "app.controllers.sites_controller.sites_get", {})
    return call_api(cfg, "GET", url, timeout=args.timeout)

def cmd_sites_get(args, cfg, endpoints):
    url, _ = resolve_op(endpoints, "app.controllers.sites_controller.site_get", {"id": args.site_id})
    return call_api(cfg, "GET", url, timeout=args.timeout)
```

Note: confirm the exact operationIds for list and get from `bin/rocket_endpoints.json` before writing (grep it). Replace the strings above with the real operationIds if they differ.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m unittest tests.test_rocket.TestSites -v`
Expected: PASS.

- [ ] **Step 5: Commit (PAUSE for Julian)**

```bash
git add bin/rocket.py tests/test_rocket.py
git commit -m "feat(cli): sites subcommand"
```

### Task 3.2 - Remaining subcommands

For each row, add a subparser and a `cmd_*` function following the Task 3.1 pattern, look up the real operationId in `bin/rocket_endpoints.json`, and add one happy-path test asserting method and URL. Mark destructive operations so they pass through `confirm_destructive`.

| Subcommand | Action(s) | Endpoint path(s) | Destructive | Task |
|---|---|---|---|---|
| `site create` | create | POST /v1/sites | no (returns task) | --wait supported |
| `site clone` | clone | POST /v1/sites/{id}/clone | yes | --wait |
| `site delete` | delete | DELETE /v1/sites/{id} | yes | - |
| `staging create` | create staging | POST /v1/sites/{id}/staging | no | --wait |
| `staging publish` | publish to prod | POST /v1/sites/{id}/staging/publish | yes | --wait |
| `wpcli` | run wp-cli | POST /v1/sites/{id}/wpcli | depends on command | pass-through |
| `backup list/create` | backups | GET/POST /v1/sites/{id}/backup | create no | --wait on create |
| `backup restore` | restore | POST /v1/sites/{id}/backup/{backup_id}/restore | yes | --wait |
| `cache purge` | purge | POST /v1/sites/{id}/cache/purge | no | - |
| `cache purge-all` | purge everything | POST /v1/sites/{id}/cache/purge_everything | no | - |
| `domains list/add` | domains | GET/POST /v1/sites/{id}/domains | add no | - |
| `ssl list` | certs | GET /v1/sites/{id}/ssl/certificates | no | - |
| `ssh keys` | list/authorize | GET/POST /v1/sites/{id}/ssh/keys | - | - |
| `plugins list/install` | plugins | GET/POST /v1/sites/{id}/plugins | - | - |
| `themes list` | themes | GET /v1/sites/{id}/themes | - | - |
| `reporting bandwidth/waf` | reporting | GET /v1/reporting/sites/{id}/... | no | - |
| `account me/usage` | account | GET /v1/account/me, /v1/account/usage | no | - |

- [ ] Implement each row as one task: failing test, run-fail, implement, run-pass, commit (PAUSE). Use the Task 3.1 code as the template. Confirm operationIds against `bin/rocket_endpoints.json`.

---

## Phase 4 - Skills

Skills are markdown with YAML frontmatter (`name`, `description`). `description` must be third person and state what the skill does AND when to trigger it. Keep each SKILL.md focused; push endpoint detail into a sibling `reference.md`. No README.md inside a skill folder.

### Task 4.1 - Router skill `rocket-net` (the canonical pattern)

**Files:**
- Create: `skills/rocket-net/SKILL.md`

- [ ] **Step 1: Write `skills/rocket-net/SKILL.md`**

```markdown
---
name: rocket-net
description: Overview and router for managing Rocket.net WordPress hosting. Use when the user wants to manage Rocket.net sites, staging, deploys, backups, WP-CLI, domains, SSL, plugins, themes, caching, or hosting reporting. Explains when to use the bundled Rocket.net MCP versus the rocket CLI, and how credentials are set up.
---

# Rocket.net hosting

This plugin manages the Rocket.net HOSTING platform. It is not a WordPress content manager (use wp-index or wp-manager for content).

## Two tools, when to use each
- Bundled MCP (rocket-net server): conversational one-off actions. "Spin up a site", "what is using disk on site X".
- CLI `bin/rocket.py`: deterministic, scripted, bulk, or anything you must wait on. Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py <command>`.

## Credentials
CLI reads ~/.config/rocket-net/config.json (username+password recommended, or api_token; tokens are 7-day JWTs). The MCP uses the plugin's userConfig (keychain). Never put credentials in the repo.

## Safety
Destructive actions (delete site, publish staging to production, restore, transfer) require --yes and a scope review. Always read current state before changing it. Never run live actions against production when a staging or test site is available.

## Common entry points
- /rocket-sites, /rocket-deploy, /rocket-stage, /rocket-backup, /rocket-wp
- Skills: rocket-site-lifecycle, rocket-staging-deploy, rocket-wp-cli, rocket-backups, rocket-fleet-ops, and surface skills for domains-ssl, plugins-themes, cache-cdn, reporting-waf, users-access, billing-account.
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate ./rocket-net-plugin --strict`
Expected: passes; the skill is discovered.

- [ ] **Step 3: Commit (PAUSE for Julian)**

```bash
git add skills/rocket-net/SKILL.md
git commit -m "feat(skills): router skill"
```

### Task 4.2 - 4.12 - Remaining skills

One task each. Each creates `skills/<name>/SKILL.md` with frontmatter and body following Task 4.1, plus a `reference.md` listing the relevant operationIds and example `rocket` CLI invocations. The exact `description` for each (write verbatim into frontmatter):

| Skill | description (frontmatter) |
|---|---|
| rocket-site-lifecycle | Create, clone, delete, lock, and transfer Rocket.net sites. Use when the user wants to provision a new site, duplicate one, remove one, lock a site, or transfer ownership. Covers async task polling for create and clone. |
| rocket-staging-deploy | Manage Rocket.net staging environments and publish staging to production. Use when the user wants to create or refresh a staging site, preview changes, or deploy staging to live. Always runs a scope review before publishing. |
| rocket-wp-cli | Run WP-CLI commands on a Rocket.net site through the API. Use when the user wants to run wp commands (plugin updates, option get/set, search-replace, user management) on a hosted site. Distinguishes read from write and dry-runs destructive wp commands. |
| rocket-backups | Manage manual, automated, and cloud backups and restores on Rocket.net. Use when the user wants to take a backup, list backups, download one, or restore files or database. Confirms restore direction and target before acting. |
| rocket-fleet-ops | Run bulk operations across many Rocket.net sites. Use when the user wants to apply an action (plugin update, cache purge, report pull, wp command) across multiple or all sites. Parallelizes CLI calls and presents a scope review before any batch change. |
| rocket-domains-ssl | Manage domains, edge settings, and SSL certificates on Rocket.net sites. Use when the user wants to add or inspect a domain, change edge settings, or review SSL certificates. |
| rocket-plugins-themes | Install, search, and update WordPress plugins and themes via the Rocket.net API. Use when the user wants to manage plugins or themes on a hosted site at the hosting-platform level. |
| rocket-cache-cdn | Purge cache and manage CDN cache settings on Rocket.net. Use when the user wants to clear a site cache, purge everything, or manage CDN cache behavior. |
| rocket-reporting-waf | Pull bandwidth, CDN, visitor, and WAF event reporting from Rocket.net. Use when the user wants hosting analytics, traffic or bandwidth figures, or web application firewall event data for a site. |
| rocket-users-access | Manage site users, roles, SSH keys, FTP accounts, and password protection on Rocket.net. Use when the user wants to grant or revoke site access, manage SSH or FTP credentials, or set password protection. |
| rocket-billing-account | Read Rocket.net account information, usage, hosting plan, and billing. Use when the user wants to check account status, usage, plan, or invoices. Read-first; payment actions stay manual. |

- [ ] For each: create the folder and SKILL.md, write the verbatim description, write a short body and `reference.md` with the relevant operationIds, validate with `claude plugin validate --strict`, commit (PAUSE).

---

## Phase 5 - Commands

Commands are flat markdown files in `commands/`. Each describes the action and tells Claude how to run it (which CLI command or MCP action, with the scope review for destructive ones).

### Task 5.1 - `/rocket-deploy` (canonical, destructive pattern)

**Files:**
- Create: `commands/rocket-deploy.md`

- [ ] **Step 1: Write `commands/rocket-deploy.md`**

```markdown
---
description: Publish a Rocket.net staging site to production with a scope review.
---

# /rocket-deploy

Publish staging to production for a Rocket.net site. This is destructive (overwrites production).

Steps:
1. Identify the target site (ask if not given). Run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py sites list` if you need to find it.
2. Fetch current production and staging state and confirm staging exists.
3. Present a scope review: site, what will be overwritten, last backup time. Recommend taking a backup first.
4. On explicit approval, run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/rocket.py staging publish <site_id> --yes --wait`.
5. Purge cache and verify the site responds. Report the outcome loudly (success or partial failure).
```

- [ ] **Step 2: Validate**

Run: `claude plugin validate ./rocket-net-plugin --strict`
Expected: passes; command discovered as `/rocket-net:rocket-deploy`.

- [ ] **Step 3: Commit (PAUSE for Julian)**

```bash
git add commands/rocket-deploy.md
git commit -m "feat(commands): rocket-deploy"
```

### Task 5.2 - 5.5 - Remaining commands

One task each, following Task 5.1. Verbatim descriptions:

| Command file | description |
|---|---|
| commands/rocket-sites.md | List and inspect Rocket.net sites in the account. |
| commands/rocket-stage.md | Create or refresh a Rocket.net staging environment for a site. |
| commands/rocket-backup.md | Create or restore a backup for a Rocket.net site (restore is destructive and confirms first). |
| commands/rocket-wp.md | Run a WP-CLI command on a Rocket.net site (dry-run destructive wp commands first). |

- [ ] For each: create the file with frontmatter and steps, validate, commit (PAUSE).

---

## Phase 6 - Live validation and finalize

### Task 6.1 - Smoke test script

**Files:**
- Create: `scripts/test-smoke.sh`

- [ ] **Step 1: Write `scripts/test-smoke.sh`**

```bash
#!/usr/bin/env bash
# Live smoke test. Runs ONLY against an explicit staging/test site. Never production.
set -euo pipefail
: "${ROCKET_SMOKE_SITE:?Set ROCKET_SMOKE_SITE to a throwaway/staging site id}"
CLI="python3 $(dirname "$0")/../bin/rocket.py"
echo "1. auth + list sites"; $CLI sites list --json >/dev/null && echo OK
echo "2. get the smoke site"; $CLI sites get "$ROCKET_SMOKE_SITE" --json >/dev/null && echo OK
echo "3. benign wp-cli (option get blogname)"; $CLI wpcli "$ROCKET_SMOKE_SITE" -- option get blogname || echo "wpcli needs verification"
echo "4. cache purge"; $CLI cache purge "$ROCKET_SMOKE_SITE" --yes || echo "cache purge needs verification"
echo "Smoke test complete. Review any 'needs verification' lines against the real API."
```

- [ ] **Step 2: Run against Julian's staging site**

Julian provides `ROCKET_SMOKE_SITE` and confirms credentials are in `~/.config/rocket-net/config.json`.
Run: `chmod +x scripts/test-smoke.sh && ROCKET_SMOKE_SITE=<id> ./scripts/test-smoke.sh`
Expected: steps 1 and 2 OK. Steps 3 and 4 confirm real request/response shapes. Fix `_find_task`, wpcli arg passing, and any subcommand operationIds against the real responses, then re-run the unit suite.

- [ ] **Step 3: Commit (PAUSE for Julian)**

```bash
git add scripts/test-smoke.sh
git commit -m "test: live smoke test against a staging site"
```

### Task 6.2 - Finalize README and local-load test

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README** to reflect the real command surface, credential setup, MCP bundling, and a quickstart. README must reflect current state.

- [ ] **Step 2: Local-load the plugin**

Run: `claude --plugin-dir ./rocket-net-plugin` then in session `/reload-plugins`, confirm the `rocket-net` skills and `/rocket-*` commands appear and the MCP server connects (after userConfig prompts for username/password).
Expected: skills/commands listed, MCP `rocket-net` connected.

- [ ] **Step 3: Final validation**

Run: `claude plugin validate ./rocket-net-plugin --strict`
Expected: passes.

- [ ] **Step 4: Commit (PAUSE for Julian)**

```bash
git add README.md
git commit -m "docs: finalize README for v0.1.0"
```

---

## Self-review notes (author check against spec)

- Spec Section 3 (3 layers): Phase 0.2 (MCP), Phases 1-3 (CLI), Phases 4-5 (skills/commands). Covered.
- Spec Section 4.5 (build step, endpoints.json): Phase 0.3. Covered.
- Spec Section 6 (auth/secrets): Tasks 1.1, 1.3, manifest userConfig in 0.2. Covered.
- Spec Section 7 (async tasks): Task 2.3 + --wait in 2.4. Covered.
- Spec Section 8 (errors): Tasks 1.2, 2.2. Covered.
- Spec Section 9 (safety): Task 2.4 guard + skill/command scope reviews. Covered.
- Spec Section 10 (testing): unit tests throughout + Task 6.1 smoke. Covered.
- Spec full surface: Phase 3 generic call (2.4) reaches all 198 ops; subcommands cover common paths. Covered.
- Spec Section 14 unknowns: userConfig schema and .mcp.json http key RESOLVED from docs (see Verified facts). operationId stability RESOLVED (all unique). Plan-tier gating remains to confirm at smoke test (Task 6.1).

## Deferred / confirm during execution

- Exact operationIds for each subcommand: grep `bin/rocket_endpoints.json` at implementation time (Phase 3).
- Real `/tasks` response shape and `wpcli` request/response: confirm in Task 6.1, then adjust `_find_task` and the wpcli wrapper.
- Whether any endpoint is gated by Rocket.net plan tier: observe during smoke test.
