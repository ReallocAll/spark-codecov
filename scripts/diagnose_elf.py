"""Compare ELF test setup across build modes; this is not coverage acceptance."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from python_runtime import shared_runtime


SOURCE_SHA = "1c0e54981fab6735bee714394012ba905f817b97"
TEST = "spark_linux_elf_domain_test"
MODES = (("covered-O0", True, "-O0"), ("uncovered-O0", False, "-O0"),
         ("covered-O1", True, "-O1"), ("covered-O2", True, "-O2"))


def debugger_script(source_file, oracle):
    source_file = source_file.as_posix()
    commands = ["set pagination off", "set confirm off", "set breakpoint pending off",
                f"break {source_file}:83", "run"]
    return "\n".join(commands) + "\npython\n" + f'''
import gdb, json, re
saved_errors = []
try:
    original_location = gdb.selected_frame().find_sal()
    if original_location.line != 83:
        saved_errors.append("Original capture breakpoint moved to " + str(original_location.line))
    gdb.set_convenience_variable("saved_original", gdb.parse_and_eval("spec.original"))
except gdb.error as error:
    saved_errors.append("Original capture: " + str(error))
end
delete breakpoints
break {source_file}:89
continue
python
result = {{"expected_source_line": 89, "errors": saved_errors}}
try:
    frame = gdb.selected_frame()
    location = frame.find_sal()
    result["actual_line"] = location.line
    result["actual_file"] = location.symtab.fullname() if location.symtab else None
    result["function"] = frame.name()
except gdb.error as error:
    result["errors"].append(str(error))
values = {{}}
for name, expression in {{"imported": "(void*) Imported", "original": "$saved_original", "replacement": "(void*) &replacement"}}.items():
    try:
        values[name] = int(gdb.parse_and_eval(expression))
        result[name] = hex(values[name])
    except (gdb.error, ValueError) as error:
        result["errors"].append(name + ": " + str(error))
if "imported" in values and "original" in values:
    result["imported_equals_original"] = values["imported"] == values["original"]
if "imported" in values and "replacement" in values:
    result["imported_equals_replacement"] = values["imported"] == values["replacement"]
for command in ["info line {source_file}:87", "info line {source_file}:89", "info address getpid", "disassemble /rs main"]:
    try:
        print(gdb.execute(command, to_string=True))
    except gdb.error as error:
        result["errors"].append(command + ": " + str(error))
try:
    assembly = gdb.execute("disassemble /r main", to_string=True)
    slots = set(re.findall(r"#\\s*(0x[0-9a-f]+)\\s*<getpid[^>]*>", assembly))
    result["getpid_memory_operands"] = sorted(slots)
    for address in sorted(slots):
        print(gdb.execute("x/gx " + address, to_string=True))
except gdb.error as error:
    result["errors"].append(str(error))
with open({str(oracle)!r}, "w") as stream:
    result["complete"] = (not result["errors"] and result.get("actual_line") == 89 and
                          result.get("actual_file") == {str(source_file)!r} and len(values) == 3)
    json.dump(result, stream, indent=2)
end
continue
quit
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()
    source, reports = args.source.resolve(), args.reports.resolve()
    infra = Path(__file__).resolve().parents[1]
    reports.mkdir(parents=True, exist_ok=True)
    result = {"diagnostic_only": True, "coverage_acceptance": False, "source_sha": SOURCE_SHA,
              "infra_sha": os.environ["GITHUB_SHA"], "run_url": os.environ["GITHUB_SERVER_URL"] + "/" +
              os.environ["GITHUB_REPOSITORY"] + "/actions/runs/" + os.environ["GITHUB_RUN_ID"], "modes": []}
    failed = False

    def run(command, log, cwd=source, required=True, timeout=1800):
        with log.open("w") as stream:
            stream.write(json.dumps(command) + "\n")
            stream.flush()
            completed = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        if required and completed.returncode:
            raise RuntimeError(f"Command failed ({completed.returncode}): {log.name}")
        return completed.returncode

    try:
        for directory, expected in ((source, SOURCE_SHA), (infra, result["infra_sha"])):
            actual = subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
            if actual != expected:
                raise RuntimeError("Diagnostic checkout SHA mismatch")
        if (source / "build").exists() or any(source.rglob("*.gcda")) or any(source.rglob("*.gcno")):
            raise RuntimeError("Fresh diagnostic checkout required")
        runtime = shared_runtime()
        os.environ["SPARK_TEST_LIBPYTHON"] = str(runtime)
        result["python_runtime"] = str(runtime)
        for tool in ("clang++", "llvm-cov", "cmake", "conan", "python", "gdb"):
            run([tool, "--version"], reports / ("version-" + tool.replace("+", "p") + ".log"))
        run(["conan", "install", ".", "--build=missing", "-s:h", "&:build_type=Debug", "--format=json",
             "--out-file=" + str(reports / "conan-graph.json")], reports / "conan.log")
        graph = json.loads((reports / "conan-graph.json").read_text())["graph"]["nodes"]
        nodes = list(graph.values()) if isinstance(graph, dict) else graph
        if nodes[0]["settings"]["build_type"] != "Debug" or any(
                node.get("settings", {}).get("build_type") not in (None, "RelWithDebInfo") for node in nodes[1:]):
            raise RuntimeError("Diagnostic Conan build types changed")
        toolchain = source / "build/Debug/generators/conan_toolchain.cmake"
        if not toolchain.is_file():
            raise RuntimeError("Expected Conan diagnostic toolchain is missing")
        for name, covered, optimization in MODES:
            entry = {"name": name, "coverage": covered, "optimization": optimization}
            result["modes"].append(entry)
            output = reports / name
            output.mkdir()
            build = source / "build" / name
            try:
                configure = ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
                             "-DCMAKE_BUILD_TYPE=Debug", "-DCMAKE_TOOLCHAIN_FILE=" + str(toolchain),
                             "-DENDSTONE_SPARK_BUILD_SELFTEST=ON", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                             "-DSPARK_TEST_LIBPYTHON:FILEPATH=" + str(runtime)]
                if covered:
                    configure += ["-DCMAKE_PROJECT_spark_INCLUDE=" + str(infra / "cmake/diagnose_elf.cmake"),
                                  "-DSPARK_DIAGNOSTIC_OPTIMIZATION=" + optimization]
                else:
                    configure.append("-DCMAKE_CXX_FLAGS_DEBUG=-g -O0")
                run(configure, output / "configure.log")
                run(["cmake", "--build", str(build), "--target", TEST, "--parallel", "2"], output / "build.log")
                shutil.copy2(build / "compile_commands.json", output)
                target_commands = [command for command in json.loads((build / "compile_commands.json").read_text())
                                   if TEST + ".dir/" in command.get("command", " ".join(command.get("arguments", [])))]
                if not target_commands:
                    raise RuntimeError("Missing diagnostic target compile commands")
                for command in target_commands:
                    arguments = command.get("arguments") or shlex.split(command["command"])
                    options = [argument for argument in arguments if re.fullmatch(r"-O(?:[0-3sgz]|fast)", argument)]
                    if not options or options[-1] != optimization or ("--coverage" in arguments) != covered:
                        raise RuntimeError("Diagnostic target effective flags do not match mode")
                (output / "target-compile-commands.json").write_text(json.dumps(target_commands, indent=2))
                discovery = subprocess.check_output(["ctest", "--test-dir", str(build), "--show-only=json-v1",
                                                     "-R", "^" + TEST + "$"], text=True)
                (output / "tests.json").write_text(discovery)
                tests = json.loads(discovery)["tests"]
                if len(tests) != 1 or tests[0]["name"] != TEST:
                    raise RuntimeError("Unexpected diagnostic test discovery")
                executable = tests[0]["command"][0]
                entry["test_exit_code"] = run(["ctest", "--test-dir", str(build), "--output-on-failure",
                                               "--no-tests=error", "-R", "^" + TEST + "$"],
                                              output / "test.log", required=False, timeout=120)
                script = output / "inspect.gdb"
                script.write_text(debugger_script(source / "tests/native/alloc/linux_gateway/elf_domain_test.cpp",
                                                  output / "oracle.json"))
                entry["gdb_exit_code"] = run(["gdb", "--batch", "--nx", "-x", str(script), "--args", executable],
                                             output / "gdb.log", cwd=build, required=False, timeout=120)
                run(["readelf", "-rW", executable], output / "relocations.log")
                if not (output / "oracle.json").exists():
                    raise RuntimeError("GDB did not produce pointer evidence")
                entry["oracle"] = json.loads((output / "oracle.json").read_text())
                entry["diagnostic_status"] = "captured" if entry["oracle"].get("complete") else "incomplete"
                failed |= entry["diagnostic_status"] == "incomplete"
            except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
                entry["diagnostic_status"] = "error"
                entry["error"] = str(error)
                failed = True
            (reports / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        result["error"] = str(error)
        failed = True
    finally:
        result["source_diff_exit_code"] = run(["git", "diff", "--exit-code", "HEAD"], reports / "source-diff.log", required=False)
        failed |= result["source_diff_exit_code"] != 0
        result["diagnostic_status"] = "error" if failed else "captured"
        (reports / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
