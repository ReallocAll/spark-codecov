"""Build an isolated Linux checkout and retain diagnostics even on failure."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from audit_coverage import audit
from python_runtime import shared_runtime


def main():
    parser = argparse.ArgumentParser()
    for name in ("source", "reports", "source-repo", "source-sha", "source-ref", "ref-type", "branch", "infra-sha", "run-id", "run-url"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    source, reports = Path(args.source).resolve(), Path(args.reports).resolve()
    infra = Path(__file__).resolve().parents[1]
    reports.mkdir(parents=True, exist_ok=True)
    metadata = dict(source_repository=args.source_repo, source_ref=args.source_ref, source_sha=args.source_sha,
                    ref_type=args.ref_type, codecov_branch=args.branch, infra_sha=args.infra_sha,
                    run_url=args.run_url, toolchains={})
    metadata.update(status="failed", scope="Linux offline tests; compiled src implementations and headers")
    failed = False

    def run(label, command, check=True):
        with (reports / (label + ".log")).open("w", encoding="utf-8") as log:
            log.write(json.dumps(command) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, text=True)
        print(f"{label}: exit {result.returncode}", flush=True)
        if check and result.returncode:
            raise RuntimeError(f"{label} failed; see artifact log")
        return result.returncode

    try:
        for checkout, expected in ((source, args.source_sha), (infra, args.infra_sha)):
            actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
            if actual != expected:
                raise RuntimeError("Checkout SHA mismatch: " + str(checkout))
        if (source / "build").exists() or any(source.rglob("*.gcda")) or any(source.rglob("*.gcno")):
            raise RuntimeError("Fresh source checkout required")
        profile = source / ".conan2/profiles/default"
        profile_hash = hashlib.sha256(profile.read_bytes()).hexdigest()
        for tool in ("clang", "clang++", "llvm-cov", "cmake", "conan", "gcovr", "ninja", "python"):
            run("version-" + tool.replace("+", "p"), [tool, "--version"])
            metadata["toolchains"][tool] = (reports / ("version-" + tool.replace("+", "p") + ".log")).read_text().splitlines()[1:]
        metadata["conan-profile-sha256"] = profile_hash
        runtime = shared_runtime()
        os.environ["SPARK_TEST_LIBPYTHON"] = str(runtime)
        metadata["python-test-runtime"] = str(runtime)
        run("conan", ["conan", "install", ".", "--build=missing", "-s:h", "&:build_type=Debug", "--format=json", "--out-file=" + str(reports / "conan-graph.json")])
        graph = json.loads((reports / "conan-graph.json").read_text())["graph"]["nodes"]
        nodes = list(graph.values()) if isinstance(graph, dict) else graph
        if nodes[0]["settings"]["build_type"] != "Debug":
            raise RuntimeError("Consumer is not Debug")
        for node in nodes[1:]:
            build_type = node.get("settings", {}).get("build_type")
            if build_type and build_type != "RelWithDebInfo":
                raise RuntimeError("Dependency build_type changed: " + str(node.get("ref")))
        if hashlib.sha256(profile.read_bytes()).hexdigest() != profile_hash:
            raise RuntimeError("Conan profile changed")
        run("configure", ["cmake", "--preset", "conan-debug", "-DENDSTONE_SPARK_BUILD_SELFTEST=ON", "-DCMAKE_PROJECT_spark_INCLUDE=" + str(infra / "cmake/coverage.cmake"), "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DSPARK_TEST_LIBPYTHON:FILEPATH=" + str(runtime)])
        build = source / "build/Debug"
        shutil.copy2(build / "coverage-targets.txt", reports)
        shutil.copy2(build / "coverage-exemptions.json", reports)
        metadata.update(audit(source, build))
        run("build", ["cmake", "--build", "--preset", "conan-debug", "--parallel", "2"])
        discovery = subprocess.check_output(["ctest", "--test-dir", str(build), "--show-only=json-v1"], cwd=source, text=True)
        (reports / "tests.json").write_text(discovery, encoding="utf-8")
        metadata["test-count"] = len(json.loads(discovery)["tests"])
        if not metadata["test-count"]:
            raise RuntimeError("No offline tests discovered")
        failed = run("ctest", ["ctest", "--test-dir", str(build), "--output-on-failure", "--no-tests=error", "--parallel", "1", "--output-junit", str(reports / "ctest.xml")], check=False) != 0
        if not any(build.rglob("*.gcda")):
            raise RuntimeError("Tests produced no gcda files")
        run("gcovr", ["gcovr", "--root", str(source), "--filter", "src/", "--merge-lines", "--merge-mode-functions=separate", "--gcov-executable", "llvm-cov-20 gcov", "--xml", str(reports / "coverage.xml"), "--html-details", str(reports / "index.html"), "--html-self-contained", "--json-summary", str(reports / "summary.json"), "--print-summary", str(build)])
        metadata["status"] = "failed" if failed else "success"
    except Exception as exc:
        failed = True
        (reports / "failure.txt").write_text(str(exc) + "\n", encoding="utf-8")
        print(str(exc), file=sys.stderr)
    finally:
        if run("source-diff", ["git", "diff", "--exit-code", "HEAD"], check=False):
            failed = True
            metadata["status"] = "failed"
        (reports / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
