import asyncio
import subprocess
from playwright.async_api import async_playwright, Page, Browser

from app.config import (
    FORM_URL,
    CHROME_CDP_URL,
    CHROME_CDP_PORT,
    CHROME_CDP_PROFILE_DIR,
)
from app.field_mappings import FIELD_MAPPINGS, get_mapped_value


async def _fill_field(page: Page, value: str, labels: list[str], select_if_select: bool = True) -> bool:
    if not value or not str(value).strip():
        return False
    value = str(value).strip()
    for label in labels:
        try:
            loc = page.get_by_label(label, exact=False)
            if await loc.count() > 0:
                first = loc.first
                tag = await first.evaluate("el => el.tagName")
                if tag.upper() == "SELECT" and select_if_select:
                    try:
                        await first.select_option(label=value)
                    except Exception:
                        await first.select_option(value=value)
                else:
                    await first.fill(value)
                return True
        except Exception:
            pass
        try:
            loc = page.get_by_placeholder(label)
            if await loc.count() > 0:
                await loc.first.fill(value)
                return True
        except Exception:
            pass
        try:
            loc = page.locator(f'input[name*="{label[:20]}"], textarea[name*="{label[:20]}"]')
            if await loc.count() > 0:
                await loc.first.fill(value)
                return True
        except Exception:
            pass
    return False


async def fill_form(extracted: dict, form_url: str | None = None) -> dict:
    url = form_url or FORM_URL
    filled: list[str] = []
    errors: list[str] = []
    browser: Browser | None = None
    connected_over_cdp = False
    opened_in_existing_browser = False

    try:
        async with async_playwright() as p:
            if CHROME_CDP_URL:
                try:
                    browser = await p.chromium.connect_over_cdp(CHROME_CDP_URL)
                    connected_over_cdp = True
                except Exception as e:
                    errors.append(f"CDP connect failed ({CHROME_CDP_URL}): {e}. Retrying after auto-start.")
                    try:
                        subprocess.Popen(
                            [
                                "/usr/bin/open",
                                "-na",
                                "Google Chrome",
                                "--args",
                                f"--remote-debugging-port={CHROME_CDP_PORT}",
                                f"--user-data-dir={CHROME_CDP_PROFILE_DIR}",
                                "--no-first-run",
                                "--no-default-browser-check",
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        await asyncio.sleep(2.0)
                        browser = await p.chromium.connect_over_cdp(CHROME_CDP_URL)
                        connected_over_cdp = True
                    except Exception as e2:
                        errors.append(
                            f"Auto-start CDP failed: {e2}. "
                            f"Run Chrome manually with --remote-debugging-port={CHROME_CDP_PORT}."
                        )

            if connected_over_cdp and browser:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
                opened_in_existing_browser = True
            else:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

            await page.goto(url, wait_until="networkidle", timeout=30000)

            for section, key, labels in FIELD_MAPPINGS:
                value = get_mapped_value(extracted, section, key)
                if not value:
                    continue
                try:
                    if await _fill_field(page, str(value), labels):
                        filled.append(f"{section}.{key}")
                except Exception as e:
                    errors.append(f"{section}.{key}: {e}")

            await asyncio.sleep(0.3)
    except Exception as e:
        errors.append(f"Browser/form: {e}")
    finally:
        if browser and not connected_over_cdp:
            await browser.close()

    return {
        "filled": filled,
        "errors": errors,
        "url": url,
        "opened_in_existing_browser": opened_in_existing_browser,
    }
