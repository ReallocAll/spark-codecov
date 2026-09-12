import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit_coverage", ROOT / "scripts/audit_coverage.py")
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)
POLICY = json.loads((ROOT / "cmake/coverage-exemptions.json").read_text())
PARSER = "spark_linux_admission_parser_fixture"


class CMakePolicyTests(unittest.TestCase):
    def configure(self, names, change=None):
        temporary = tempfile.TemporaryDirectory(prefix="spark coverage ")
        self.addCleanup(temporary.cleanup)
        source = Path(temporary.name)
        groups = {}
        for name in names:
            rule = POLICY["targets"].get(name, POLICY["targets"][PARSER])
            target = dict(name=name, kind="SHARED", origin=rule["source_dir"],
                          sources=rule["sources"].copy(), option="-nostartfiles",
                          definition=rule.get("definition", ""))
            if change:
                change(target)
            groups.setdefault(target["origin"], []).append(target)
        declarations = {}
        for origin, targets in groups.items():
            lines = []
            for target in targets:
                paths = []
                for path in target["sources"]:
                    file = source / path
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text("int fixture;\n")
                    paths.append('"' + file.as_posix() + '"')
                name = target["name"]
                lines += [f'add_library({name} {target["kind"]} {" ".join(paths)})',
                          f'set_target_properties({name} PROPERTIES LINKER_LANGUAGE CXX)',
                          f'target_link_options({name} PRIVATE {target["option"]})',
                          f'target_compile_definitions({name} PRIVATE {target["definition"]})']
            declarations[origin] = "\n".join(lines)
        root = f'''cmake_minimum_required(VERSION 3.29)
project(spark LANGUAGES NONE)
set(CMAKE_CXX_COMPILER_ID Clang)
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_CXX_COMPILE_OBJECT unused)
set(CMAKE_CXX_CREATE_SHARED_LIBRARY unused)
set(CMAKE_CXX_ARCHIVE_CREATE unused)
set(CMAKE_CXX_ARCHIVE_FINISH unused)
include("{(ROOT / 'cmake/coverage.cmake').as_posix()}")
'''
        root += declarations.pop(".", "") + "\n"
        for origin, contents in declarations.items():
            directory = source / origin
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "CMakeLists.txt").write_text(contents)
            root += f'add_subdirectory("{origin}")\n'
        (source / "src").mkdir(exist_ok=True)
        (source / "src/core.cpp").write_text("int core;\n")
        root += '''add_library(spark_linux_permanent_gateway STATIC src/core.cpp)
add_library(spark_linux_gateway_test_backend STATIC src/core.cpp)
set_target_properties(spark_linux_permanent_gateway spark_linux_gateway_test_backend PROPERTIES LINKER_LANGUAGE CXX)
function(snapshot)
'''
        for name in names + ["spark_linux_permanent_gateway", "spark_linux_gateway_test_backend"]:
            root += f'''get_target_property(comp {name} COMPILE_OPTIONS)
get_target_property(link {name} LINK_OPTIONS)
file(APPEND "${{PROJECT_BINARY_DIR}}/options.txt" "{name}|${{comp}}|${{link}}\\n")
'''
        root += 'endfunction()\ncmake_language(DEFER CALL snapshot)\n'
        (source / "CMakeLists.txt").write_text(root)
        result = subprocess.run(["cmake", "-S", str(source), "-B", str(source / "build"), "-G", "Ninja"],
                                capture_output=True, text=True)
        return source, result

    def test_historical_targets(self):
        names = [name for name in POLICY["targets"] if name != PARSER]
        source, result = self.configure(names)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((source / "build/coverage-exemptions.json").read_text())
        self.assertEqual(len(data["exemptions"]), 5)
        self.check_options(source, names)

    def test_current_parser_and_static_targets(self):
        source, result = self.configure([PARSER])
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((source / "build/coverage-exemptions.json").read_text())
        self.assertEqual(len(data["exemptions"]), 1)
        self.assertEqual(len(data["exemptions"][0]["sources"]), 2)
        self.check_options(source, [PARSER])

    def check_options(self, source, exempt):
        for line in (source / "build/options.txt").read_text().splitlines():
            name, compile_options, link_options = line.split("|")
            if name in exempt:
                self.assertEqual(compile_options, "comp-NOTFOUND")
                self.assertEqual(link_options, "-nostartfiles")
            else:
                self.assertEqual(compile_options, "--coverage;-fprofile-update=atomic;-O1;-g")

    def test_contract_changes_fail(self):
        changes = {
            "source": lambda t: t.update(sources=["src/changed.cpp"]),
            "extra_source": lambda t: t["sources"].append("src/extra.cpp"),
            "type": lambda t: t.update(kind="STATIC"),
            "origin": lambda t: t.update(origin="tests/changed"),
            "option": lambda t: t.update(option="-Wl,--as-needed"),
            "definition": lambda t: t.update(definition="SPARK_GATEWAY_PARSER_FIXTURE=0"),
        }
        for case, change in changes.items():
            with self.subTest(case=case):
                _, result = self.configure([PARSER], change)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Coverage exemption", result.stderr)

    def test_unknown_no_startup_fails(self):
        _, result = self.configure(["unreviewed_gateway"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unreviewed no-startup", result.stderr)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="spark audit ")
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name).resolve()
        self.build = self.source / "build"
        self.build.mkdir()
        self.binary = self.build / "tests/native/alloc/linux_gateway"
        self.paths = [str(self.source / path) for path in POLICY["targets"][PARSER]["sources"]]
        self.manifest = {"policy_version": 1, "exemptions": [
            {"target": PARSER, "type": "SHARED_LIBRARY", "source_dir": str(self.source / POLICY["targets"][PARSER]["source_dir"]),
             "binary_dir": str(self.binary), "sources": self.paths, "reason": "ELF contract"}]}
        self.inventory = f"ordinary\tSTATIC_LIBRARY\t{self.source}\t{self.build}\n"
        self.entries = [self.entry(path, PARSER, self.binary, False) for path in self.paths]
        self.entries += [self.entry(path, "ordinary", self.build, True) for path in self.paths]
        self.entries.append(self.entry(str(self.source / "src/core.cpp"), "ordinary", self.build, True))

    def entry(self, path, target, binary, covered):
        output = binary / "CMakeFiles" / (target + ".dir") / (Path(path).name + ".o")
        args = ["clang++", "-c", path, "-o", str(output)]
        if covered:
            args.extend(["--coverage", "-O1"])
        return {"file": path, "directory": str(self.build), "arguments": args, "output": str(output)}

    def run_audit(self):
        (self.build / "compile_commands.json").write_text(json.dumps(self.entries))
        (self.build / "coverage-exemptions.json").write_text(json.dumps(self.manifest))
        (self.build / "coverage-targets.txt").write_text(self.inventory)
        return auditor.audit(self.source, self.build)

    def test_shared_sources_are_target_specific(self):
        result = self.run_audit()
        self.assertEqual(result["implementation-command-counts"], {"total": 1, "instrumented": 1, "exempt": 0})
        self.assertEqual(result["exempt-compile-commands"], 2)
        self.assertEqual(result["tests-skipped-by-coverage-policy"], 0)
        self.assertEqual(result["coverage-optimization"], "-O1")

    def test_last_optimization_wins(self):
        self.entries[-1]["arguments"].insert(1, "-O2")
        self.assertEqual(self.run_audit()["coverage-optimization"], "-O1")

    def test_optimization_override_or_absence_fails(self):
        for option in ("-O0", "-O2", "-O3", "-Os", "-Oz", "-Og", "-Ofast", "-O", None):
            with self.subTest(option=option):
                saved = self.entries[2]["arguments"].copy()
                if option is None:
                    self.entries[2]["arguments"].remove("-O1")
                else:
                    self.entries[2]["arguments"].append(option)
                with self.assertRaisesRegex(ValueError, "effective -O1"):
                    self.run_audit()
                self.entries[2]["arguments"] = saved

    def test_historical_five_implementation_exemptions(self):
        self.manifest["exemptions"] = []
        self.entries = [self.entries[-1]]
        for name, rule in POLICY["targets"].items():
            if name == PARSER:
                continue
            origin = self.source / rule["source_dir"]
            binary = self.build / rule["source_dir"]
            path = str(self.source / rule["sources"][0])
            self.manifest["exemptions"].append(dict(target=name, type="SHARED_LIBRARY", source_dir=str(origin),
                                                    binary_dir=str(binary), sources=[path], reason="ELF contract"))
            self.entries.append(self.entry(path, name, binary, False))
        self.assertEqual(self.run_audit()["implementation-command-counts"], {"total": 6, "instrumented": 1, "exempt": 5})

    def test_tokenized_command_output(self):
        import shlex
        for entry in self.entries:
            entry["command"] = shlex.join(entry.pop("arguments"))
            del entry["output"]
        self.assertEqual(self.run_audit()["exempt-compile-commands"], 2)

    def test_invalid_commands_fail(self):
        changes = {
            "ordinary_missing": lambda: self.entries[-1]["arguments"].remove("--coverage"),
            "shared_source_missing": lambda: self.entries[2]["arguments"].remove("--coverage"),
            "exempt_covered": lambda: self.entries[0]["arguments"].append("--coverage"),
            "unmatched_manifest": lambda: self.entries.pop(0),
            "missing_manifest": lambda: self.manifest["exemptions"].clear(),
            "unexpected_source": lambda: self.entries[0].update(file=str(self.source / "src/other.cpp")),
            "ambiguous_output": lambda: self.entries[0].update(output=str(self.build / "wrong.o")),
            "unknown_owner": lambda: self.entries[0].update(arguments=["clang++", "-o", str(self.build / "wrong.o")], output=str(self.build / "wrong.o")),
            "duplicate_owner": lambda: self.manifest["exemptions"].append(copy.deepcopy(self.manifest["exemptions"][0])),
        }
        entries, manifest = copy.deepcopy(self.entries), copy.deepcopy(self.manifest)
        for name, change in changes.items():
            with self.subTest(case=name):
                self.entries, self.manifest = copy.deepcopy(entries), copy.deepcopy(manifest)
                change()
                with self.assertRaises(ValueError):
                    self.run_audit()


if __name__ == "__main__":
    unittest.main()
