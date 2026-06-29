"""The composer send path — the panel's single, explicit write to Telegram.

The no-send guard (test_no_send.py) proves the READ/command endpoints never
send; this proves the send route DOES send when the user asks, with validation
and proper reply threading.
"""

from unittest.mock import AsyncMock

import pytest

from .conftest import make_message


@pytest.mark.asyncio
async def test_send_file_uses_throttle_and_echoes(panel_state, mock_client):
    mock_client.send_file = AsyncMock(return_value=make_message(id=321, text="cap", out=True))
    out = await panel_state.messenger.send_attachment(
        201, b"some-bytes", "photo.jpg", caption="cap", reply_to=7
    )
    assert out["ok"] and out["message"]["id"] == 321
    mock_client.send_file.assert_awaited_once()
    _, kwargs = mock_client.send_file.call_args
    assert kwargs.get("reply_to") == 7


@pytest.mark.asyncio
async def test_send_file_rejects_empty_and_oversize(panel_state, mock_client):
    with pytest.raises(Exception):
        await panel_state.messenger.send_attachment(201, b"", "x.bin")
    with pytest.raises(Exception):
        await panel_state.messenger.send_attachment(201, b"x" * (21 * 1024 * 1024), "big.bin")
    mock_client.send_file.assert_not_called()


def test_send_calls_telegram_and_echoes(client, mock_client, auth_headers):
    resp = client.post(
        "/api/entity/101/send", json={"text": "hello there"}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["message"]["out"] is True
    assert "id" in data["message"]

    mock_client.send_message.assert_awaited_once()
    args, kwargs = mock_client.send_message.call_args
    assert args[0] == 101
    assert args[1] == "hello there"
    assert kwargs.get("reply_to") is None


def test_send_threads_reply(client, mock_client, auth_headers):
    resp = client.post(
        "/api/entity/101/send", json={"text": "re", "reply_to": 42}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    _, kwargs = mock_client.send_message.call_args
    assert kwargs.get("reply_to") == 42


def test_send_trims_and_rejects_empty(client, mock_client, auth_headers):
    resp = client.post(
        "/api/entity/101/send", json={"text": "   "}, headers=auth_headers
    )
    assert resp.status_code == 400
    mock_client.send_message.assert_not_called()


def test_send_rejects_too_long(client, mock_client, auth_headers):
    resp = client.post(
        "/api/entity/101/send", json={"text": "x" * 5000}, headers=auth_headers
    )
    assert resp.status_code == 400
    mock_client.send_message.assert_not_called()


def test_send_requires_token(client):
    resp = client.post("/api/entity/101/send", json={"text": "hi"})
    assert resp.status_code == 401
