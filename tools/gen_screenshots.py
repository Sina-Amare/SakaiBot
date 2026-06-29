"""Generate the README screenshots from a FAKE demo dataset (zero private data).

Run from the repo root:  python tools/gen_screenshots.py
Needs the dev extras (Playwright + Pillow):  pip install -e ".[dev]" && playwright install chromium

It renders the REAL panel (real FastAPI + real services) wired to a mock Telegram
client carrying invented contacts + a sample conversation + a placeholder photo,
then captures crisp 2x screenshots into docs/screenshots/. Because the data is
invented, the committed screenshots can never leak a real chat.
"""

import asyncio
import datetime
import shutil
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PIL import Image, ImageDraw, ImageFont
from telethon.tl.types import (  # noqa: E402
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "tests" / "panel"))
import conftest  # noqa: E402  (test fixtures double as a demo harness)
from src.ai.response_metadata import AIResponseMetadata  # noqa: E402
from src.panel.runner import start_panel  # noqa: E402

OUT = PROJECT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = Path(tempfile.mkdtemp())
PHOTO = ASSETS / "sunset.jpg"
STICKER = ASSETS / "sticker.webp"

# Deterministic gradient avatars per entity id (so the demo shows real photos,
# not initials, without any network).
AVATAR_COLORS = [
    ((45, 212, 191), (34, 211, 238)), ((244, 114, 182), (168, 85, 247)),
    ((251, 191, 36), (249, 115, 22)), ((96, 165, 250), (59, 130, 246)),
    ((52, 211, 153), (16, 185, 129)), ((248, 113, 113), (239, 68, 68)),
]


def make_avatar(eid, name, path):
    w = h = 240
    c1, c2 = AVATAR_COLORS[eid % len(AVATAR_COLORS)]
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h)
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    d = ImageDraw.Draw(img)
    letter = ((name or "?").strip()[:1] or "?").upper()
    try:
        font = ImageFont.truetype("arialbd.ttf", 120)
    except OSError:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]), letter,
           fill=(255, 255, 255), font=font)
    img.save(path, quality=90)


def make_sticker():
    s = 320
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([30, 30, s - 30, s - 30], fill=(45, 212, 191, 255))
    d.ellipse([110, 120, 142, 162], fill=(4, 37, 33, 255))
    d.ellipse([178, 120, 210, 162], fill=(4, 37, 33, 255))
    d.arc([110, 150, 210, 235], start=10, end=170, fill=(4, 37, 33, 255), width=12)
    img.save(STICKER, "WEBP")


def make_photo():
    w, h = 1000, 680
    img = Image.new("RGB", (w, h))
    px = img.load()
    top, mid, bot = (38, 26, 64), (228, 110, 70), (250, 206, 128)
    for y in range(h):
        t = y / h
        if t < 0.55:
            k = t / 0.55
            c = tuple(int(top[i] + (mid[i] - top[i]) * k) for i in range(3))
        else:
            k = (t - 0.55) / 0.45
            c = tuple(int(mid[i] + (bot[i] - mid[i]) * k) for i in range(3))
        for x in range(w):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, int(h * 0.5)
    d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=(255, 230, 170))
    d.rectangle([0, int(h * 0.78), w, h], fill=(70, 40, 60))
    img.save(PHOTO, quality=88)


def mk(id, text, out, hh, mm, **kw):
    return conftest.make_message(
        id=id, text=text, out=out,
        date=datetime.datetime(2026, 6, 24, hh, mm, 0), **kw,
    )


CONVO = [
    mk(1, "Hey! Did you get a chance to try the new panel? 👀", False, 18, 52),
    mk(2, "It honestly feels like a real messenger now", False, 18, 52),
    mk(3, "Yes! Sending + inline media is so smooth 🙌", True, 18, 54),
    mk(4, "And the dark theme looks 🔥", True, 18, 54),
    mk(10, "", False, 18, 55, media=SimpleNamespace(), sticker=SimpleNamespace(),
       document=SimpleNamespace(mime_type="image/webp", attributes=[])),
    mk(5, "Sunset from the office 🌇", False, 18, 57,
       media=SimpleNamespace(), photo=SimpleNamespace()),
    mk(6, "Wow, absolutely stunning 😍", True, 18, 58,
       reply_to=SimpleNamespace(reply_to_msg_id=5)),
    mk(7, "", False, 19, 1, media=SimpleNamespace(),
       document=SimpleNamespace(
           mime_type="application/pdf",
           attributes=[SimpleNamespace(file_name="aigram-design-spec.pdf")])),
    mk(8, "Got it — reviewing now 👍", True, 19, 2),
    mk(9, "Sounds perfect — see you at 7 🙌", False, 19, 4),
]


def iso(hh, mm):
    return datetime.datetime(2026, 6, 24, hh, mm, 0).isoformat()


DEMO_DIALOGS = [
    dict(id=1001, kind="pv", display_name="Maya Chen", username="@maya", has_photo=True, is_forum=False, preview="Sounds perfect — see you at 7 🙌", last_date=iso(19, 4)),
    dict(id=1002, kind="group", display_name="Design Team", username=None, has_photo=True, is_forum=False, preview="Alex: pushed the new mockups 🎨", last_date=iso(18, 40)),
    dict(id=1003, kind="channel", display_name="Aigram News", username="@aigram", has_photo=True, is_forum=False, preview="v2 is live — inline media + send", last_date=iso(17, 10)),
    dict(id=1004, kind="pv", display_name="Jordan Blake", username="@jordanb", has_photo=True, is_forum=False, preview="📷 Photo", last_date=iso(16, 22)),
    dict(id=1005, kind="bot", display_name="DevBot", username="@devbot", has_photo=True, is_forum=False, preview="Build #482 passed ✓", last_date=iso(15, 5)),
    dict(id=1006, kind="pv", display_name="Sam Patel", username="@samp", has_photo=True, is_forum=False, preview="🎤 Voice message", last_date=iso(14, 0)),
    dict(id=1007, kind="group", display_name="Book Club", username=None, has_photo=True, is_forum=False, preview="Priya: loved chapter 7!", last_date=iso(12, 30)),
    dict(id=1008, kind="pv", display_name="Mom ❤️", username=None, has_photo=True, is_forum=False, preview="Call me when you land ✈️", last_date=iso(9, 15)),
]

ANALYSIS = (
    "This is a warm, upbeat exchange between two close collaborators wrapping up "
    "the day.\n\n"
    "Tone: friendly and enthusiastic, with lots of positive reactions.\n"
    "Main topics: feedback on the new panel UI, a shared sunset photo, and a "
    "design spec to review.\n"
    "Action items: review aigram-design-spec.pdf, and meet up at 7."
)


def demo_get_messages(entity_id, **kw):
    if "ids" in kw:
        ids = kw["ids"]
        if isinstance(ids, list):  # batch (reply previews) -> list
            return [m for m in CONVO if m.id in ids]
        return next((m for m in CONVO if m.id == ids), None)  # single -> one msg
    if kw.get("min_id") or kw.get("max_id"):
        return []
    return list(reversed(CONVO))  # newest-first, like Telethon


def demo_download_media(msg, file=None, thumb=None):
    dest = Path(file)
    dest.parent.mkdir(parents=True, exist_ok=True)
    is_sticker = getattr(msg, "sticker", None) is not None
    src = STICKER if is_sticker else PHOTO
    if thumb is not None:  # thumb path already carries .thumb.jpg
        shutil.copy(src, dest)
        return str(dest)
    out = dest.with_suffix(".webp" if is_sticker else ".jpg")
    shutil.copy(src, out)
    return str(out)


# Presence variety so the header shows real Telegram-style statuses.
_PRESENCE = {
    1001: UserStatusOnline(expires=datetime.datetime(2026, 6, 24, 20, 0, 0)),
    1004: UserStatusRecently(),
    1006: UserStatusOffline(was_online=datetime.datetime(2026, 6, 24, 14, 0, 0)),
    1008: UserStatusRecently(),
}


def demo_get_entity(eid):
    row = next((d for d in DEMO_DIALOGS if d["id"] == eid), None)
    common = dict(id=eid, photo=SimpleNamespace(), verified=False)
    if row is None:
        return SimpleNamespace(first_name="User", last_name="", username=None,
                               bot=False, status=None, **common)
    uname = (row["username"] or "").lstrip("@") or None
    if row["kind"] in ("group", "channel"):
        return SimpleNamespace(
            title=row["display_name"], username=uname,
            participants_count=128 if row["kind"] == "group" else 12400,
            broadcast=(row["kind"] == "channel"), megagroup=(row["kind"] == "group"),
            **common,
        )
    parts = row["display_name"].split()
    return SimpleNamespace(
        first_name=parts[0], last_name=(parts[1] if len(parts) > 1 else ""),
        username=uname, bot=(row["kind"] == "bot"), status=_PRESENCE.get(eid),
        **common,
    )


async def main():
    make_photo()
    make_sticker()
    tmp = Path(tempfile.mkdtemp())
    client = conftest.build_mock_client()
    client.get_messages = AsyncMock(side_effect=demo_get_messages)
    client.download_media = AsyncMock(side_effect=demo_download_media)
    client.get_entity = AsyncMock(side_effect=demo_get_entity)

    def _dl_photo(entity, file=None):
        p = Path(file)
        p.parent.mkdir(parents=True, exist_ok=True)
        name = getattr(entity, "title", None) or getattr(entity, "first_name", "") or "?"
        make_avatar(int(getattr(entity, "id", 0)), name, p)
        return str(p)

    client.download_profile_photo = AsyncMock(side_effect=_dl_photo)

    ai = conftest.build_mock_ai()
    ai.analyze_conversation_messages = AsyncMock(return_value=AIResponseMetadata(
        response_text=ANALYSIS, model_used="gemini-2.5-flash",
        provider_used="Google Gemini", latency_seconds=2.1,
        input_tokens=320, output_tokens=140))

    state = conftest.build_state(tmp, client=client, ai=ai, real_photos=True)
    state.dialogs_cache = {"items": DEMO_DIALOGS, "ts": time.monotonic()}
    state.config.gemini_api_key_1 = "AIzaSyD3moK3yA00000000000000000000_qwA"
    state.config.gemini_api_key_2 = "AIzaSyB1234567890abcdefghijklmnop_t74E"
    state.config.gemini_api_keys = [state.config.gemini_api_key_1, state.config.gemini_api_key_2]
    state.config.openrouter_api_key_1 = "sk-or-v1-0000000000000000000000000000000000000000000000000000000062ad"
    state.config.openrouter_api_keys = [state.config.openrouter_api_key_1]

    handle = await start_panel(state)
    base = f"http://127.0.0.1:{state.panel_config.port}"
    tok = conftest.TOKEN
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
            await page.goto(f"{base}/?token={tok}")
            await page.wait_for_selector(".dialog-row", timeout=15000)
            await page.locator(".dialog-row").first.click()
            await page.wait_for_selector(".bubble", timeout=15000)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUT / "chat-dark.png"))

            await page.locator("#ev-ai-btn").click()
            await page.wait_for_selector("#modal:not(.hidden) .card", timeout=10000)
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / "ai-sheet.png"))

            analyze = page.locator(".card").filter(has=page.locator('.card-head h3:text-is("Analyze chat")')).first
            await analyze.get_by_role("button", name="Run").evaluate("el => el.click()")
            await page.wait_for_selector(".result .rhtml", timeout=15000)
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / "ai-result.png"))

            # scope to the topbar nav: the same data-dash chip also lives in the
            # mobile drawer footer, so an unscoped selector matches 2 elements.
            await page.locator('.dash-nav .chip[data-dash="keys"]').click()
            await page.wait_for_selector("#modal:not(.hidden) .modal-body", timeout=10000)
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUT / "keys.png"))
            await page.locator("#modal-close").click()
            await page.wait_for_selector("#modal", state="hidden", timeout=5000)

            # Profile view: click the chat name → info card + shared-media tabs.
            await page.locator("#ev-name").click()
            await page.wait_for_selector("#modal:not(.hidden) .profile-card", timeout=10000)
            await page.wait_for_timeout(700)
            await page.screenshot(path=str(OUT / "profile.png"))
            await page.locator("#modal-close").click()
            await page.wait_for_selector("#modal", state="hidden", timeout=5000)

            await page.locator("#theme-toggle").click()
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(OUT / "chat-light.png"))
            await browser.close()

            browser = await p.chromium.launch()
            # NOTE: do NOT pass is_mobile=True. Chromium's mobile emulation pins the
            # layout viewport to a device default (~411 CSS px) regardless of the
            # 390 viewport, so the >760px desktop layout leaks in: the account chip
            # stays visible and the topbar overflows. A plain 390px viewport at 2x
            # lays out at true phone width (account chip hidden, no overflow) while
            # still capturing a crisp retina image. has_touch keeps it touch-like.
            ctx = await browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, device_scale_factor=2)
            page = await ctx.new_page()
            await page.goto(f"{base}/?token={tok}")
            await page.wait_for_selector(".dialog-row", timeout=15000)
            await page.locator("#menu-btn").click()
            await page.wait_for_timeout(350)
            await page.locator(".dialog-row").first.click()
            await page.wait_for_selector(".bubble", timeout=15000)
            await page.wait_for_timeout(1000)
            await page.screenshot(path=str(OUT / "chat-mobile.png"))
            await browser.close()
    finally:
        await handle.stop()
    print("Screenshots written to", OUT)


if __name__ == "__main__":
    asyncio.run(main())
