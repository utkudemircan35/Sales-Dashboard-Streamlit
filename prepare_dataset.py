"""Bir kez calistirin: python prepare_dataset.py"""
from pathlib import Path
from data_analysis import save_prepared_data

if __name__ == "__main__":
    report = save_prepared_data(Path(__file__).parent)
    print(f"Raw rows: {report['raw_rows']:,}; retained rows: {report['clean_rows']:,}")
    for step in report["steps"]:
        print(step)
