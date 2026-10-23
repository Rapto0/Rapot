"""Synthetic session refresh keeps healthy charts, never credentials or stale accounts."""

import base64
import json
import threading
from types import SimpleNamespace

import pytest

from application.services.borsapy_gateway import (
    _AUTH_LOCK,
    CUSTOM_AUTH_REFRESH_SECONDS,
    BorsapyGateway,
    BorsapyGatewayError,
)
from infrastructure.providers.custom_indicator_stream import NativeStreamPool
from tests.test_borsapy_gateway import connect
from tests.test_borsapy_gateway import gateway as gateway_fixture
from tests.test_custom_indicator_leases import DAY, LONG, event, setup_book
from tests.test_custom_indicator_stream import Transport


@pytest.fixture
def gateway(tmp_path):
    yield from gateway_fixture.__wrapped__(tmp_path)


def pool_for(gateway):
    pool = NativeStreamPool(
        Transport,
        gateway._token,
        gateway.memory_epoch(),
        lambda _: None,
        clock=lambda: 1_800_000_000.0,
    )
    pool.configure({("BIST", "THYAO", "1D")})
    gateway._custom_streams.append(pool)
    return pool


def test_periodic_refresh_uses_same_epoch_and_sockets_without_chart_recreation(gateway):
    connect(gateway)
    pool = pool_for(gateway)
    epoch = gateway.memory_epoch()
    stream = next(iter(pool._streams.values()))
    sessions = stream.sessions.copy()
    before = list(stream.sent)
    sent_without_locks = []
    original_send = stream._ws.send

    def send(message):
        sent_without_locks.append(not _AUTH_LOCK._is_owned())
        acquired = []

        def receiver():
            with stream._lock:
                acquired.append(True)

        worker = threading.Thread(target=receiver)
        worker.start()
        worker.join(1)
        assert acquired == [True]
        return original_send(message)

    stream._ws.send = send
    gateway.clock[0] = CUSTOM_AUTH_REFRESH_SECONDS - 1
    gateway.refresh_custom_indicator_auth()
    assert gateway.fake.auth_calls == 1
    gateway.clock[0] += 1
    gateway.refresh_custom_indicator_auth()
    assert gateway.fake.auth_calls == 2
    assert gateway.memory_epoch() == epoch and pool.connected
    assert stream.sessions == sessions
    assert stream.sent[len(before) :] == [{"m": "set_auth_token", "p": [gateway._token]}]
    assert sent_without_locks == [True]
    assert gateway.custom_indicator_auth_status() == {
        "provider_paused": False,
        "refresh_count": 1,
        "refresh_error": False,
        "retry_waiting": False,
        "retry_after_seconds": 0,
    }
    gateway.refresh_custom_indicator_auth()
    assert gateway.fake.auth_calls == 2


def test_failed_refresh_is_visible_and_retried_with_bounded_backoff(gateway):
    connect(gateway)
    pool_for(gateway)
    gateway.clock[0] = CUSTOM_AUTH_REFRESH_SECONDS
    gateway.fake.fail_auth = True
    for expected in (30, 60, 120, 240, 480, 960, 1800, 1800):
        before_calls = gateway.fake.auth_calls
        with pytest.raises(BorsapyGatewayError):
            gateway.refresh_custom_indicator_auth()
        due = gateway._token_refresh_retry_at
        assert due - gateway.clock[0] == expected
        assert gateway.custom_indicator_auth_status()["refresh_error"]
        assert gateway.fake.auth_calls == before_calls + 1
        for _ in range(3):
            with pytest.raises(BorsapyGatewayError):
                gateway.refresh_custom_indicator_auth()
        assert gateway.fake.auth_calls == before_calls + 1
        gateway.clock[0] = due
    gateway.fake.fail_auth = False
    gateway.refresh_custom_indicator_auth()
    assert gateway.status()["authenticated"]
    assert not gateway.custom_indicator_auth_status()["refresh_error"]


def test_auth_rejection_forces_bounded_refresh_before_regular_deadline(gateway):
    connect(gateway)
    pool = pool_for(gateway)
    pool._auth_refresh_required = True
    gateway.clock[0] = 299
    gateway.refresh_custom_indicator_auth()
    assert gateway.fake.auth_calls == 1
    gateway.clock[0] = 300
    gateway.refresh_custom_indicator_auth()
    assert gateway.fake.auth_calls == 2
    assert not pool.auth_refresh_required


def test_jwt_expiry_hint_shortens_refresh_and_expired_token_is_rejected(monkeypatch):
    monkeypatch.setattr("application.services.borsapy_gateway.time.time", lambda: 1000)

    def token(exp):
        payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=").decode()
        return "synthetic." + payload + ".signature"

    assert BorsapyGateway._token_refresh_delay(token(1300)) == 240
    assert BorsapyGateway._token_refresh_delay(token(10000)) == 1800
    assert BorsapyGateway._token_refresh_delay(token(10**400)) == 1800
    assert BorsapyGateway._token_refresh_delay("opaque-provider-token") == 1800
    assert BorsapyGateway._token_refresh_delay("a.not-json.signature") == 1800
    for payload in ([], 123, "opaque", None):
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        assert BorsapyGateway._token_refresh_delay("a." + encoded + ".signature") == 1800
    with pytest.raises(BorsapyGatewayError):
        BorsapyGateway._token_refresh_delay(token(1030))


def test_account_file_change_during_refresh_closes_old_pool_before_token_send(gateway):
    connect(gateway)
    pool = pool_for(gateway)
    epoch = gateway.memory_epoch()
    stream = next(iter(pool._streams.values()))
    before = list(stream.sent)
    authenticate = gateway._session_auth

    def changed(*args, **kwargs):
        result = authenticate(*args, **kwargs)
        gateway._store.save({"session": "new-synthetic-session", "session_sign": "new-signature"})
        return result

    gateway._session_auth = changed
    gateway.clock[0] = CUSTOM_AUTH_REFRESH_SECONDS
    with pytest.raises(BorsapyGatewayError):
        gateway.refresh_custom_indicator_auth()
    assert pool.closed and gateway.memory_epoch() != epoch
    assert stream.sent == before


def test_changed_auth_reopens_entitlement_refusals_without_reusing_old_lease():
    book, _ = setup_book()
    book.confirm(event(book, DAY))
    old = event(book, LONG)
    assert book.reject({**old, "reason": "permission_denied"})
    book.auth_refreshed()
    fresh = event(book, LONG)
    assert fresh["native_lease_id"] != old["native_lease_id"]
    assert not book.confirm(old)["accepted"]
    assert book.confirm(fresh)["accepted"]


def test_account_change_closes_reusable_history_without_waiting_for_request(gateway):
    connect(gateway)
    closed = []
    gateway._custom_history = SimpleNamespace(close=lambda: closed.append(True))
    gateway.clear()
    assert closed == [True] and gateway._custom_history is None


def test_control_backoff_does_not_repeat_auth_or_invalidate_all_members(monkeypatch):
    from tests.test_custom_indicator_live_data import ready_service

    clock, provider, service, _, _, _ = ready_service()
    attempts, gaps = [], []
    deadline = clock[0] + 30

    def failed_refresh():
        attempts.append(clock[0])
        raise BorsapyGatewayError("Synthetic auth failure", 409)

    provider.refresh_custom_indicator_auth = failed_refresh
    provider.custom_indicator_auth_status = lambda: {
        "retry_after_seconds": max(0, deadline - clock[0])
    }
    original_gap = service.live_gap

    def gap(*args, **kwargs):
        gaps.append(True)
        return original_gap(*args, **kwargs)

    monkeypatch.setattr(service, "live_gap", gap)
    service.live.control_step()
    generation = service.live._generation
    assert service.live._retry == deadline
    for _ in range(29):
        clock[0] += 1
        service.live.control_step()
    assert len(attempts) == len(gaps) == 1
    assert service.live._generation == generation
    clock[0] += 1
    service.live.control_step()
    assert len(attempts) == len(gaps) == 2


def test_changed_account_bypasses_control_backoff_without_old_seed(monkeypatch):
    from tests.test_custom_indicator_live_data import ready_service

    clock, provider, service, _, _, _ = ready_service()
    provider.refresh_custom_indicator_auth = lambda: (_ for _ in ()).throw(
        BorsapyGatewayError("Synthetic auth failure", 409)
    )
    provider.custom_indicator_auth_status = lambda: {"retry_after_seconds": 1800}
    service.live.control_step()
    assert not service.live._compiled
    assert service.live._retry > clock[0]
    provider.generation += 1
    refreshed = []
    provider.refresh_custom_indicator_auth = lambda: refreshed.append(True)
    connection = SimpleNamespace(
        epoch=provider.generation,
        connected=True,
        configure=lambda *args, **kwargs: None,
    )
    provider.create_custom_indicator_stream = lambda callback: connection
    service.live.control_step()
    assert refreshed == [True]
    assert service.live._connection is connection
    assert not service.live._compiled


def test_credentials_changed_during_auth_backoff_allow_new_account_immediately(gateway):
    connect(gateway)
    gateway.clock[0] = CUSTOM_AUTH_REFRESH_SECONDS
    gateway.fake.fail_auth = True
    with pytest.raises(BorsapyGatewayError):
        gateway.refresh_custom_indicator_auth()
    assert gateway.custom_indicator_auth_status()["retry_waiting"]
    epoch = gateway.memory_epoch()
    gateway._store.save({"session": "changed-session", "session_sign": "changed-signature"})
    assert gateway.data_epoch() != epoch
    assert not gateway.custom_indicator_auth_status()["retry_waiting"]
    gateway.fake.fail_auth = False
    with gateway._account_lock():
        gateway._prepare(require_auth=True)
    assert gateway.status()["authenticated"]
