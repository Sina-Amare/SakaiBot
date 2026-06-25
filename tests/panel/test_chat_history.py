"""History now powers a real chat: media metadata, reply previews, polling."""

from types import SimpleNamespace

import pytest

from .conftest import make_message


@pytest.mark.asyncio
async def test_history_includes_media_metadata(panel_state):
    data = await panel_state.entity.history(201, limit=5)
    assert data["ok"] and data["items"]
    for it in data["items"]:
        assert "media_kind" in it
        assert "file_name" in it
        assert "mime" in it
        assert "has_media" in it
    assert "newest_id" in data and "oldest_id" in data


@pytest.mark.asyncio
async def test_history_after_id_polls_with_min_id(panel_state, mock_client):
    await panel_state.entity.history(201, after_id=3)
    assert any(
        c.kwargs.get("min_id") == 3 for c in mock_client.get_messages.call_args_list
    )


@pytest.mark.asyncio
async def test_history_attaches_reply_preview(panel_state, mock_client):
    async def _get(entity_id, **kw):
        if "ids" in kw:  # the batched reply-resolution read
            return [make_message(id=1, text="the original message")]
        return [
            make_message(
                id=2, text="a reply", reply_to=SimpleNamespace(reply_to_msg_id=1)
            )
        ]

    mock_client.get_messages.side_effect = _get
    data = await panel_state.entity.history(201, limit=5)
    assert data["items"][0]["reply"]["text"] == "the original message"
