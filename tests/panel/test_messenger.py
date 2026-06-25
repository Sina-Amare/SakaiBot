"""The composer send path — the panel's single, explicit write to Telegram.

The no-send guard (test_no_send.py) proves the READ/command endpoints never
send; this proves the send route DOES send when the user asks, with validation
and proper reply threading.
"""

import pytest


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
