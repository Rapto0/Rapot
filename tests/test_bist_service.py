import ssl

import pytest

import bist_service


class DummyClientSession:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False

    async def close(self):
        self.closed = True


class DummyConnector:
    def __init__(self, ssl=None):
        self.ssl = ssl


@pytest.mark.asyncio
async def test_bist_service_start_uses_isyatirim_ssl_context(monkeypatch):
    service = bist_service.BISTDataService()
    service._running = False

    ssl_context = ssl.create_default_context()
    created_tasks = []
    captured = {}

    def fake_get_ssl_context():
        return ssl_context

    def fake_create_task(coro):
        created_tasks.append(coro)
        coro.close()
        return object()

    def fake_client_session(**kwargs):
        session = DummyClientSession(**kwargs)
        captured["session"] = session
        return session

    monkeypatch.setattr(bist_service, "get_isyatirim_ssl_context", fake_get_ssl_context)
    monkeypatch.setattr(bist_service, "TCPConnector", DummyConnector)
    monkeypatch.setattr(bist_service.aiohttp, "ClientSession", fake_client_session)
    monkeypatch.setattr(bist_service.asyncio, "create_task", fake_create_task)

    await service.start()

    assert service._ssl_context is ssl_context
    assert isinstance(captured["session"].kwargs["connector"], DummyConnector)
    assert captured["session"].kwargs["connector"].ssl is ssl_context
    assert created_tasks

    await service.stop()


@pytest.mark.asyncio
async def test_bist_service_start_without_ssl_context(monkeypatch):
    service = bist_service.BISTDataService()
    service._running = False

    created_tasks = []
    captured = {}

    def fake_create_task(coro):
        created_tasks.append(coro)
        coro.close()
        return object()

    def fake_client_session(**kwargs):
        session = DummyClientSession(**kwargs)
        captured["session"] = session
        return session

    monkeypatch.setattr(bist_service, "get_isyatirim_ssl_context", lambda: None)
    monkeypatch.setattr(bist_service.aiohttp, "ClientSession", fake_client_session)
    monkeypatch.setattr(bist_service.asyncio, "create_task", fake_create_task)

    await service.start()

    assert service._ssl_context is None
    assert captured["session"].kwargs["connector"] is None
    assert created_tasks

    await service.stop()
