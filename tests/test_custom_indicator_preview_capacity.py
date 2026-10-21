"""Ten real indicator configurations retain current TF proof without replay churn."""

from copy import deepcopy
from datetime import UTC, datetime
from math import sin

import pandas as pd

from application.services.custom_indicator_data import (
    MAX_PREVIEW_CELLS,
    CustomIndicatorData,
    _crypto_end,
)
from application.services.custom_indicators import catalog
from tests.test_custom_indicator_bootstrap import quote, witness
from tests.test_custom_indicator_data import NOW, Provider, frame


class MixedHistory(Provider):
    def __init__(self):
        super().__init__()
        self.data = frame(count=600)
        self.frames = {}

    def custom_indicator_history(self, symbol, **kwargs):
        if kwargs["exchange"] == "BIST":
            return super().custom_indicator_history(symbol, **kwargs)
        self.calls.append((symbol, kwargs))
        timeframe = kwargs["timeframe"]
        if timeframe not in self.frames:
            current = datetime(1970, 1, 5 if timeframe.endswith("W") else 1, tzinfo=UTC)
            stamps = []
            while current.timestamp() <= NOW:
                stamps.append(current)
                current = datetime.fromtimestamp(_crypto_end(current.timestamp(), timeframe), UTC)
            stamps = stamps[-600:]
            values = [100 + sin(stamp.timestamp() / 86400) for stamp in stamps]
            result = pd.DataFrame(
                {"Open": values, "High": 500.0, "Low": 1.0, "Close": values, "Volume": 100.0},
                index=pd.DatetimeIndex(stamps),
            )
            result.attrs.update(
                native_timeframe=timeframe,
                session_metadata={"timezone": "Etc/UTC", "session": "24x7"},
            )
            self.frames[timeframe] = result
        return self.frames[timeframe].copy()


def test_ten_default_previews_keep_latest_tf_rows_without_replaying_under_cell_pressure(
    monkeypatch,
):
    clock = [NOW + 0.2]
    provider = MixedHistory()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    replayed = []
    raw_cells = []
    expected_history = {}
    original = catalog.evaluate

    def counted(indicator, inputs, primary, frames, **kwargs):
        values = original(indicator, inputs, primary, frames, **kwargs)
        replayed.append(indicator)
        raw_cells.append(service._result_cells({"points": values[-128:]}))
        expected_history[(indicator, primary[-1].time)] = deepcopy(values[-128:])
        return values

    monkeypatch.setattr(catalog, "evaluate", counted)
    for symbol, market in (("THYAO", "BIST"), ("BTCUSDT", "Kripto")):
        for indicator in catalog.SPECS:
            service.preview(indicator, {}, symbol, market)
    keys = tuple(service.live._configs)
    assert len(keys) == 10
    for _ in keys:
        job = service._next_job()
        assert job is not None
        service.process(*job)
        assert service._results[job[0]]["error"] is None
    assert len(replayed) == 10
    assert set(service._preview_results) == set(keys)
    assert sum(raw_cells) > MAX_PREVIEW_CELLS * 4
    assert sum(map(service._result_cells, service._preview_results.values())) <= MAX_PREVIEW_CELLS
    assert service._next_job() is None
    for key in keys:
        cached = service._preview_results[key]
        points = cached["points"]
        expected = expected_history[(cached["config"]["indicator"], points[-1]["time"])]
        assert len(points) == 128
        assert [point["outputs"] for point in points] == [point["outputs"] for point in expected]
        assert all(not point["rows"] for point in points[:-1])
        assert points[-1]["rows"] == expected[-1]["rows"]
        assert points[-1]["rows"]
        witness(service, key, clock)
    evaluators = {key: item["evaluator"] for key, item in service.live._compiled.items()}
    fetches = len(provider.calls)
    for price in (110, 111, 109):
        for member in (("BIST", "THYAO"), ("Kripto", "BTCUSDT")):
            member_key = next(key for key in keys if key[:2] == member)
            quote(service, member_key, clock, price)
        for key in keys:
            config = service.live._configs[key]
            preview = service.preview(config["indicator"], config["inputs"], key[1], key[0])
            assert preview["state"] == "ready", preview["reason"]
            assert preview["latest"]["rows"]
            assert all(not point["rows"] for point in preview["points"][:-1])
            assert service._results[key]["points"][-1]["rows"] == []
            assert service._preview_results[key]["history_replayed"]
            assert service.live._compiled[key]["evaluator"] is evaluators[key]
        assert (
            sum(map(service._result_cells, service._preview_results.values())) <= MAX_PREVIEW_CELLS
        )
        assert service._next_job() is None
    assert len(replayed) == 10
    assert len(provider.calls) == fetches


def test_preview_compaction_does_not_mutate_shared_points_or_outputs():
    points = [
        {"time": 1, "rows": [{"timeframe": "1D", "rsi": 42}], "outputs": {"buy_signal": 1}},
        {"time": 2, "rows": [{"timeframe": "1D", "rsi": 45}], "outputs": {"buy_signal": 0}},
    ]
    alarm_result = {"points": points}
    before = deepcopy(alarm_result)
    compact = CustomIndicatorData._preview_points(points)
    assert alarm_result == before
    assert compact[0] is not points[0]
    assert compact[0]["rows"] == []
    assert compact[-1] == points[-1]
    assert compact[-1]["rows"]
    assert [point["outputs"] for point in compact] == [point["outputs"] for point in points]
    assert CustomIndicatorData._preview_points([]) == []
