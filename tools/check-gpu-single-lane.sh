#!/usr/bin/env bash
# Hosted-only runner route guard (historical filename retained for references).
#
# SENS-Futhark must never dispatch GitHub Actions onto the owner's computer.
# The former "single self-hosted GPU lane" rule was retired. This checker
# statically validates runner selection; it does NOT prove CUDA execution.
# A skipped or blocked CUDA job is UNVERIFIED, never a GPU PASS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
if [[ $# -ge 1 ]]; then
  ROOT="$1"
fi

python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
workflow_dir = root / ".github" / "workflows"
files = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
if not files:
    print("HOSTED_ROUTING_FAIL: no workflow files to audit", file=sys.stderr)
    sys.exit(2)

# Only standard GitHub-owned images that have been explicitly reviewed.
# Future organization-managed GitHub-hosted GPU labels need a separate,
# positively evidenced admission change. Never insert a custom local label.
allowed = {"ubuntu-24.04"}
violations = []
routes = 0

for path in files:
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\s*runs-on\s*:\s*(.*?)\s*$", line)
        if match is None:
            continue
        routes += 1
        candidate = match.group(1).split("#", 1)[0].strip().strip("'\"")
        if candidate not in allowed:
            violations.append(
                f"{path.relative_to(root)}:{line_no}: forbidden/unknown runs-on={candidate!r}"
            )

if routes == 0:
    violations.append("No runs-on declarations found; unable to prove routing")

if violations:
    for item in violations:
        print(f"HOSTED_ROUTING_FAIL: {item}", file=sys.stderr)
    sys.exit(2)

print(
    f"HOSTED_ROUTING_GREEN: {routes} explicit GitHub-owned Ubuntu runner routes "
    f"in {len(files)} workflow(s)"
)
print("CUDA/FPGA execution evidence: UNVERIFIED unless a real hardware job passes")
PY
