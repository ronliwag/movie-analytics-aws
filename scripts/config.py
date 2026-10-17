"""Data locations shared by the pipeline scripts.

Everything lives under DATA_DIR, which defaults to <repo>/data. Set the
DATA_DIR env var (or put it in .env) to point the scripts somewhere else,
e.g. /tmp in a Lambda later on.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# `or`, not a get() default: an empty `DATA_DIR=` line in .env sets the var
# to "", and Path("") would silently mean "the current directory".
DATA_DIR = Path(os.environ.get("DATA_DIR") or REPO_ROOT / "data").expanduser().resolve()

RAW_DIR = DATA_DIR / "raw"
ENRICHED_DIR = DATA_DIR / "enriched"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
