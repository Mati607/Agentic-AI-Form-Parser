import asyncio
import subprocess
from playwright.async_api import async_playwright, Page, Browser

from app.config import (
    FORM_URL,
    CHROME_CDP_URL,
    CHROME_CDP_PORT,
    CHROME_CDP_PROFILE_DIR,
)

FIELD_MAPPINGS = [
    # Part 1 - Attorney
    ("attorney", "online_account_number", ["Online Account Number", "1. Online Account Number"]),
    ("attorney", "family_name", ["2.a. Family Name", "Family Name (Last Name)"]),
    ("attorney", "given_name", ["2.b. Given Name", "Given Name (First Name)"]),
    ("attorney", "middle_name", ["2.c. Middle Name", "Middle Name"]),
    ("attorney", "street_number_and_name", ["3.a. Street Number and Name", "Street Number and Name"]),
    ("attorney", "apt_ste_flr", ["Apt. Ste. Flr.", "Apt"]),
    ("attorney", "city", ["3.c. City", "City"]),
    ("attorney", "state", ["3.d. State", "State"]),
    ("attorney", "zip_code", ["3.e. ZIP Code", "ZIP Code"]),
    ("attorney", "country", ["3.f. Country", "Country"]),
    ("attorney", "daytime_telephone", ["4. Daytime Telephone Number", "Daytime Telephone"]),
    ("attorney", "mobile_telephone", ["5. Mobile Telephone Number", "Mobile Telephone"]),
    ("attorney", "email", ["6. Email Address", "Email Address"]),
    ("attorney", "licensing_authority", ["Licensing Authority"]),
    ("attorney", "bar_number", ["1.b. Bar Number", "Bar Number"]),
    ("attorney", "law_firm_or_organization", ["1.d. Name of Law Firm or Organization", "Law Firm"]),
    # Part 3 - Passport (beneficiary)
    ("passport", "last_name", ["1.a. Last Name", "Last Name"]),
    ("passport", "first_name", ["1.b. First Name(s)", "First Name"]),
    ("passport", "middle_name", ["1.c. Middle Name(s)", "Middle Name(s)"]),
    ("passport", "passport_number", ["2. Passport Number", "Passport Number"]),
    ("passport", "country_of_issue", ["3. Country of Issue", "Country of Issue"]),
    ("passport", "nationality", ["4. Nationality", "Nationality"]),
    ("passport", "date_of_birth", ["5.a. Date of Birth", "Date of Birth"]),
    ("passport", "place_of_birth", ["5.b. Place of Birth", "Place of Birth"]),
    ("passport", "sex", ["6. Sex", "Sex"]),
    ("passport", "date_of_issue", ["7.a. Date of Issue", "Date of Issue"]),
    ("passport", "date_of_expiration", ["7.b. Date of Expiration", "Date of Expiration"]),
]


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
                value = (extracted.get(section) or {}).get(key)
                if value is None:
                    value = (extracted.get(section) or {}).get(key.replace("_", " ").title())
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
