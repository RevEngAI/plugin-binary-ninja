import site
import os
import sys
from binaryninja import log_info, log_error
import importlib

def delete_module(module_name):
    to_delete = []
    for module in sys.modules:
        if module.startswith(module_name):
            to_delete.append(module)
    for module_to_delete in to_delete:
        log_info(f"RevEng.AI | Deleting module: {module_to_delete}")
        del sys.modules[module_to_delete]

def import_module(module_name):
    try:
        importlib.import_module(module_name)
        log_info(f"RevEng.AI | Imported module: {module_name}")
    except Exception as e:
        log_error(f"RevEng.AI | Error importing module: {e}")

try:
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    log_info(f"RevEng.AI | Using __file__ for plugin directory")
except NameError:
    import reai_toolkit
    plugin_dir = os.path.dirname(os.path.abspath(reai_toolkit.__file__))
    log_info(f"RevEng.AI | Using module path for plugin directory")

vendor_path = os.path.join(plugin_dir, "vendor")

log_info(f"RevEng.AI | Plugin directory: {plugin_dir}")
log_info(f"RevEng.AI | Vendor path: {vendor_path}")
log_info(f"RevEng.AI | Vendor exists: {os.path.exists(vendor_path)}")

if os.path.exists(vendor_path):
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)
        log_info(f"RevEng.AI | Added vendor directory to sys.path at position 0")

    site.addsitedir(vendor_path)

    try:
        contents = os.listdir(vendor_path)
        log_info(f"RevEng.AI | Vendor directory contains {len(contents)} items")
        log_info(f"RevEng.AI | Sample contents: {', '.join(contents[:5])}")
        
        modules = ["urllib3", "certifi", "revengai"]

        for module in modules:
            delete_module(module)
            import_module(module)

        import certifi

        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

        modules.remove("revengai")
        sys.path.remove(vendor_path)

        for module in modules:
            delete_module(module)
            import_module(module)

        sys.path.insert(0, vendor_path)
        
    except Exception as e:
        log_error(f"RevEng.AI | Error listing vendor contents: {e}")
else:
    log_error(f"RevEng.AI | ERROR: Vendor directory not found at {vendor_path}")
    try:
        plugin_contents = os.listdir(plugin_dir)
        log_info(f"RevEng.AI | Plugin directory contains: {', '.join(plugin_contents)}")
    except Exception as e:
        log_error(f"RevEng.AI | Error listing plugin directory: {e}")

from reai_toolkit.revengai import RevengAIPlugin

plugin = RevengAIPlugin()
log_info("RevEng.AI | Plugin loaded successfully")
