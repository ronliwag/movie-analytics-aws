#!/usr/bin/env bash
#
# Downloads the capstone dataset into data/raw/, and downloads the Postgres
# JDBC driver the PySpark loader needs to write to the database.
# Safe to re-run: skips whichever parts are already present.
#
# Usage:
#   ./scripts/download_data.sh          # skip whatever's already there
#   ./scripts/download_data.sh --force  # re-download and overwrite everything

set -euo pipefail

DATASET_URL="https://cdn.stratpoint.io/data-training/project_data.zip"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="$REPO_ROOT/data/raw"
ZIP_PATH="$REPO_ROOT/data/project_data.zip"

JDBC_VERSION="42.7.12"
JDBC_URL="https://repo1.maven.org/maven2/org/postgresql/postgresql/${JDBC_VERSION}/postgresql-${JDBC_VERSION}.jar"
JAR_DIR="$REPO_ROOT/scripts/pyspark/jars"
JAR_PATH="$JAR_DIR/postgresql-${JDBC_VERSION}.jar"

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
  echo "data/raw/ already has all expected files, skipping dataset download (use --force to redo)."
else
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
fi

if [[ -f "$JAR_PATH" && "$FORCE" == false ]]; then
  echo "Postgres JDBC driver already at $JAR_PATH, skipping (use --force to redo)."
else
  mkdir -p "$JAR_DIR"
  echo "Downloading Postgres JDBC driver ($JDBC_VERSION) for the PySpark loader ..."
  curl -fL -o "$JAR_PATH" "$JDBC_URL"
  echo "Saved JDBC driver to $JAR_PATH"
fi
