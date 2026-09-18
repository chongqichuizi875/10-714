from futures_intel.cli import build_parser


def test_offline_flag_is_accepted_after_demo() -> None:
    args = build_parser().parse_args(
        ["demo", "--offline", "--date", "2026-09-17", "--contract", "JM2701"]
    )
    assert args.command == "demo"
    assert args.offline is True
    assert args.date == "2026-09-17"
    assert args.contract == "JM2701"
