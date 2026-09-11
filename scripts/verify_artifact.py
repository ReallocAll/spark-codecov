"""Bind untrusted report data to the trusted prepare job outputs."""
import json
import os
from pathlib import Path
import subprocess

expected = json.loads(os.environ["EXPECTED"])
actual = json.loads(Path("reports/metadata.json").read_text())
for key in ("source_repository", "source_ref", "ref_type", "source_sha", "codecov_branch", "infra_sha", "run_url"):
    if actual.get(key) != expected[key]:
        raise SystemExit(f"Artifact provenance mismatch: {key}")
if actual.get("status") != "success":
    raise SystemExit("Artifact build did not succeed")
for folder, key in (("infra", "infra_sha"), ("source", "source_sha")):
    sha = subprocess.check_output(["git", "-C", folder, "rev-parse", "HEAD"], text=True).strip()
    if sha != expected[key]:
        raise SystemExit(f"Checkout mismatch: {folder}")
