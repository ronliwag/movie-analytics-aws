#!/usr/bin/env bash
#
# Downloads the capstone dataset and unzips it into data/raw/.
# Safe to re-run: skips the download if the expected files are already there.
#
# Usage:
#   ./scripts/download_data.sh          # skip if data/raw/ already populated
#   ./scripts/download_data.sh --force  # re-download and overwrite

set -euo pipefail

DATASET_URL="https://cdn.stratpoint.io/data-training/project_data.zip"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw"
ZIP_PATH="$REPO_ROOT/data/project_data.zip"
FORCE=false

if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
fi

EXPECTED_FILES=(movies_main.csv ratings.json movie_extended.csv)

already_present=true
for f in "${EXPECTED_FILES[@]}"; do
  [[ -f "$RAW_DIR/$f" ]] || already_present=false
done

if [[ "$already_present" == true && "$FORCE" == false ]]; then
  echo "data/raw/ already has all expected files, skipping download (use --force to redo)."
  exit 0
fi

mkdir -p "$RAW_DIR"

echo "Downloading dataset from $DATASET_URL ..."
curl -fL -o "$ZIP_PATH" "$DATASET_URL"

echo "Unzipping into $RAW_DIR ..."
if command -v unzip >/dev/null 2>&1; then
  unzip -o "$ZIP_PATH" -d "$RAW_DIR"
else
  python3 -m zipfile -e "$ZIP_PATH" "$RAW_DIR"
fi

rm -f "$ZIP_PATH"

# The archive nests everything under a project_data/ folder; flatten it so
# the CSVs/JSON land directly in data/raw/ as the rest of the repo expects.
if [[ -d "$RAW_DIR/project_data" ]]; then
  mv "$RAW_DIR/project_data"/* "$RAW_DIR/"
  rmdir "$RAW_DIR/project_data"
fi

echo "Done. Contents of data/raw/:"
ls -la "$RAW_DIR"
