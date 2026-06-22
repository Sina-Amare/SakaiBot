"""Panel service layer.

Each service wraps EXISTING SakaiBot components and returns plain JSON-friendly
data. Services perform READS + AI calls only. They must never send, edit,
forward, delete, react, or register Telegram event handlers — enforced by the
``tests/.../test_panel_no_send`` guard.
"""
