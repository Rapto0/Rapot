"""TradingView BTC native year boundaries; timestamps from 16 Oct diagnostics.

OHLC is synthetic. The real timestamps below are the provider-adjacent starts
reported in btc-native-history-5472-first.json, not locally resampled candles.
The official bar-alignment contract also covers non-dividing month periods:
https://www.tradingview.com/charting-library-docs/latest/ui_elements/Resolution/#bar-alignment
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from application.services.custom_indicator_data import CustomIndicatorData, _crypto_end, native_bars
from tests.test_custom_indicator_data import Provider

OBSERVED_BOUNDARIES = (
    ("3D", "2022-12-30", "2023-01-01"),
    ("3D", "2023-12-30", "2024-01-01"),
    ("3D", "2025-12-30", "2026-01-01"),
    ("7D", "2017-12-31", "2018-01-01"),
    ("7D", "2018-12-31", "2019-01-01"),
    ("7D", "2019-12-31", "2020-01-01"),
    ("7D", "2020-12-30", "2021-01-01"),
    ("2D", "2023-12-31", "2024-01-01"),
    ("2D", "2025-12-31", "2026-01-01"),
    ("2W", "2018-12-31", "2019-01-07"),
    ("2W", "2024-12-30", "2025-01-06"),
    ("3W", "2017-12-25", "2018-01-01"),
    ("3W", "2018-12-24", "2019-01-07"),
    ("3W", "2019-12-30", "2020-01-06"),
    ("3W", "2020-12-28", "2021-01-04"),
    ("4D", "2021-12-31", "2022-01-01"),
    ("4D", "2022-12-31", "2023-01-01"),
    ("4D", "2023-12-31", "2024-01-01"),
    ("4D", "2024-12-30", "2025-01-01"),
    ("5D", "2020-12-31", "2021-01-01"),
    ("5D", "2024-12-31", "2025-01-01"),
    ("6D", "2018-12-27", "2019-01-01"),
    ("6D", "2019-12-27", "2020-01-01"),
    ("6D", "2021-12-27", "2022-01-01"),
    ("6D", "2022-12-27", "2023-01-01"),
)


def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp()


def native_frame(timeframe, dates):
    frame = pd.DataFrame(
        {"Open": 100.0, "High": 102.0, "Low": 99.0, "Close": 101.0},
        index=pd.to_datetime(dates, utc=True, format="ISO8601"),
    )
    frame.attrs.update(native_timeframe=timeframe, session_metadata={"timezone": "Etc/UTC"})
    return frame


@pytest.mark.parametrize("timeframe,previous,following", OBSERVED_BOUNDARIES)
def test_real_provider_year_boundary_is_contiguous_and_confirmed(timeframe, previous, following):
    bars = native_bars(
        native_frame(timeframe, [previous, following]), timeframe, "Kripto", stamp(following) + 1
    )
    assert bars[0].end == bars[1].time == stamp(following)
    assert bars[0].confirmed and not bars[1].confirmed
    assert _crypto_end(stamp(previous), timeframe) == stamp(following)


@pytest.mark.parametrize(
    "timeframe,previous,current,expected_end",
    (
        ("2D", "2024-12-28", "2024-12-30", "2025-01-01"),
        ("3D", "2024-12-26", "2024-12-29", "2025-01-01"),
        ("7D", "2020-12-23", "2020-12-30", "2021-01-01"),
        ("2W", "2024-12-16", "2024-12-30", "2025-01-06"),
        ("3W", "2020-12-07", "2020-12-28", "2021-01-04"),
        ("5M", "2024-06-01", "2024-11-01", "2025-01-01"),
        ("7M", "2024-01-01", "2024-08-01", "2025-01-01"),
    ),
)
def test_current_bucket_ends_at_exact_anchor_without_future_witness(
    timeframe, previous, current, expected_end
):
    frame = native_frame(timeframe, [previous, current])
    just_before = native_bars(frame, timeframe, "Kripto", stamp(expected_end) - 1)
    at_end = native_bars(frame, timeframe, "Kripto", stamp(expected_end))
    assert just_before[-1].end == stamp(expected_end)
    assert not just_before[-1].confirmed and at_end[-1].confirmed


@pytest.mark.parametrize("year", range(2017, 2028))
def test_first_full_week_anchor_handles_all_new_year_weekdays(year):
    january = datetime(year, 1, 1, tzinfo=UTC)
    first_monday = january + timedelta(days=(7 - january.weekday()) % 7)
    # Last Monday in December is always a possible provider witness; a three
    # week nominal end extends past the first full week for every weekday.
    december = datetime(year - 1, 12, 31, tzinfo=UTC)
    last_monday = december - timedelta(days=december.weekday())
    assert _crypto_end(last_monday.timestamp(), "3W") == first_monday.timestamp()


@pytest.mark.parametrize("timeframe", ("2D", "3D", "4D", "5D", "6D", "7D", "2W", "3W", "5M"))
def test_missing_real_new_year_bar_is_still_rejected(timeframe):
    previous, following = next(
        ((old, new) for tf, old, new in OBSERVED_BOUNDARIES if tf == timeframe),
        ("2024-11-01", "2025-01-01"),
    )
    skipped = datetime.fromtimestamp(_crypto_end(stamp(following), timeframe), UTC).isoformat()
    with pytest.raises(ValueError, match="boşluk"):
        native_bars(
            native_frame(timeframe, [previous, skipped]), timeframe, "Kripto", stamp(skipped) + 1
        )


@pytest.mark.parametrize(
    "timeframe,previous,incorrect",
    (
        ("3D", "2022-12-30", "2023-01-02"),  # Old duration skipped the January anchor.
        ("2W", "2018-12-31", "2019-01-14"),
        ("3W", "2020-12-28", "2021-01-11"),  # Wrong first full week.
        ("3D", "2026-05-01", "2026-05-03"),  # Ordinary overlap.
        ("3D", "2026-05-01", "2026-05-07"),  # Ordinary missing bar.
        ("2W", "2026-05-04", "2026-05-25"),
        ("1D", "2026-05-01", "2026-05-03"),
        ("1M", "2026-01-01", "2026-03-01"),
    ),
)
def test_wrong_boundaries_are_not_made_valid_by_new_year_support(timeframe, previous, incorrect):
    with pytest.raises(ValueError, match="boşluk"):
        native_bars(
            native_frame(timeframe, [previous, incorrect]),
            timeframe,
            "Kripto",
            stamp(incorrect) + 1,
        )


@pytest.mark.parametrize("timeframe", ("1D", "2D", "7D", "1W", "2W", "3W", "15", "1S"))
def test_ordinary_duration_is_unchanged(timeframe):
    unit = timeframe[-1]
    duration = int(timeframe[:-1] if unit.isalpha() else timeframe) * {
        "D": 86400,
        "W": 604800,
        "S": 1,
    }.get(unit, 60)
    assert _crypto_end(stamp("2026-06-01"), timeframe) == stamp("2026-06-01") + duration


@pytest.mark.parametrize(
    "timeframe,start,end",
    (
        ("1M", "2024-02-01", "2024-03-01"),
        ("1M", "2025-02-01", "2025-03-01"),
        ("3M", "2024-10-01", "2025-01-01"),
        ("6M", "2024-07-01", "2025-01-01"),
        ("12M", "2024-01-01", "2025-01-01"),
    ),
)
def test_calendar_months_and_dividing_month_intervals_are_unchanged(timeframe, start, end):
    assert _crypto_end(stamp(start), timeframe) == stamp(end)


def test_live_packet_and_history_share_identical_year_boundary_validation():
    now = stamp("2025-01-01")
    service = CustomIndicatorData(provider=Provider(), clock=lambda: now)
    key = ("Kripto", "BTCUSDT", "2W")
    service.live._wanted.add(key)
    frame = native_frame("2W", ["2024-12-16", "2024-12-30"])
    event = {
        "kind": "bars",
        "key": key,
        "rows": [
            (stamp(str(index.date())), *row)
            for index, row in zip(frame.index, frame.to_numpy(), strict=True)
        ],
        "metadata": frame.attrs["session_metadata"],
        "received_at": now,
    }
    service.live._bars(event)
    history = native_bars(frame, "2W", "Kripto", now)
    assert service.live._buckets[key][0] == history
    assert history[-1].end == stamp("2025-01-06")
