from __future__ import annotations

from collections.abc import Callable
from typing import Any

from domain.events import SignalDomainEvent


def persist_and_publish_signal(
    *,
    save_signal_fn: Callable[..., int | None],
    publish_signal_fn: Callable[[dict[str, Any]], bool],
    payload_builder_fn: Callable[..., dict[str, Any]],
    save_kwargs: dict[str, Any],
    payload_kwargs: dict[str, Any],
) -> int:
    """
    Persist a signal and publish realtime payload when persistence succeeds.
    """
    signal_id = save_signal_fn(**save_kwargs)
    if signal_id:
        payload = payload_builder_fn(signal_id=int(signal_id), **payload_kwargs)
        publish_signal_fn(payload)
    return int(signal_id or 0)


def persist_and_publish_signal_event(
    *,
    event: SignalDomainEvent,
    save_signal_fn: Callable[..., int | None],
    publish_signal_fn: Callable[[dict[str, Any]], bool],
    payload_builder_fn: Callable[..., dict[str, Any]],
    details_serializer: Callable[[dict[str, Any] | None], str | None],
) -> int:
    """
    Persist and publish a typed scanner signal event.
    """
    serialized_details = details_serializer(event.details)
    return persist_and_publish_signal(
        save_signal_fn=save_signal_fn,
        publish_signal_fn=publish_signal_fn,
        payload_builder_fn=payload_builder_fn,
        save_kwargs=event.to_save_kwargs(serialized_details=serialized_details),
        payload_kwargs=event.to_payload_kwargs(),
    )
