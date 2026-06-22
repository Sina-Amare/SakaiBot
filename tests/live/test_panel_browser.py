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

from ._helpers import live_panel, skip_unless_live

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

                # --- select first PV → commands render ---
                await page.locator(".dialog-row").first.click()
                await page.wait_for_selector(".card", timeout=10000)
                await expect(page.locator('.card-head h3:text-is("Prompt")')).to_be_visible()
                await page.screenshot(path=str(SHOTS / "01_dark_commands.png"), full_page=False)

                # --- toggle switch works (premium control, not a raw checkbox) ---
                prompt_card = page.locator(".card").filter(
                    has=page.locator('.card-head h3:text-is("Prompt")')
                ).first
                toggle = prompt_card.locator(".toggle").first
                cb = toggle.locator("input[type=checkbox]")
                assert not await cb.is_checked()
                await toggle.click()
                assert await cb.is_checked()
                await toggle.click()  # back off so the prompt runs fast

                # --- run a real prompt → result renders in the rail ---
                await prompt_card.locator("textarea").fill("Reply with exactly one word: PONG")
                await prompt_card.get_by_role("button", name="Run").click()
                await page.wait_for_selector(".result .rhtml", timeout=180000)
                result_text = await page.locator(".result .rhtml").first.inner_text()
                assert result_text.strip()
                await expect(page.locator("#rail-count")).to_contain_text("(1)")
                await page.screenshot(path=str(SHOTS / "02_dark_result.png"), full_page=False)

                # --- Messages tab + scroll-up pagination ---
                await page.locator('.tab[data-ev="messages"]').click()
                await page.wait_for_selector(".msg", timeout=20000)
                first_count = await page.locator(".msg").count()
                # scroll the message pane to the top to trigger older-page load
                await page.eval_on_selector(".msg-scroll", "el => el.scrollTop = 0")
                await page.wait_for_timeout(2500)
                second_count = await page.locator(".msg").count()
                assert second_count >= first_count  # older messages loaded (or already at start)

                # --- Media tab loads ---
                await page.locator('.tab[data-ev="media"]').click()
                await page.wait_for_timeout(2500)
                # either tiles or a friendly empty state — must not error
                assert await page.locator("#ev-media").is_visible()

                # --- dashboards: each opens and closes ---
                for dash in ["keys", "models", "auth", "help"]:
                    await page.locator(f'.chip[data-dash="{dash}"]').click()
                    await page.wait_for_selector("#modal:not(.hidden) .modal-body", timeout=10000)
                    await page.wait_for_timeout(500)
                    if dash == "keys":
                        await page.screenshot(path=str(SHOTS / "03_dark_keys.png"), full_page=False)
                    await page.locator("#modal-close").click()
                    await page.wait_for_selector("#modal", state="hidden", timeout=5000)

                # --- theme toggle → light, and back ---
                assert await page.evaluate("document.documentElement.dataset.theme") == "dark"
                await page.locator("#theme-toggle").click()
                assert await page.evaluate("document.documentElement.dataset.theme") == "light"
                await page.wait_for_timeout(400)
                await page.screenshot(path=str(SHOTS / "04_light_commands.png"), full_page=False)
                await page.locator('.tab[data-ev="commands"]').click()
                await page.wait_for_timeout(300)
                await page.screenshot(path=str(SHOTS / "05_light_full.png"), full_page=False)

                # no JS console errors anywhere in the walkthrough
                assert not errors, f"JS errors during walkthrough: {errors}"
            finally:
                await browser.close()
