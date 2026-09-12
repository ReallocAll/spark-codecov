"""Audit coverage by owning CMake target and source, never by source alone."""

import json
from pathlib import Path
import re
import shlex


def absolute(value, directory):
    path = Path(value)
    return (path if path.is_absolute() else directory / path).resolve()


def audit(source, build):
    source, build = Path(source).resolve(), Path(build).resolve()
    policy = json.loads((Path(__file__).resolve().parents[1] / "cmake/coverage-exemptions.json").read_text())
    manifest = json.loads((build / "coverage-exemptions.json").read_text())
    if manifest.get("policy_version") != policy["policy_version"]:
        raise ValueError("Unknown coverage exemption policy version")
    owners = []
    names = set()
    expected_pairs = set()
    for entry in manifest["exemptions"]:
        name = entry["target"]
        spec = policy["targets"].get(name)
        if not spec or name in names or entry["type"] != "SHARED_LIBRARY":
            raise ValueError("Invalid coverage exemption target")
        expected_sources = {absolute(path, source) for path in spec["sources"]}
        actual_sources = [absolute(path, source) for path in entry["sources"]]
        binary_dir = absolute(entry["binary_dir"], build)
        if (absolute(entry["source_dir"], source) != absolute(spec["source_dir"], source)
                or set(actual_sources) != expected_sources or len(actual_sources) != len(expected_sources)
                or not binary_dir.is_relative_to(build)):
            raise ValueError("Invalid coverage exemption paths")
        owners.append((name, binary_dir / "CMakeFiles" / (name + ".dir"), True, expected_sources))
        expected_pairs.update((name, path) for path in expected_sources)
        names.add(name)
    for line in (build / "coverage-targets.txt").read_text().splitlines():
        name, kind, origin, binary = line.split("\t")
        binary_dir = absolute(binary, build)
        if name in names or not binary_dir.is_relative_to(build):
            raise ValueError("Duplicate or invalid coverage target inventory")
        owners.append((name, binary_dir / "CMakeFiles" / (name + ".dir"), False, None))
        names.add(name)

    seen_pairs = set()
    counts = {"total": 0, "instrumented": 0, "exempt": 0}
    exempt_commands = 0
    for entry in json.loads((build / "compile_commands.json").read_text()):
        directory = Path(entry["directory"]).resolve()
        path = absolute(entry["file"], directory)
        args = entry.get("arguments")
        if args is None:
            args = shlex.split(entry["command"])
        covered = "--coverage" in args or "-fprofile-arcs" in args or "-ftest-coverage" in args
        own = path.is_relative_to(source / "src") or path.is_relative_to(source / "tests")
        if not own:
            if covered:
                raise ValueError(f"Third-party source instrumented: {path}")
            continue
        outputs = []
        if entry.get("output"):
            outputs.append(absolute(entry["output"], directory))
        for index, arg in enumerate(args):
            if arg == "-o":
                if index + 1 == len(args):
                    raise ValueError("Compile output argument missing")
                outputs.append(absolute(args[index + 1], directory))
            elif arg.startswith("-o") and len(arg) > 2:
                outputs.append(absolute(arg[2:], directory))
        if not outputs or len(set(outputs)) != 1:
            raise ValueError(f"Ambiguous compile output: {path}")
        matches = [owner for owner in owners if outputs[0].is_relative_to(owner[1])]
        if len(matches) != 1:
            raise ValueError(f"Ambiguous or missing compile target: {path}")
        name, _, exempt, expected_sources = matches[0]
        if exempt:
            if path not in expected_sources or covered or "-fprofile-update=atomic" in args:
                raise ValueError(f"Unexpected exempt source or instrumentation: {name}: {path}")
            seen_pairs.add((name, path))
            exempt_commands += 1
        elif not covered:
            raise ValueError(f"Missing ordinary target coverage: {name}: {path}")
        else:
            optimization = [arg for arg in args if re.fullmatch(r"-O(?:[0-9]+|[sgz]|fast)?", arg)]
            if not optimization or optimization[-1] != "-O1":
                raise ValueError(f"Expected effective -O1 coverage optimization: {name}: {path}")
        if path.is_relative_to(source / "src"):
            counts["total"] += 1
            counts["exempt" if exempt else "instrumented"] += 1
    if seen_pairs != expected_pairs:
        raise ValueError("Exemption manifest has unmatched target/source entries")
    if not counts["instrumented"]:
        raise ValueError("No instrumented Spark implementation compile commands")
    return {"implementation-commands": counts["total"],
            "coverage-optimization": "-O1",
            "implementation-command-counts": counts,
            "exempt-compile-commands": exempt_commands,
            "coverage-exemptions": manifest,
            "tests-skipped-by-coverage-policy": 0}
