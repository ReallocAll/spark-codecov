import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolve = load("resolve")
validator = load("validate_report")
SHA = "a" * 40
OTHER = "b" * 40


class ResolveTests(unittest.TestCase):
    def lookup(self, ref, remote):
        with patch.object(resolve, "run", side_effect=lambda args: remote if args[1] == "ls-remote" else ""):
            return resolve.resolve_ref("ReallocAll/spark", ref)

    def test_allowlist(self):
        for repository in ("attacker/spark", "reallocall/spark", "ReallocAll/spark.git", ""):
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                resolve.resolve_ref(repository, "develop")

    def test_malformed(self):
        for ref in ("", " develop", "x\ny", "x:y", "x;echo", "x$(echo)", "-x", "refs/pull/1", "abcdef0"):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                self.lookup(ref, "")
        for ref in ("../oops", "foo..bar", "foo.lock", "foo//bar", "foo@{bar"):
            with self.subTest(ref=ref), self.assertRaises((ValueError, subprocess.CalledProcessError)):
                resolve.resolve_ref("ReallocAll/spark", ref)

    def test_missing_and_ambiguous(self):
        with self.assertRaises(ValueError):
            self.lookup("develop", "")
        with self.assertRaises(ValueError):
            self.lookup("release", f"{SHA}\trefs/heads/release\n{OTHER}\trefs/tags/release\n")

    def test_branch_and_tags(self):
        self.assertEqual(self.lookup("refs/heads/release", f"{SHA}\trefs/heads/release\n"),
                         ("branch", SHA, "release"))
        self.assertEqual(self.lookup("develop", f"{SHA}\trefs/heads/develop\n"),
                         ("branch", SHA, "develop"))
        self.assertEqual(self.lookup("refs/tags/v1", f"{SHA}\trefs/tags/v1\n{OTHER}\trefs/tags/v1^{{}}\n"),
                         ("tag", OTHER, "refs/tags/v1"))
        self.assertEqual(self.lookup("v1", f"{SHA}\trefs/tags/v1\n"), ("tag", SHA, "refs/tags/v1"))

    def test_sha(self):
        with patch.object(resolve, "run", return_value=json.dumps({"sha": SHA})) as runner:
            self.assertEqual(resolve.resolve_ref("EndstoneMC/spark", SHA), ("commit", SHA, SHA))
            runner.assert_called_once_with(["gh", "api", f"repos/EndstoneMC/spark/commits/{SHA}"])
        with patch.object(resolve, "run", return_value=json.dumps({"sha": OTHER})), self.assertRaises(ValueError):
            resolve.resolve_ref("ReallocAll/spark", SHA)
        with patch.object(resolve, "run", side_effect=subprocess.CalledProcessError(1, "gh")):
            with self.assertRaises(subprocess.CalledProcessError):
                resolve.resolve_ref("ReallocAll/spark", SHA)

    def test_event_defaults_and_false(self):
        env = dict(GITHUB_EVENT_NAME="workflow_dispatch", SOURCE_REPOSITORY="EndstoneMC/spark",
                   SOURCE_REF="main", UPLOAD_TO_CODECOV="false", GITHUB_SHA=OTHER,
                   GITHUB_SERVER_URL="https://github.com", GITHUB_REPOSITORY="ReallocAll/spark-codecov",
                   GITHUB_RUN_ID="1", GITHUB_RUN_ATTEMPT="2")
        with patch.object(resolve, "resolve_ref", return_value=("branch", SHA, "main")) as lookup:
            data = resolve.metadata(env)
            self.assertFalse(data["upload_to_codecov"])
            self.assertEqual(data["secret_name"], "CODECOV_TOKEN_ENDSTONE")
            self.assertTrue(data["run_url"].endswith("/runs/1/attempts/2"))
            lookup.assert_called_with("EndstoneMC/spark", "main")
            env.update(GITHUB_EVENT_NAME="push", SOURCE_REPOSITORY="", SOURCE_REF="", UPLOAD_TO_CODECOV="")
            data = resolve.metadata(env)
            lookup.assert_called_with("ReallocAll/spark", "develop")
            self.assertTrue(data["upload_to_codecov"])
        for value in ("False", "0", "", "yes"):
            with self.assertRaises(ValueError):
                resolve.boolean(value)

    def test_token_preflight(self):
        for repo, flag, secret in (("ReallocAll/spark", "PERSONAL_TOKEN_PRESENT", "CODECOV_TOKEN"),
                                   ("EndstoneMC/spark", "ENDSTONE_TOKEN_PRESENT", "CODECOV_TOKEN_ENDSTONE")):
            data = dict(source_repository=repo, upload_to_codecov=True)
            with self.assertRaisesRegex(ValueError, secret):
                resolve.check_token(data, {})
            other = "ENDSTONE_TOKEN_PRESENT" if flag == "PERSONAL_TOKEN_PRESENT" else "PERSONAL_TOKEN_PRESENT"
            with self.assertRaises(ValueError):
                resolve.check_token(data, {other: "true"})
            resolve.check_token(data, {flag: "true"})
            data["upload_to_codecov"] = False
            resolve.check_token(data, {})


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name)
        (self.source / "src").mkdir()
        (self.source / "src/main.cpp").write_text("int main() {\n return 0;\n}\n", encoding="utf-8")
        (self.source / "src/api.h").write_text("#pragma once\n", encoding="utf-8")
        self.report = self.source / "coverage.xml"
        self.git = patch.object(validator.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, stdout=b"src/main.cpp\0src/api.h\0src/tests/main.cpp\0src/escape.cpp\0"))
        self.git.start()
        self.addCleanup(self.git.stop)

    def xml(self, filename="src/main.cpp", lines='<line number="1" hits="1"/><line number="2" hits="0"/>',
            valid="2", covered="1", extra=""):
        return (f'<coverage lines-valid="{valid}" lines-covered="{covered}"><packages><package><classes>'
                f'<class filename="{filename}"><lines>{lines}</lines></class>{extra}'
                '</classes></package></packages></coverage>')

    def check(self, xml):
        self.report.write_text(xml, encoding="utf-8")
        return validator.validate(self.source, self.report)

    def test_valid(self):
        summary = self.check(self.xml())
        self.assertEqual(summary["lines_covered"], 1)
        self.assertEqual(summary["line_rate"], 0.5)

    def test_gcovr_cobertura_declaration(self):
        declaration = "<?xml version='1.0' encoding='utf-8'?>\n" + validator.COBERTURA_DOCTYPE.decode() + "\n"
        xml = self.xml().replace('<coverage ', '<coverage version="gcovr 8.6" line-rate="0.5" ')
        self.assertEqual(self.check(declaration + xml)["lines_valid"], 2)

    def test_empty_header_class(self):
        extra = '<class filename="src/api.h"><lines/></class>'
        summary = self.check(self.xml(extra=extra))
        self.assertEqual(summary["files"], 2)
        self.assertEqual(summary["cpp_files"], 1)
        with self.assertRaises(ValueError):
            self.check(self.xml(lines="", valid="0", covered="0", extra=extra))
        measured_header = '<class filename="src/api.h"><lines><line number="1" hits="1"/></lines></class>'
        with self.assertRaises(ValueError):
            self.check(self.xml(lines="", valid="1", covered="1", extra=measured_header))

    def test_checkout_identity(self):
        with patch.object(validator.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=SHA + "\n")):
            validator.verify_checkout(self.source, {"source_sha": SHA})
            for data in ({"source_sha": OTHER}, {"source_sha": "main"}, {}):
                with self.subTest(data=data), self.assertRaises(ValueError):
                    validator.verify_checkout(self.source, data)

    def test_paths(self):
        for filename in ("../src/main.cpp", "/src/main.cpp", "C:/src/main.cpp", "src\\main.cpp",
                         "src/../src/main.cpp", "src//main.cpp", "src/./main.cpp", "src/missing.cpp",
                         "tests/main.cpp", "src/tests/main.cpp"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.check(self.xml(filename))

    def test_symlink_escape(self):
        outside = self.source / "outside.cpp"
        outside.write_text("line\nline\n", encoding="utf-8")
        try:
            (self.source / "src/escape.cpp").symlink_to(outside)
        except OSError:
            self.skipTest("Symlinks require host permission")
        with self.assertRaises(ValueError):
            self.check(self.xml("src/escape.cpp"))

    def test_bad_counts_and_empty(self):
        for xml in (self.xml(valid="0", covered="0"), self.xml(covered="3"), self.xml(valid="3"),
                    self.xml(lines=""), self.xml(lines='<line number="0" hits="1"/>'),
                    self.xml(lines='<line number="99" hits="1"/>'),
                    self.xml(lines='<line number="1" hits="-1"/>'),
                    self.xml(lines='<line number="1" hits="1"/><line number="1" hits="0"/>'),
                    '<coverage lines-valid="1" lines-covered="1"><packages/></coverage>',
                    self.xml("src/api.h", '<line number="1" hits="1"/>', "1", "1"),
                    self.xml().replace('<coverage ', '<coverage line-rate="nan" ')):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                self.check(xml)

    def test_duplicates_and_xml_poisoning(self):
        extra = '<class filename="src/main.cpp"><lines><line number="1" hits="1"/></lines></class>'
        with self.assertRaises(ValueError):
            self.check(self.xml(extra=extra))
        standard = validator.COBERTURA_DOCTYPE.decode()
        for prefix in ('<!DOCTYPE coverage>', '<!DOCTYPE coverage [<!ENTITY a SYSTEM "file:///etc/passwd">]>',
                       '<!DOCTYPE coverage SYSTEM "file:///etc/passwd">',
                       '<!DOCTYPE coverage SYSTEM "https://example.com/coverage.dtd">',
                       standard[:-1] + ' []>', standard + standard,
                       standard + '<!ENTITY a "poison">'):
            with self.assertRaises(ValueError):
                self.check(prefix + self.xml())


if __name__ == "__main__":
    unittest.main()
