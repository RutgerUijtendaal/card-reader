from __future__ import annotations

import argparse

from seeds.runner import run_registered_seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run registered seeders")
    parser.add_argument("--force", action="store_true", help="Run all seeders even when tables are not empty")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_registered_seeds(force=args.force)
    for result in results:
        print(
            f"seed={result.name} skipped={result.skipped} created={result.created} updated={result.updated} message={result.message}"
        )


if __name__ == "__main__":
    main()

