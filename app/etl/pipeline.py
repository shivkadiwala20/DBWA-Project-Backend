"""
Run this to load all data:
  python -m app.etl.pipeline
"""
from pathlib import Path
from .loaders import load_accidents, load_rate_per_10k

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def run():
    files = [
        (
            "accident_per_location_2023.csv",
            "Unfallatlas 2023 — Full Germany",
            "https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/",
        ),
        (
            "accident_per_location_2021_in_Schleswig-Holstein.csv",
            "Unfallatlas 2021 — Schleswig-Holstein",
            "https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/",
        ),
    ]

    for fname, name, url in files:
        path = DATA_DIR / fname
        if path.exists():
            print(f"\nLoading: {name}")
            load_accidents(path, name, url)
        else:
            print(f"SKIP: {fname} not found")

    rate_file = DATA_DIR / "accident_per_10000_per_city.csv"
    if rate_file.exists():
        print("\nLoading: accident rate per 10k")
        load_rate_per_10k(rate_file)

    print("\n=== ETL complete ===")


if __name__ == "__main__":
    run()
