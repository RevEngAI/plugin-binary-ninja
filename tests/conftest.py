import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("REAI_DISABLE_PLUGIN_AUTOLOAD", "1")


def _add_vendor_paths() -> None:
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    roots = [ROOT, os.path.join(ROOT, "reai_toolkit")]
    suffixes = [
        "vendor",
        "vendor/site-packages",
        "vendor/Lib/site-packages",
        f"vendor/lib/{pyver}/site-packages",
        f"vendor/{pyver}/site-packages",
    ]
    for root in roots:
        for suf in suffixes:
            path = os.path.join(root, suf)
            if os.path.isdir(path) and path not in sys.path:
                sys.path.insert(0, path)


def _bootstrap_binary_ninja() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        import binaryninja  # noqa: F401

        return
    except ImportError:
        pass

    install_dir = os.environ.get("BN_INSTALL_DIR")
    if install_dir:
        api_path = os.path.join(install_dir, "python")
        if os.path.isdir(api_path) and api_path not in sys.path:
            sys.path.insert(0, api_path)


def _stub_binary_ninja_ui() -> None:
    try:
        import binaryninjaui  # noqa: F401

        return
    except Exception:
        pass

    module = types.ModuleType("binaryninjaui")

    class UIContextNotification:
        def __init__(self, *args, **kwargs):
            pass

    class UIContext:
        @staticmethod
        def registerNotification(*args, **kwargs):
            pass

        @staticmethod
        def unregisterNotification(*args, **kwargs):
            pass

        @staticmethod
        def activeContext(*args, **kwargs):
            return None

    module.UIContext = UIContext
    module.UIContextNotification = UIContextNotification
    sys.modules["binaryninjaui"] = module


_add_vendor_paths()
_bootstrap_binary_ninja()
_stub_binary_ninja_ui()
_add_vendor_paths()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
