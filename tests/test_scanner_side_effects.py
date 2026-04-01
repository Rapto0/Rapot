from domain.events import SignalDomainEvent
from scanner_side_effects import persist_and_publish_signal_event


def test_persist_and_publish_signal_event_success_flow():
    captured_save_kwargs = {}
    published_payloads = []

    def _save_signal_fn(**kwargs):
        nonlocal captured_save_kwargs
        captured_save_kwargs = kwargs
        return 77

    def _publish_signal_fn(payload):
        published_payloads.append(payload)
        return True

    def _payload_builder_fn(signal_id, **kwargs):
        return {"id": signal_id, **kwargs}

    event = SignalDomainEvent(
        symbol="THYAO",
        market_type="BIST",
        strategy="HUNTER",
        signal_type="AL",
        timeframe="1D",
        score="8/10",
        price=302.15,
        details={"TopScore": "8/10"},
        special_tag="COK_UCUZ",
    )

    saved_id = persist_and_publish_signal_event(
        event=event,
        save_signal_fn=_save_signal_fn,
        publish_signal_fn=_publish_signal_fn,
        payload_builder_fn=_payload_builder_fn,
        details_serializer=lambda details: str(details),
    )

    assert saved_id == 77
    assert captured_save_kwargs["symbol"] == "THYAO"
    assert captured_save_kwargs["special_tag"] == "COK_UCUZ"
    assert captured_save_kwargs["details"] == "{'TopScore': '8/10'}"
    assert len(published_payloads) == 1
    assert published_payloads[0]["id"] == 77
    assert published_payloads[0]["symbol"] == "THYAO"


def test_persist_and_publish_signal_event_no_publish_when_persist_fails():
    published_payloads = []

    event = SignalDomainEvent(
        symbol="BTCUSDT",
        market_type="Kripto",
        strategy="COMBO",
        signal_type="SAT",
        timeframe="1D",
        score="5/10",
        price=61000.0,
        details=None,
        special_tag=None,
    )

    saved_id = persist_and_publish_signal_event(
        event=event,
        save_signal_fn=lambda **_kwargs: None,
        publish_signal_fn=lambda payload: published_payloads.append(payload) or True,
        payload_builder_fn=lambda signal_id, **kwargs: {"id": signal_id, **kwargs},
        details_serializer=lambda details: "" if details is None else str(details),
    )

    assert saved_id == 0
    assert published_payloads == []
