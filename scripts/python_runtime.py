"""Resolve the shared runtime of the selected Python for native source tests."""

import ctypes
from pathlib import Path
import sys
import sysconfig


def shared_runtime():
    libdir = sysconfig.get_config_var("LIBDIR")
    library = sysconfig.get_config_var("LDLIBRARY")
    if sys.version_info < (3, 12) or not libdir or not library or ".so" not in library:
        raise RuntimeError("Selected Python must provide a Python >= 3.12 shared runtime")
    path = (Path(libdir) / library).resolve(strict=True)
    if not path.is_file():
        raise RuntimeError("Selected Python shared runtime is not a file")
    runtime = ctypes.CDLL(str(path))
    runtime.Py_GetVersion.restype = ctypes.c_char_p
    actual = runtime.Py_GetVersion().decode().split()[0]
    if actual != sys.version.split()[0]:
        raise RuntimeError("Selected Python shared runtime version mismatch")
    return path
