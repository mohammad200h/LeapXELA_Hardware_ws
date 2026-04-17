#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent / "ros_ws" / "src" / "LEAP_Hand_API" / "ros2_module" / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse a leap_state text dump into a CSV inside ros2_module/scripts."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input text file containing repeated leap_state data blocks.",
    )
    parser.add_argument(
        "--output-name",
        default=None,
        help="Optional output CSV filename. Defaults to <input_stem>.csv inside ros2_module/scripts.",
    )
    return parser.parse_args()


def extract_rows(input_path: Path) -> list[list[float]]:
    rows = []
    current_block = []
    in_data_block = False

    with input_path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line == "data:":
                in_data_block = True
                current_block = []
                continue

            if not in_data_block:
                continue

            if line.startswith("- "):
                try:
                    value = float(line[2:])
                except ValueError:
                    continue

                current_block.append(value)
                if len(current_block) == 16:
                    rows.append(current_block)
                    in_data_block = False
            else:
                in_data_block = False

    return rows


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file).expanduser()
    if not input_path.exists():
        raise SystemExit(f"Input file does not exist: {input_path}")

    output_name = args.output_name or f"{input_path.stem}.csv"
    output_path = OUTPUT_DIR / output_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = extract_rows(input_path)

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([f"joint_{i+1}" for i in range(16)])
        writer.writerows(rows)

    print(f"Parsed {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
