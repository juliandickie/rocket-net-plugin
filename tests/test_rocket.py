import os, json, tempfile, unittest
from unittest import mock
import importlib.util
import urllib.error
import base64

def load_module():
    spec = importlib.util.spec_from_file_location("rocket", os.path.join(os.path.dirname(__file__), "..", "bin", "rocket.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as d:
            cfgpath = os.path.join(d, "config.json")
            with open(cfgpath, "w") as fh:
                json.dump({"username": "file@x.com", "password": "filepw", "base_url": "https://api.rocket.net"}, fh)
            with mock.patch.dict(os.environ, {"ROCKET_BASE_URL": "https://override.example"}):
                cfg = self.rocket.load_config(cfgpath)
        self.assertEqual(cfg["username"], "file@x.com")
        self.assertEqual(cfg["base_url"], "https://override.example")


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

    def test_sends_non_default_user_agent(self):
        # Cloudflare 403-bans the default Python-urllib UA; we must send our own.
        captured = {}
        def fake_urlopen(req, timeout=30):
            captured["ua"] = req.get_header("User-agent")
            m = mock.MagicMock(); m.read.return_value = b"{}"; m.__enter__.return_value = m
            return m
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.rocket.http_request("GET", "https://api.rocket.net/v1/sites", token="t")
        self.assertTrue(captured["ua"], "a User-Agent must be set")
        self.assertNotIn("urllib", captured["ua"].lower())


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


class TestPoll(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_polls_until_complete(self):
        cfg = {"base_url": "https://api.rocket.net"}
        states = [{"success": True, "result": [{"id": "9", "task_status": "IN_PROGRESS"}]},
                  {"success": True, "result": [{"id": "9", "task_status": "IN_PROGRESS"}]},
                  {"success": True, "result": [{"id": "9", "task_status": "DONE"}]}]
        with mock.patch.object(self.rocket, "call_api", side_effect=states), \
             mock.patch("time.sleep"):
            out = self.rocket.wait_for_task(cfg, site_id="1", task_id="9", interval=0.01, max_wait=5)
        self.assertEqual(out["task_status"], "DONE")

    def test_raises_on_failed(self):
        cfg = {"base_url": "https://api.rocket.net"}
        with mock.patch.object(self.rocket, "call_api", return_value={"success": True, "result": [{"id": "9", "task_status": "FAILED", "error": "boom"}]}), \
             mock.patch("time.sleep"):
            with self.assertRaises(self.rocket.RocketError):
                self.rocket.wait_for_task(cfg, site_id="1", task_id="9", interval=0.01, max_wait=5)


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


class TestSubcommands(unittest.TestCase):
    """Happy-path tests for a representative subset of Phase 3 subcommands."""

    def setUp(self):
        self.rocket = load_module()
        self.endpoints = self.rocket.load_endpoints()
        self.cfg = {"base_url": "https://api.rocket.net"}

    def _parse(self, argv):
        return self.rocket.build_parser().parse_args(argv)

    # --- sites list ---

    def test_sites_list_calls_get_v1_sites(self):
        with mock.patch.object(self.rocket, "call_api", return_value={"data": []}) as ca:
            args = self._parse(["sites", "list"])
            args.func(args, self.cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "GET")
        self.assertTrue(url.endswith("/v1/sites"), f"Expected /v1/sites, got {url}")

    # --- site delete - genuinely destructive, requires --yes ---

    def test_site_delete_requires_yes(self):
        """delete is destructive - SystemExit without --yes (no tty in test runner)."""
        args = self._parse(["site", "delete", "99"])
        with self.assertRaises(SystemExit):
            args.func(args, self.cfg, self.endpoints)

    def test_site_clone_not_guarded_posts_clone_path(self):
        """clone is additive, so it runs without --yes and posts to /v1/sites/{id}/clone."""
        with mock.patch.object(self.rocket, "call_api", return_value={"task_id": "t1"}) as ca:
            args = self._parse(["site", "clone", "42"])
            args.func(args, self.cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "POST")
        self.assertIn("/v1/sites/42/clone", url)

    # --- cache purge ---

    def test_cache_purge_clears_everything(self):
        """cache purge maps to purge_everything (no body) and runs without --yes."""
        with mock.patch.object(self.rocket, "call_api", return_value={}) as ca:
            args = self._parse(["cache", "purge", "7"])
            args.func(args, self.cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v1/sites/7/cache/purge_everything"), url)

    def test_cache_purge_files_sends_files_body(self):
        """cache purge-files posts to /cache/purge with a {files: [...]} body."""
        with mock.patch.object(self.rocket, "call_api", return_value={}) as ca:
            args = self._parse(["cache", "purge-files", "7", "https://x/a.css", "https://x/b.js"])
            args.func(args, self.cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v1/sites/7/cache/purge"), url)
        self.assertEqual(ca.call_args.kwargs.get("body"), {"files": ["https://x/a.css", "https://x/b.js"]})

    # --- account me ---

    def test_account_me_calls_get_account_me(self):
        with mock.patch.object(self.rocket, "call_api", return_value={"email": "a@b.com"}) as ca:
            args = self._parse(["account", "me"])
            out = args.func(args, self.cfg, self.endpoints)
        method, url = ca.call_args[0][1], ca.call_args[0][2]
        self.assertEqual(method, "GET")
        self.assertTrue(url.endswith("/v1/account/me"), f"Expected /v1/account/me, got {url}")
        self.assertEqual(out["email"], "a@b.com")


class TestFindTask(unittest.TestCase):
    def setUp(self):
        self.rocket = load_module()

    def test_list_returns_matching_task(self):
        data = [{"id": "1", "status": "x"}, {"id": "9", "status": "done"}]
        self.assertEqual(self.rocket._find_task(data, "9")["status"], "done")

    def test_list_no_match_returns_none(self):
        data = [{"id": "1"}, {"id": "2"}]
        self.assertIsNone(self.rocket._find_task(data, "9"))

    def test_result_envelope_list(self):
        data = {"success": True, "result": [{"id": "9", "status": "done"}]}
        self.assertEqual(self.rocket._find_task(data, "9")["status"], "done")

    def test_single_dict_non_match_returns_none(self):
        data = {"id": "5", "status": "running"}
        self.assertIsNone(self.rocket._find_task(data, "9"))


class TestOpConstants(unittest.TestCase):
    """Every OP_* constant must be a real operationId in the generated endpoint map."""

    def test_all_op_constants_exist_in_map(self):
        rocket = load_module()
        endpoints = rocket.load_endpoints()
        ops = endpoints["operations"]
        op_consts = {k: v for k, v in vars(rocket).items() if k.startswith("OP_")}
        self.assertTrue(op_consts, "expected OP_* constants to exist")
        missing = {k: v for k, v in op_consts.items() if v not in ops}
        self.assertEqual(missing, {}, f"OP_* constants not found in endpoint map: {missing}")


if __name__ == "__main__":
    unittest.main()
