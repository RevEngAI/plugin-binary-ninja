#!/usr/bin/env bash
# Generates a local, gitignored `revengai` SDK build (.dev-sdk/) from an OpenAPI spec, using
# sdk-python's own generator config fetched fresh from GitHub at `main`. This is a stopgap for
# endpoints that exist server-side but haven't reached a published `revengai` release yet
# (https://docs.reveng.ai/openapi.json only reflects what's currently live).
#
# Usage:
#   scripts/gen_dev_sdk.sh <path-to-openapi.json>
#   scripts/gen_dev_sdk.sh --url <https://.../openapi.json>
#
# Requires `openapi-generator-cli` (via `npx @openapitools/openapi-generator-cli`, which in
# turn requires a Java runtime) and `git`.
set -euo pipefail

SDK_PYTHON_REPO="https://github.com/RevEngAI/sdk-python.git"
# version-manager wants the bare Maven version, not the GitHub release tag's "v" prefix.
GENERATOR_VERSION="7.17.0"
OUTPUT_DIR=".dev-sdk"

usage() {
    echo "Usage: $0 <path-to-openapi.json> | --url <openapi-url>" >&2
    exit 1
}

if [[ $# -ne 1 && $# -ne 2 ]]; then
    usage
fi

if [[ "$1" == "--url" ]]; then
    [[ $# -eq 2 ]] || usage
    SPEC="$2"
else
    [[ $# -eq 1 ]] || usage
    SPEC="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "Fetching sdk-python's generator config from $SDK_PYTHON_REPO@main..."
git clone --quiet --depth 1 --branch main "$SDK_PYTHON_REPO" "$WORK_DIR/sdk-python"

# So the generated package's own version compares >= pyproject.toml's `revengai` pin (schema-pin
# tests check this) - mirrors sdk-python's own check.yaml, which stamps packageVersion from the
# spec's info.version the same way.
SPEC_VERSION="$(python3 -c "
import json, urllib.request
spec = '$SPEC'
if spec.startswith('http://') or spec.startswith('https://'):
    data = json.load(urllib.request.urlopen(spec))
else:
    data = json.load(open(spec))
print(data['info']['version'])
")"

rm -rf "$OUTPUT_DIR"

npx --yes @openapitools/openapi-generator-cli version-manager set "$GENERATOR_VERSION"

npx --yes @openapitools/openapi-generator-cli generate \
    --generator-name python \
    --input-spec "$SPEC" \
    --config "$WORK_DIR/sdk-python/config.yml" \
    --template-dir "$WORK_DIR/sdk-python/templates" \
    --additional-properties="packageVersion=$SPEC_VERSION" \
    --output "$OUTPUT_DIR"

echo
echo "Dev SDK generated at $OUTPUT_DIR."
echo "Install it over the pinned revengai version with:"
echo "  uv pip install -e $OUTPUT_DIR --python .venv"
