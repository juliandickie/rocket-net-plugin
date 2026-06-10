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

DESTRUCTIVE_HINTS = ("delete", "cancel", "restore", "publish", "reset", "transfer", "deauthorize")

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
