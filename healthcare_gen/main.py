import os

from .config import apply_cli_overrides, build_arg_parser, CONFIG
from .pipeline import generate_dataset, print_summary, validate_schema


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    apply_cli_overrides(args)

    os.makedirs(os.path.dirname(CONFIG["output_path"]), exist_ok=True)

    df, tracker = generate_dataset()

    output_path = CONFIG["output_path"]
    if CONFIG["output_format"] == "parquet":
        if output_path.endswith(".csv"):
            output_path = output_path[:-4] + ".parquet"
        df.to_parquet(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)
    print(f"\nDataset saved to: {output_path}")

    report = tracker.generate_report()
    with open(CONFIG["report_path"], "w") as f:
        f.write(report)
    print(f"Quality report saved to: {CONFIG['report_path']}")

    if CONFIG["verbose"]:
        validate_schema(df)
        print_summary(df)

    print("\n" + "=" * 60)
    print("DATA QUALITY ISSUES INTRODUCED")
    print("=" * 60)
    for issue_type, count in sorted(tracker.counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {issue_type}: {count}")
