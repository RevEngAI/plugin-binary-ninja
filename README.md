# <img src="./images/logo.png" width=20> RevEng.AI Binary Ninja Plugin

A Binary Ninja plugin for integrating with the RevEng.AI platform for binary analysis and function renaming.

## Features

- Upload binaries for analysis to RevEng.AI platform
- Download and check analysis status
- Rename functions based on similar functions found in other binaries
- Batch analyze entire binaries for function renaming
- Configuration management for API settings

## Installation

1. Ensure you have Python 3.9 or later installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the `revengai_bn` directory to your Binary Ninja plugins directory:
   - Linux: `~/.binaryninja/plugins/`
   - Windows: `%APPDATA%\Binary Ninja\plugins\`
   - macOS: `~/Library/Application Support/Binary Ninja/plugins/`


## Requirements

- Binary Ninja 5.0 or later
- Python 3.9 or later
- Internet connection for API access
- RevEng.AI API key

## License

This plugin is released under the GPL-2.0 license. 