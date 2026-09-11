"""Resolve an allowlisted source ref to an immutable commit."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


REPOSITORIES = {"ReallocAll/spark": "CODECOV_TOKEN", "EndstoneMC/spark": "CODECOV_TOKEN_ENDSTONE"}
SHA = re.compile(r"[0-9a-f]{40}\Z")


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def boolean(value):
    if value not in ("true", "false"):
        raise ValueError("Boolean inputs must be exactly true or false")
    return value == "true"


def resolve_ref(repository, ref):
    if repository not in REPOSITORIES:
        raise ValueError("Source repository is not allowlisted")
    if not ref or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in ref):
        raise ValueError("Source ref must be nonempty and contain no whitespace or controls")
    if SHA.fullmatch(ref):
        data = json.loads(run(["gh", "api", f"repos/{repository}/commits/{ref}"]))
        if data.get("sha") != ref:
            raise ValueError("Commit API did not confirm the requested SHA")
        return "commit", ref, ref
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", ref):
        raise ValueError("Commit inputs must be complete lowercase 40-character SHAs")
    if ref.startswith("refs/"):
        if not ref.startswith(("refs/heads/", "refs/tags/")):
            raise ValueError("Only branch and tag refs are supported")
        candidates = [ref]
    else:
        candidates = [f"refs/heads/{ref}", f"refs/tags/{ref}"]
    if any(c in ref for c in "\\:*?[]~^;`$|&<>\"'(){}") or ref.startswith("-"):
        raise ValueError("Malformed source ref")
    for candidate in candidates:
        run(["git", "check-ref-format", candidate])
    patterns = candidates + [c + "^{}" for c in candidates if c.startswith("refs/tags/")]
    output = run(["git", "ls-remote", f"https://github.com/{repository}.git", *patterns])
    refs = {}
    for line in output.splitlines():
        sha, name = line.split("\t", 1)
        if name in patterns:
            if not SHA.fullmatch(sha) or name in refs:
                raise ValueError("Invalid remote ref response")
            refs[name] = sha
    matches = [c for c in candidates if c in refs]
    if len(matches) != 1:
        raise ValueError("Ref missing or ambiguous; use refs/heads/ or refs/tags/ explicitly")
    selected = matches[0]
    if selected.startswith("refs/heads/"):
        return "branch", refs[selected], selected[len("refs/heads/"):]
    return "tag", refs.get(selected + "^{}", refs[selected]), selected


def metadata(env):
    dispatch = env["GITHUB_EVENT_NAME"] == "workflow_dispatch"
    repository = env["SOURCE_REPOSITORY"] if dispatch else "ReallocAll/spark"
    ref = env["SOURCE_REF"] if dispatch else "develop"
    upload = boolean(env["UPLOAD_TO_CODECOV"]) if dispatch else True
    kind, sha, branch = resolve_ref(repository, ref)
    if not SHA.fullmatch(env["GITHUB_SHA"]):
        raise ValueError("Invalid infrastructure SHA")
    if env["GITHUB_SERVER_URL"] != "https://github.com":
        raise ValueError("Unsupported GitHub server URL")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", env["GITHUB_REPOSITORY"]):
        raise ValueError("Invalid workflow repository")
    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        if not re.fullmatch(r"[0-9]+", env[name]):
            raise ValueError("Invalid workflow run identifier")
    return dict(source_repository=repository, source_ref=ref, ref_type=kind, source_sha=sha,
                codecov_branch=branch, infra_sha=env["GITHUB_SHA"],
                run_url=f"{env['GITHUB_SERVER_URL']}/{env['GITHUB_REPOSITORY']}/actions/runs/"
                        f"{env['GITHUB_RUN_ID']}/attempts/{env['GITHUB_RUN_ATTEMPT']}",
                upload_to_codecov=upload, secret_name=REPOSITORIES[repository])


def check_token(data, env):
    repository = data["source_repository"]
    if repository not in REPOSITORIES or type(data["upload_to_codecov"]) is not bool:
        raise ValueError("Invalid token preflight metadata")
    if not data["upload_to_codecov"]:
        return
    name = "PERSONAL_TOKEN_PRESENT" if repository == "ReallocAll/spark" else "ENDSTONE_TOKEN_PRESENT"
    if not boolean(env.get(name, "false")):
        raise ValueError(f"Missing required secret: {REPOSITORIES[repository]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/metadata.json"))
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--check-token-only", action="store_true", help="Check presence flags against existing --output metadata")
    args = parser.parse_args()
    try:
        if args.check_token_only:
            check_token(json.loads(args.output.read_text(encoding="utf-8")), os.environ)
            return
        data = metadata(os.environ)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if args.github_output:
            lines = []
            for key, value in data.items():
                value = str(value).lower() if isinstance(value, bool) else value
                if any(ord(c) < 32 or ord(c) == 127 for c in value):
                    raise ValueError("Unsafe GitHub output")
                lines.append(f"{key}={value}\n")
            with args.github_output.open("a", encoding="utf-8") as stream:
                stream.writelines(lines)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Resolution failed: {error if not isinstance(error, subprocess.CalledProcessError) else 'Git or GitHub lookup failed'}\n")


if __name__ == "__main__":
    main()
