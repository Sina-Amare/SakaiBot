"""Comprehensive LIVE browser E2E (real Chromium + real backend + real LLM).

Walks the full UI: token gate, sidebar tabs/search, entity selection, command
cards + toggle switches, running a real command, Messages tab + scroll-up
pagination, Media tab, every dashboard, and the dark/light theme toggle. Also
captures screenshots of both themes for visual QA.

Setup:  pip install playwright && playwright install chromium
Run:     SAKAIBOT_RUN_LIVE_TESTS=1 pytest tests/live/test_panel_browser.py -v
"""

from pathlib import Path

import pytest

from ._helpers import live_panel, setup_panel, skip_unless_live

pytestmark = [pytest.mark.live, pytest.mark.slow, skip_unless_live]

SHOTS = Path("temp/panel_shots")


@pytest.mark.asyncio
async def test_full_ui_walkthrough():
    try:
        from playwright.async_api import async_playwright, expect
    except ImportError:
        pytest.skip("playwright not installed")

    SHOTS.mkdir(parents=True, exist_ok=True)

    async with live_panel() as (state, base, client):
        if not state.ai_processor.is_configured:
            pytest.skip("AI provider not configured")

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            # Surface any JS console errors as test failures.
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                # --- gate auto-unlock via ?token ---
                await page.goto(f"{base}/?token={state.panel_config.token}")
                await page.wait_for_selector(".dialog-row", timeout=30000)
                await expect(page.locator("#gate")).to_be_hidden()

                # --- sidebar: counts + tab switching + search ---
                rows_all = await page.locator(".dialog-row").count()
                assert rows_all > 0
                await page.locator('.tab[data-kind="channel"]').click()
                await page.wait_for_timeout(400)
                # every visible badge should now say "channel"
                badges = await page.locator(".dialog-row .kind-badge").all_inner_texts()
                assert badges and all(b.strip().lower() == "channel" for b in badges)
                await page.locator('.tab[data-kind="pv"]').click()
                await page.wait_for_selector(".dialog-row", timeout=10000)
                await page.wait_for_timeout(300)

                # --- select first PV → the chat opens (header + scroll + composer) ---
                await page.locator(".dialog-row").first.click()
                await page.wait_for_selector("#chat-scroll", timeout=10000)
                await expect(page.locator(".composer-input")).to_be_visible()
                await page.wait_for_timeout(2500)  # let history + inline media render
                await page.screenshot(path=str(SHOTS / "01_dark_chat.png"), full_page=False)

                # --- chat: scroll-up pagination (when the chat has messages) ---
                bubbles = await page.locator(".bubble").count()
                if bubbles:
                    await page.eval_on_selector("#chat-scroll", "el => el.scrollTop = 0")
                    await page.wait_for_timeout(2200)
                    assert await page.locator(".bubble").count() >= bubbles

                # --- composer: typing toggles the send button (NO real send to a PV) ---
                await page.locator(".composer-input").fill("draft — not sent during tests")
                await expect(page.locator("#composer-send")).to_be_enabled()
                await page.locator(".composer-input").fill("")
                await expect(page.locator("#composer-send")).to_be_disabled()

                # --- AI sheet: open, toggle a switch, run a real prompt → rail result ---
                await page.locator("#ev-ai-btn").click()
                await page.wait_for_selector("#modal:not(.hidden) .card", timeout=10000)
                await expect(page.locator('.card-head h3:text-is("Prompt")')).to_be_visible()
                await page.screenshot(path=str(SHOTS / "01b_dark_ai_sheet.png"), full_page=False)
                prompt_card = page.locator(".card").filter(
                    has=page.locator('.card-head h3:text-is("Prompt")')
                ).first
                toggle = prompt_card.locator(".toggle").first
                cb = toggle.locator("input[type=checkbox]")
                assert not await cb.is_checked()
                await toggle.click()
                assert await cb.is_checked()
                await toggle.click()  # back off so the prompt runs fast
                await prompt_card.locator("textarea").fill("Reply with exactly one word: PONG")
                await prompt_card.get_by_role("button", name="Run").click()
                # running closes the AI sheet and the result streams into the rail
                await page.wait_for_selector(".result .rhtml", timeout=180000)
                result_text = await page.locator(".result .rhtml").first.inner_text()
                assert result_text.strip()
                await expect(page.locator("#rail-count")).to_contain_text("(1)")
                await page.screenshot(path=str(SHOTS / "02_dark_result.png"), full_page=False)

                # --- Media sheet opens (tiles or a friendly empty state) ---
                await page.locator("#ev-media-btn").click()
                await page.wait_for_selector("#modal:not(.hidden) .modal-body", timeout=10000)
                await page.wait_for_timeout(2200)
                assert await page.locator("#modal-body").is_visible()
                await page.locator("#modal-close").click()
                await page.wait_for_selector("#modal", state="hidden", timeout=5000)

                # --- dashboards: each opens and closes ---
                for dash in ["keys", "routing", "models", "auth", "help"]:
                    await page.locator(f'.chip[data-dash="{dash}"]').click()
                    await page.wait_for_selector("#modal:not(.hidden) .modal-body", timeout=10000)
                    await page.wait_for_timeout(1200)
                    if dash == "keys":
                        await page.screenshot(path=str(SHOTS / "03_dark_keys.png"), full_page=False)
                    if dash == "routing":
                        await page.screenshot(path=str(SHOTS / "08_dark_routing.png"), full_page=False)
                    await page.locator("#modal-close").click()
                    await page.wait_for_selector("#modal", state="hidden", timeout=5000)

                # --- theme toggle → light, and back ---
                assert await page.evaluate("document.documentElement.dataset.theme") == "dark"
                await page.locator("#theme-toggle").click()
                assert await page.evaluate("document.documentElement.dataset.theme") == "light"
                await page.wait_for_timeout(400)
                await page.screenshot(path=str(SHOTS / "04_light_chat.png"), full_page=False)
                # light AI sheet for a second visual QA shot
                await page.locator("#ev-ai-btn").click()
                await page.wait_for_selector("#modal:not(.hidden) .card", timeout=10000)
                await page.wait_for_timeout(300)
                await page.screenshot(path=str(SHOTS / "05_light_ai_sheet.png"), full_page=False)
                await page.locator("#modal-close").click()
                await page.wait_for_selector("#modal", state="hidden", timeout=5000)

                # no JS console errors anywhere in the walkthrough
                assert not errors, f"JS errors during walkthrough: {errors}"
            finally:
                await browser.close()


@pytest.mark.asyncio
async def test_mobile_and_pwa():
    """Mobile drawers + installable PWA (manifest + service worker) in a phone viewport."""
    try:
        from playwright.async_api import async_playwright, expect
    except ImportError:
        pytest.skip("playwright not installed")

    SHOTS.mkdir(parents=True, exist_ok=True)

    async with live_panel() as (state, base, client):
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
            ctx = await browser.new_context(
                viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
            )
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                await page.goto(f"{base}/?token={state.panel_config.token}")
                await page.wait_for_selector(".dialog-row", timeout=30000)

                # hamburger is visible on mobile; sidebar starts off-canvas
                await expect(page.locator("#menu-btn")).to_be_visible()
                assert "open" not in (await page.get_attribute(".sidebar", "class") or "")

                # open the sidebar drawer
                await page.locator("#menu-btn").click()
                await page.wait_for_timeout(350)
                assert "open" in (await page.get_attribute(".sidebar", "class") or "")
                await expect(page.locator("#scrim")).to_be_visible()
                await page.screenshot(path=str(SHOTS / "06_mobile_sidebar.png"))

                # picking a chat closes the drawer and shows the chat composer
                await page.locator(".dialog-row").first.click()
                await page.wait_for_timeout(350)
                assert "open" not in (await page.get_attribute(".sidebar", "class") or "")
                await page.wait_for_selector("#chat-scroll", timeout=10000)
                await expect(page.locator(".composer-input")).to_be_visible()
                await page.wait_for_timeout(1500)
                await page.screenshot(path=str(SHOTS / "07_mobile_chat.png"))

                # AI sheet opens full-screen-ish on mobile
                await page.locator("#ev-ai-btn").click()
                await page.wait_for_selector("#modal:not(.hidden) .card", timeout=10000)
                await page.screenshot(path=str(SHOTS / "07b_mobile_ai.png"))
                await page.locator("#modal-close").click()
                await page.wait_for_selector("#modal", state="hidden", timeout=5000)

                # results drawer toggles via the rail button
                await page.locator("#rail-btn").click()
                await page.wait_for_timeout(300)
                assert "open" in (await page.get_attribute(".rail", "class") or "")

                # PWA: manifest reachable + valid, service worker registers
                resp = await page.request.get(f"{base}/manifest.webmanifest")
                assert resp.ok
                man = await resp.json()
                assert man["name"].startswith("Aigram")
                await page.wait_for_timeout(1500)
                has_sw = await page.evaluate(
                    "async () => 'serviceWorker' in navigator && !!(await navigator.serviceWorker.getRegistration())"
                )
                assert has_sw, "service worker did not register"

                assert not errors, f"JS errors on mobile: {errors}"
            finally:
                await browser.close()


@pytest.mark.asyncio
async def test_setup_wizard_renders():
    """First-run onboarding wizard renders (no real login is submitted)."""
    try:
        from playwright.async_api import async_playwright, expect
    except ImportError:
        pytest.skip("playwright not installed")

    SHOTS.mkdir(parents=True, exist_ok=True)
    async with setup_panel() as (state, base):
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Chromium unavailable: {exc}")
            page = await browser.new_page(viewport={"width": 440, "height": 880})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                await page.goto(f"{base}/?token=setup-token")
                # needs_setup is True (no client) -> the wizard appears
                await page.wait_for_selector("#wizard .gate-card", timeout=15000)
                await expect(page.locator("#wizard")).to_contain_text("Set up Aigram")
                assert await page.locator("#wz-id").is_visible()
                assert await page.locator("#wz-phone").is_visible()
                await page.screenshot(path=str(SHOTS / "09_setup_wizard.png"))
                assert not errors, f"JS errors in wizard: {errors}"
            finally:
                await browser.close()
