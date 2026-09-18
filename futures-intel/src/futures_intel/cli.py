from __future__ import annotations

import argparse
import sys
from pathlib import Path

from futures_intel.config import (
    DEFAULT_DATA_DIR,
    PACKAGE_ROOT,
    load_compliance,
    resolve_commodity,
)
from futures_intel.http import ComplianceError, PoliteClient
from futures_intel.report import render_markdown
from futures_intel.sources.eastmoney import EastmoneyPositionClient
from futures_intel.storage import LocalStore
from futures_intel.summarize import summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="futures-intel",
        description="Collect and summarize public futures member-position rankings for personal research.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run the JM / 焦煤 demo end to end")
    _add_collect_args(demo)
    demo.add_argument("--symbol", default="JM", help="Commodity symbol (default: JM)")
    demo.add_argument("--date", help="Trade date YYYY-MM-DD. Default: latest available.")
    demo.add_argument("--contract", help="Concrete contract such as JM2701. Default: main contract.")

    fetch = sub.add_parser("fetch", help="Fetch one variety and write local files")
    _add_collect_args(fetch)
    fetch.add_argument("--symbol", required=True)
    fetch.add_argument("--date")
    fetch.add_argument("--contract")

    summarize_cmd = sub.add_parser("summarize", help="Rebuild a markdown report from a processed snapshot")
    summarize_cmd.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    summarize_cmd.add_argument("--snapshot", type=Path, required=True, help="Processed JSON snapshot")
    return parser


def _add_collect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Local output directory (default: ./data)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Reuse cache only. Do not open a new network connection.",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "summarize":
        return _summarize_existing(args.snapshot, args.data_dir)
    return _collect(
        symbol=args.symbol,
        trade_date=args.date,
        contract=args.contract,
        data_dir=args.data_dir,
        offline=args.offline,
    )


def _collect(
    *,
    symbol: str,
    trade_date: str | None,
    contract: str | None,
    data_dir: Path,
    offline: bool,
) -> int:
    commodity = resolve_commodity(symbol)
    compliance = load_compliance()
    cache_dir = data_dir / ".http-cache"
    client = PoliteClient(compliance, cache_dir, allow_network=not offline)
    source = EastmoneyPositionClient(client, compliance)
    store = LocalStore(data_dir)

    try:
        snapshot = source.fetch_snapshot(commodity, trade_date=trade_date, contract=contract)
    except ComplianceError as exc:
        print(f"compliance stop: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"fetch failed: {exc}", file=sys.stderr)
        return 1

    summary = summarize(snapshot)
    markdown = render_markdown(summary)
    snapshot_paths = store.write_snapshot(snapshot)
    summary_paths = store.write_summary(summary, markdown)
    paths = {
        "snapshot_json": snapshot_paths["json"],
        "snapshot_csv": snapshot_paths["csv"],
        "report_json": summary_paths["json"],
        "report_markdown": summary_paths["markdown"],
    }

    print(markdown)
    print("local files:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    print(f"network requests this run: {client.requests_used}")
    print(f"cache directory: {cache_dir}")
    print(f"compliance notes: {PACKAGE_ROOT / 'docs' / 'COMPLIANCE.md'}")
    return 0


def _summarize_existing(snapshot_path: Path, data_dir: Path) -> int:
    import json
    from datetime import date

    from futures_intel.models import DailySnapshot, MarketTotals, MemberPosition

    raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    members = []
    for item in raw.get("members", []):
        members.append(
            MemberPosition(
                trade_date=date.fromisoformat(item["trade_date"]),
                exchange=item["exchange"],
                variety_code=item["variety_code"],
                variety_name=item["variety_name"],
                contract=item["contract"],
                member_name=item["member_name"],
                member_name_raw=item.get("member_name_raw", item["member_name"]),
                volume=item.get("volume"),
                volume_change=item.get("volume_change"),
                volume_rank=item.get("volume_rank"),
                long_position=item.get("long_position"),
                long_change=item.get("long_change"),
                long_rank=item.get("long_rank"),
                short_position=item.get("short_position"),
                short_change=item.get("short_change"),
                short_rank=item.get("short_rank"),
                net_long=item.get("net_long"),
                net_long_change=item.get("net_long_change"),
                net_short=item.get("net_short"),
                net_short_change=item.get("net_short_change"),
                settle_price=item.get("settle_price"),
                source=item.get("source", ""),
                source_page=item.get("source_page", ""),
            )
        )
    totals_raw = raw.get("totals") or {}
    snapshot = DailySnapshot(
        trade_date=date.fromisoformat(raw["trade_date"]),
        commodity_symbol=raw["commodity_symbol"],
        commodity_name=raw["commodity_name"],
        exchange=raw["exchange"],
        exchange_name=raw["exchange_name"],
        contract=raw["contract"],
        is_main_contract=bool(raw.get("is_main_contract")),
        settle_price=raw.get("settle_price"),
        members=members,
        totals=MarketTotals(**{key: totals_raw.get(key) for key in MarketTotals.__dataclass_fields__}),
        source=raw.get("source", ""),
        source_page=raw.get("source_page", ""),
        fetched_at=raw.get("fetched_at", ""),
        disclaimer=raw.get("disclaimer", ""),
    )
    summary = summarize(snapshot)
    markdown = render_markdown(summary)
    paths = LocalStore(data_dir).write_summary(summary, markdown)
    print(markdown)
    print("local files:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    return 0
