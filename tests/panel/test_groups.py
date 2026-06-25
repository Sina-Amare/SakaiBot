"""Offline tests for categorization/group management + TTS voices."""

import pytest


@pytest.mark.asyncio
async def test_list_groups(panel_state):
    d = await panel_state.groups.list_groups()
    titles = [g["title"] for g in d["items"]]
    assert "Friends Group" in titles      # the megagroup from mock dialogs
    assert all(g["id"] for g in d["items"])


@pytest.mark.asyncio
async def test_list_topics(panel_state):
    d = await panel_state.groups.list_topics(201)
    assert {"id": 12, "title": "Memes"} in d["items"]


def test_set_target(panel_state):
    r = panel_state.groups.set_target(201)
    assert r["target"]["id"] == 201
    panel_state.settings_manager.save_user_settings.assert_called()


def test_add_then_remove_mapping(panel_state):
    panel_state.groups.add_mapping("/Meme", 12)   # normalized to lowercase, no slash
    saved = panel_state.settings_manager.save_user_settings.call_args[0][0]
    assert saved["active_command_to_topic_map"].get("12") == ["meme"]

    panel_state.groups.remove_mapping("meme")
    saved2 = panel_state.settings_manager.save_user_settings.call_args[0][0]
    assert "meme" not in saved2["active_command_to_topic_map"].get("12", [])


def test_add_mapping_requires_command(panel_state):
    from src.panel.errors import PanelError
    with pytest.raises(PanelError):
        panel_state.groups.add_mapping("", 12)


def test_get_state_shape(panel_state):
    st = panel_state.groups.get_state()
    assert st["target"]["id"] == 201
    assert isinstance(st["mappings"], list)


def test_clear_mappings(panel_state):
    panel_state.groups.clear()
    saved = panel_state.settings_manager.save_user_settings.call_args[0][0]
    assert saved["active_command_to_topic_map"] == {}


def test_tts_voices(panel_state):
    v = panel_state.status.tts_voices()
    assert "orus" in v["voices"]
    assert len(v["voices"]) >= 25
    assert v["default"]
