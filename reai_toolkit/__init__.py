import site
import os
import sys
from binaryninja import log_info, log_error

# Get the directory where this __init__.py file is located
try:
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    log_info(f"RevEng.AI | Using __file__ for plugin directory")
except NameError:
    # If __file__ is not defined, try to get it from the module
    import reai_toolkit
    plugin_dir = os.path.dirname(os.path.abspath(reai_toolkit.__file__))
    log_info(f"RevEng.AI | Using module path for plugin directory")

vendor_path = os.path.join(plugin_dir, "vendor")

log_info(f"RevEng.AI | Plugin directory: {plugin_dir}")
log_info(f"RevEng.AI | Vendor path: {vendor_path}")
log_info(f"RevEng.AI | Vendor exists: {os.path.exists(vendor_path)}")

# Check if vendor directory exists and list its contents
if os.path.exists(vendor_path):
    # Add vendor directory to the beginning of sys.path for priority
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)
        log_info(f"RevEng.AI | Added vendor directory to sys.path at position 0")

    # Also use site.addsitedir to handle .pth files
    site.addsitedir(vendor_path)

    # List some contents for verification
    try:
        contents = os.listdir(vendor_path)
        log_info(f"RevEng.AI | Vendor directory contains {len(contents)} items")
        log_info(f"RevEng.AI | Sample contents: {', '.join(contents[:5])}")
    except Exception as e:
        log_error(f"RevEng.AI | Error listing vendor contents: {e}")
else:
    log_error(f"RevEng.AI | ERROR: Vendor directory not found at {vendor_path}")
    # List what's actually in the plugin directory
    try:
        plugin_contents = os.listdir(plugin_dir)
        log_info(f"RevEng.AI | Plugin directory contains: {', '.join(plugin_contents)}")
    except Exception as e:
        log_error(f"RevEng.AI | Error listing plugin directory: {e}")

from reai_toolkit.revengai import RevengAIPlugin

plugin = RevengAIPlugin()
log_info("RevEng.AI | Plugin loaded successfully")
