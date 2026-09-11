"""Validate Cobertura coverage paths and counters against the source checkout."""

import argparse
import json
import math
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


COBERTURA_DOCTYPE = b"<!DOCTYPE coverage SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-04.dtd'>"


def integer(value, name):
    if value is None or not value.isascii() or not value.isdecimal():
        raise ValueError(f"Invalid {name}")
    return int(value)


def verify_checkout(source, data):
    expected = data.get("source_sha", "")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("Invalid source SHA in metadata")
    actual = subprocess.run(["git", "-C", str(source), "rev-parse", "--verify", "HEAD^{commit}"],
                            check=True, capture_output=True, text=True).stdout.strip()
    if actual != expected:
        raise ValueError("Source checkout HEAD does not match metadata source_sha")


def validate(source, report):
    source = source.resolve(strict=True)
    raw = report.read_bytes()
    raw = raw.replace(COBERTURA_DOCTYPE, b"", 1)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper() or b"\x00" in raw:
        raise ValueError("Unexpected XML DTD declarations and entities are forbidden")
    root = ET.fromstring(raw)
    if root.tag != "coverage":
        raise ValueError("Expected a Cobertura coverage root")
    valid = integer(root.get("lines-valid"), "lines-valid")
    covered = integer(root.get("lines-covered"), "lines-covered")
    if not 0 <= covered <= valid or valid == 0:
        raise ValueError("Empty or inconsistent coverage totals")
    tracked = set(subprocess.run(["git", "-C", str(source), "ls-files", "-z", "--", "src"],
                                 check=True, capture_output=True).stdout.decode("utf-8").split("\0"))
    classes = root.findall("./packages/package/classes/class")
    if not classes:
        raise ValueError("Coverage contains no classes")
    seen = set()
    total = total_covered = implementations = 0
    for cls in classes:
        filename = cls.get("filename", "")
        path = PurePosixPath(filename)
        if (not filename.startswith("src/") or "\\" in filename or ":" in filename
                or any(ord(c) < 32 for c in filename) or path.is_absolute()
                or any(p in (".", "..", "") for p in filename.split("/"))
                or filename in seen or filename not in tracked
                or any(p.lower() in ("tests", "test", "third-party", "third_party", "build") for p in path.parts)):
            raise ValueError("Invalid or duplicate source filename")
        target = (source / filename).resolve(strict=True)
        if not target.is_file() or not target.is_relative_to(source / "src"):
            raise ValueError("Source path escapes checkout src directory")
        seen.add(filename)
        lines = cls.findall("./lines/line")
        implementations += path.suffix == ".cpp" and bool(lines)
        numbers = set()
        source_lines = len(target.read_bytes().splitlines())
        for line in lines:
            number = integer(line.get("number"), "line number")
            hits = integer(line.get("hits"), "line hits")
            if number == 0 or number > source_lines or number in numbers:
                raise ValueError("Invalid or duplicate line number")
            numbers.add(number)
            total += 1
            total_covered += hits > 0
    if implementations == 0 or total != valid or total_covered != covered:
        raise ValueError("Coverage does not match source lines or totals")
    if root.get("line-rate") is not None:
        rate = float(root.get("line-rate"))
        if not math.isfinite(rate) or not 0 <= rate <= 1 or abs(rate - covered / valid) > 0.0001:
            raise ValueError("Inconsistent coverage line rate")
    return dict(files=len(seen), cpp_files=implementations, lines_valid=valid, lines_covered=covered,
                line_rate=covered / valid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    try:
        data = None
        if args.metadata:
            data = json.loads(args.metadata.read_text(encoding="utf-8"))
            verify_checkout(args.source, data)
        summary = validate(args.source, args.report)
        if args.metadata:
            data["coverage"] = summary
            args.metadata.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, sort_keys=True))
    except (ValueError, OSError, ET.ParseError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Report validation failed: {error}\n")


if __name__ == "__main__":
    main()
