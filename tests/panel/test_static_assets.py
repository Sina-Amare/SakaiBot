"""Offline contract tests for the panel's static assets (brand + design tokens).

Guards the Aigram glass redesign: the new teal tokens + glass utility must
exist, the old indigo/violet 'AI-stereotype' palette must be fully gone, and
the brand must read 'Aigram'.
"""

from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[2] / "src" / "panel" / "static"

# The indigo/violet palette the owner rejected — must not reappear.
FORBIDDEN_HEX = ["6366f1", "7c8bff", "8b5cf6", "a78bfa", "5b63e6"]


def _read(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_glass_tokens_present():
    css = _read("app.css")
    assert "--accent: #2dd4bf" in css, "aurora-teal accent token missing"
    assert "--glass-blur" in css and ".glass" in css, "glass system missing"
    assert "backdrop-filter" in css, "glass surfaces need backdrop-filter"


def test_no_legacy_indigo_palette():
    css = _read("app.css").lower()
    leaked = [h for h in FORBIDDEN_HEX if h in css]
    assert not leaked, f"legacy indigo/violet hex still in app.css: {leaked}"


def test_brand_is_aigram():
    html = _read("index.html")
    assert "Aigram" in html
    assert "<title>Aigram" in html
    # No leftover product-name in the visible shell brand.
    assert "SakaiBot Control Panel" not in html
    assert "> SakaiBot<" not in html


def test_mobile_shell_hooks_present():
    html = _read("index.html")
    for hook in ['id="menu-btn"', 'id="rail-btn"', 'id="scrim"']:
        assert hook in html, f"mobile shell hook missing: {hook}"
    css = _read("app.css")
    assert "@media (max-width: 760px)" in css and "@media (max-width: 400px)" in css
    js = _read("app.js")
    assert "initMobile" in js and "closeDrawers" in js, "mobile drawer JS missing"


def test_pwa_manifest_valid():
    import json

    m = json.loads(_read("manifest.webmanifest"))
    assert m["name"].startswith("Aigram")
    assert m["display"] == "standalone"
    assert m["start_url"] == "/" and m["scope"] == "/"
    purposes = {i.get("purpose") for i in m["icons"]}
    assert "maskable" in purposes, "a maskable icon is required for a real PWA"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_pwa_wiring():
    html = _read("index.html")
    assert 'rel="manifest"' in html and 'name="theme-color"' in html
    assert 'rel="apple-touch-icon"' in html
    sw = _read("sw.js")
    assert "aigram-shell" in sw and "addEventListener" in sw
    # commands/media must never be SW-cached
    assert "/api/cmd/" in sw and "never" in sw.lower()
    js = _read("app.js")
    assert 'serviceWorker' in js and 'register("/sw.js")' in js


def test_sw_shell_is_network_first():
    """Regression: the shell must be NETWORK-FIRST so fresh app.css/app.js are
    never pinned stale behind an updated index.html (the bug that left returning
    users on a broken half-old UI)."""
    sw = _read("sw.js")
    assert "network-first" in sw.lower()
    # the classic cache-first shell handler must be gone
    assert "caches.match(req).then((r) => r || fetch(req))" not in sw
    # returning users get auto-reloaded when the new worker takes over
    js = _read("app.js")
    assert "controllerchange" in js


def test_pwa_icons_exist():
    icons = STATIC / "icons"
    for name in ["icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png"]:
        p = icons / name
        assert p.exists() and p.stat().st_size > 200, f"icon missing/empty: {name}"


def test_panel_config_tls_gates_lan():
    from src.panel.config import PanelConfig

    assert not PanelConfig(token="t").tls_enabled  # loopback default
    with pytest.raises(ValueError):
        PanelConfig(host="192.168.1.9", token="t")  # LAN without TLS refused
    c = PanelConfig(host="192.168.1.9", token="t", tls_certfile="c.pem", tls_keyfile="k.pem")
    assert c.tls_enabled and c.url.startswith("https://")
