import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("python_runtime", Path(__file__).parents[1] / "scripts/python_runtime.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class PythonRuntimeTests(unittest.TestCase):
    def test_selected_shared_library_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "libpython3.12.so"
            path.touch()
            values = {"LIBDIR": directory, "LDLIBRARY": path.name}
            library = Mock()
            library.Py_GetVersion.return_value = (sys.version.split()[0] + " test").encode()
            with patch.object(runtime.sysconfig, "get_config_var", side_effect=values.get), \
                    patch.object(runtime.ctypes, "CDLL", return_value=library) as load:
                self.assertEqual(runtime.shared_runtime(), path.resolve())
                load.assert_called_once_with(str(path.resolve()))
                library.Py_GetVersion.return_value = b"3.11.0 wrong"
                with self.assertRaisesRegex(RuntimeError, "mismatch"):
                    runtime.shared_runtime()

    def test_missing_or_static_library_fails(self):
        for values in ({}, {"LIBDIR": "/missing", "LDLIBRARY": "libpython.a"}):
            with self.subTest(values=values), patch.object(runtime.sysconfig, "get_config_var", side_effect=values.get):
                with self.assertRaises(RuntimeError):
                    runtime.shared_runtime()
        with tempfile.TemporaryDirectory() as directory:
            values = {"LIBDIR": directory, "LDLIBRARY": "libpython.so"}
            with patch.object(runtime.sysconfig, "get_config_var", side_effect=values.get):
                with self.assertRaises(FileNotFoundError):
                    runtime.shared_runtime()
