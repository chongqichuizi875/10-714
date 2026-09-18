from futures_intel.models import clean_member_name, clean_rank, parse_trade_date


def test_parse_trade_date_strips_time() -> None:
    assert parse_trade_date("2026-09-17 00:00:00").isoformat() == "2026-09-17"


def test_clean_rank_treats_9999_as_missing() -> None:
    assert clean_rank(1) == 1
    assert clean_rank(9999) is None
    assert clean_rank(None) is None


def test_clean_member_name_drops_agency_suffix() -> None:
    assert clean_member_name("示例甲", "示例甲（代客）") == "示例甲"
    assert clean_member_name(None, "示例乙（代客）") == "示例乙"
