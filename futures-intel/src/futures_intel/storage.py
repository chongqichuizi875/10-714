from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from futures_intel.models import DailySnapshot
from futures_intel.summarize import PositionSummary


class LocalStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.processed_dir = data_dir / "processed"
        self.report_dir = data_dir / "reports"
        for path in (self.raw_dir, self.processed_dir, self.report_dir):
            path.mkdir(parents=True, exist_ok=True)

    def snapshot_stem(self, snapshot: DailySnapshot) -> str:
        return f"{snapshot.commodity_symbol.lower()}_{snapshot.contract.lower()}_{snapshot.trade_date.isoformat()}"

    def write_snapshot(self, snapshot: DailySnapshot) -> dict[str, Path]:
        stem = self.snapshot_stem(snapshot)
        json_path = self.processed_dir / f"{stem}.json"
        csv_path = self.processed_dir / f"{stem}.csv"
        json_path.write_text(
            json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        fieldnames = [
            "trade_date",
            "contract",
            "member_name",
            "volume",
            "volume_change",
            "volume_rank",
            "long_position",
            "long_change",
            "long_rank",
            "short_position",
            "short_change",
            "short_rank",
            "net_long",
            "net_short",
            "settle_price",
        ]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in snapshot.members:
                writer.writerow({key: getattr(row, key) for key in fieldnames})
        return {"json": json_path, "csv": csv_path}

    def write_summary(self, summary: PositionSummary, markdown: str) -> dict[str, Path]:
        stem = f"{summary.commodity_symbol.lower()}_{summary.contract.lower()}_{summary.trade_date}"
        json_path = self.report_dir / f"{stem}.json"
        md_path = self.report_dir / f"{stem}.md"
        json_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        md_path.write_text(markdown, encoding="utf-8")
        return {"json": json_path, "markdown": md_path}

    def write_raw(self, name: str, payload: Any) -> Path:
        path = self.raw_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
