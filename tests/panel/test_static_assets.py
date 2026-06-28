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


def test_mobile_responsiveness_guards():
    """Regression: the phone-layout fixes must stay in place.

    These guard the bug where the single-column grid overflowed the phone
    viewport — a phantom horizontal scrollbar, the desktop account chip leaking
    into the topbar, and flex children refusing to shrink. They also guard the
    drawer footer that makes the dashboards reachable at all on phones (the
    topbar nav is hidden there)."""
    css = _read("app.css")
    # no phantom horizontal scroll from the off-canvas drawers
    assert "overflow-x: hidden" in css, "html/body must clip horizontal overflow"
    # the topbar's space hogs are hidden so min-content can't widen the column
    assert ".topbar .account, .topbar .divider { display: none; }" in css, \
        "account chip + dividers must be hidden on phones"
    # flex children must be allowed to shrink (min-width:0) instead of overflowing
    assert "min-width: 0" in css, "flex children need min-width:0 to shrink"

    html = _read("index.html")
    # the mobile drawer footer carries the dashboards (topbar nav is hidden)
    assert 'class="sidebar-foot"' in html, "mobile dashboard drawer footer missing"
    for dash in ["keys", "routing", "models", "auth", "help"]:
        assert f'data-dash="{dash}"' in html, f"mobile dashboard entry missing: {dash}"

    js = _read("app.js")
    # every dashboard entry point is wired (topbar nav AND drawer footer)
    assert '$$("[data-dash]")' in js, "dashboards must wire all [data-dash] entry points"
    assert "theme-toggle-m" in js, "mobile theme toggle must be wired"


def test_fonts_selfhosted():
    """Persian (Vazirmatn) + English (Inter) are self-hosted woff2 — never a CDN."""
    css = _read("app.css")
    assert "@font-face" in css, "no @font-face — fonts not actually loaded"
    assert "Vazirmatn" in css and "Inter" in css
    assert "/fonts/" in css, "@font-face must point at local /fonts, not a CDN"

    fonts_dir = STATIC / "fonts"
    for name in ["inter-400", "inter-500", "inter-600", "inter-700",
                 "vazirmatn-400", "vazirmatn-500", "vazirmatn-700"]:
        p = fonts_dir / f"{name}.woff2"
        assert p.exists() and p.stat().st_size > 2000, f"font missing/empty: {name}"
        assert p.read_bytes()[:4] == b"wOF2", f"not a valid woff2: {name}"

    sw = _read("sw.js")
    assert "/fonts/inter-400.woff2" in sw and "/fonts/vazirmatn-400.woff2" in sw, \
        "fonts must be precached in the service worker"

    # Never reach an external font CDN (offline + restricted-region safe).
    for blob in (css, _read("index.html"), _read("app.js")):
        low = blob.lower()
        assert "fonts.googleapis.com" not in low
        assert "fonts.gstatic.com" not in low


def test_lottie_vendored():
    """Animated (.tgs) stickers use a SELF-HOSTED lottie player + gzip decode."""
    js = _read("app.js")
    assert "/vendor/lottie.min.js" in js, "lottie must be referenced from /vendor"
    assert "DecompressionStream" in js, ".tgs gzip decode missing"
    p = STATIC / "vendor" / "lottie.min.js"
    assert p.exists() and p.stat().st_size > 50000, "lottie player missing/too small"
    assert "/vendor/lottie.min.js" in _read("sw.js"), "lottie must be precached"
    # no external CDN for the player
    for blob in (js, _read("index.html")):
        assert "cdn.jsdelivr.net" not in blob and "unpkg.com" not in blob


def test_pwa_install_affordance():
    """Installable on Android (beforeinstallprompt + button) and iOS (Add-to-Home hint)."""
    html = _read("index.html")
    assert 'id="install-btn"' in html, "Android install button missing"
    js = _read("app.js")
    assert "beforeinstallprompt" in js, "Android install prompt not handled"
    assert "appinstalled" in js, "appinstalled cleanup missing"
    assert "Add to Home Screen" in js, "iOS install hint missing"


def test_asset_cache_versions_consistent():
    """The ?v= cache-bust on app.css/app.js and the SW shell version must move
    together, or returning users get a half-stale UI."""
    html = _read("index.html")
    import re

    versions = set(re.findall(r"/app\.(?:css|js)\?v=(\d+)", html))
    assert len(versions) == 1, f"app.css/app.js cache versions disagree: {versions}"


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
