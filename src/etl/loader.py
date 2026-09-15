"""Day 01 loader entry point placeholder.

The Excel ingestion and normalization implementation is added in Day 02.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def main() -> None:
    """Verify that the raw-data directory is available."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Raw data directory ready: {RAW_DATA_DIR}")


if __name__ == "__main__":
    main()
