#!/usr/bin/env bash
# Live smoke test. Runs ONLY against an explicit staging/test site. Never production.
set -euo pipefail
: "${ROCKET_SMOKE_SITE:?Set ROCKET_SMOKE_SITE to a throwaway/staging site id}"
CLI="python3 $(dirname "$0")/../bin/rocket.py"
echo "1. auth + list sites"; $CLI sites list --json >/dev/null && echo OK
echo "2. get the smoke site"; $CLI sites get "$ROCKET_SMOKE_SITE" --json >/dev/null && echo OK
echo "3. benign wp-cli (option get blogname)"; $CLI wpcli "$ROCKET_SMOKE_SITE" -- option get blogname || echo "wpcli needs verification"
echo "4. cache purge"; $CLI cache purge "$ROCKET_SMOKE_SITE" || echo "cache purge needs verification"
echo "Smoke test complete. Review any 'needs verification' lines against the real API."
