"""Throttle (ban-safety) unit tests: FloodWait handling + concurrency caps."""

import asyncio

import pytest
from telethon.errors import FloodWaitError

from src.panel.errors import PanelFloodError
from src.panel.throttle import Throttle


def make_flood(seconds: int) -> FloodWaitError:
    exc = FloodWaitError.__new__(FloodWaitError)
    exc.seconds = seconds
    return exc


@pytest.mark.asyncio
async def test_retries_once_after_short_floodwait(monkeypatch):
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    t = Throttle(min_gap_seconds=0.0)

    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] == 1:
            raise make_flood(2)
        return "ok"

    result = await t.tg_read(op)
    assert result == "ok"
    assert calls["n"] == 2
    assert 3 in slept  # slept e.seconds + 1


@pytest.mark.asyncio
async def test_hard_cap_surfaces_without_long_sleep(monkeypatch):
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    t = Throttle(min_gap_seconds=0.0)

    async def op():
        raise make_flood(300)

    with pytest.raises(PanelFloodError):
        await t.tg_read(op)
    # Never slept for the punitive duration.
    assert all(s < 120 for s in slept)


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency():
    t = Throttle(max_concurrent_rpc=3, min_gap_seconds=0.0)
    state = {"cur": 0, "max": 0}

    async def op():
        state["cur"] += 1
        state["max"] = max(state["max"], state["cur"])
        await asyncio.sleep(0.02)
        state["cur"] -= 1
        return True

    await asyncio.gather(*[t.tg_read(op) for _ in range(12)])
    assert state["max"] <= 3
