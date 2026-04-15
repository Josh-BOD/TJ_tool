"""Step 2 — Geo & Audience: geo selection + all toggle-gated targeting sections."""

import time
import logging
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import enable_toggle, select2_choose, safe_click

logger = logging.getLogger(__name__)

COUNTRY_MAP = {
    # Gold
    "US": "United States", "CA": "Canada", "GB": "United Kingdom",
    "UK": "United Kingdom", "AU": "Australia", "NZ": "New Zealand",
    # Silver
    "AE": "United Arab Emirates", "AT": "Austria", "BE": "Belgium",
    "BG": "Bulgaria", "CH": "Switzerland", "CR": "Costa Rica",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain",
    "HK": "Hong Kong", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland",
    "IT": "Italy", "KR": "South Korea", "LT": "Lithuania", "LV": "Latvia",
    "NL": "Netherlands", "PL": "Poland", "PR": "Puerto Rico", "PT": "Portugal",
    "RO": "Romania", "RS": "Serbia", "SA": "Saudi Arabia", "SK": "Slovakia",
    "TW": "Taiwan",
    # Bronze1
    "AD": "Andorra", "BM": "Bermuda", "CD": "Congo", "CW": "Curaçao",
    "CY": "Cyprus", "CZ": "Czechia", "FI": "Finland", "FO": "Faroe Islands",
    "GD": "Grenada", "GG": "Guernsey", "GL": "Greenland", "ID": "Indonesia",
    "IM": "Isle of Man", "JE": "Jersey", "KY": "Cayman Islands",
    "LA": "Laos", "LB": "Lebanon", "LC": "Saint Lucia", "LU": "Luxembourg",
    "MC": "Monaco", "MD": "Moldova", "MT": "Malta", "PA": "Panama",
    "SI": "Slovenia", "TH": "Thailand", "TR": "Turkey", "UA": "Ukraine",
    "UY": "Uruguay", "VE": "Venezuela", "YE": "Yemen",
    # Bronze3
    "AL": "Albania", "BA": "Bosnia and Herzegovina", "BR": "Brazil",
    "CL": "Chile", "GE": "Georgia", "GR": "Greece", "IL": "Israel",
    "SG": "Singapore", "ZA": "South Africa",
    # Other common
    "FR": "France", "JP": "Japan", "MX": "Mexico", "IN": "India",
    "SE": "Sweden", "NO": "Norway", "AR": "Argentina", "CO": "Colombia",
    "MY": "Malaysia", "PH": "Philippines", "VN": "Vietnam", "RU": "Russia",
    "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya", "PE": "Peru",
    "BB": "Barbados", "JM": "Jamaica", "TT": "Trinidad and Tobago",
    "DO": "Dominican Republic", "EC": "Ecuador", "PY": "Paraguay",
    "BO": "Bolivia", "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador",
    "NI": "Nicaragua", "CU": "Cuba", "HT": "Haiti",
}

LANGUAGE_MAP = {
    "EN": "English", "FR": "French", "DE": "German", "ES": "Spanish",
    "IT": "Italian", "PT": "Portuguese", "NL": "Dutch", "JA": "Japanese",
    "KO": "Korean", "ZH": "Chinese", "PL": "Polish", "RU": "Russian",
    "TR": "Turkish", "AR": "Arabic", "CS": "Czech", "SV": "Swedish",
    "DA": "Danish", "NO": "Norwegian", "FI": "Finnish", "HU": "Hungarian",
    "RO": "Romanian", "TH": "Thai",
}


def configure_step2(page: Page, config: V4CampaignConfig, variant: str):
    """Configure Geo & all toggle-gated targeting sections on Step 2."""
    logger.info("  [Step 2] Configuring geo & audience targeting...")

    # Wait for page to fully load after step 1 navigation
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)

    # Geo — only modify if CSV specified geos (non-default)
    if config.geo and config.geo != ["US"]:
        _add_geos(page, config.geo)
    else:
        logger.info("    Geo: inherited from template (no CSV override)")

    # OS targeting — skip for desktop/all variants, auto-derive for mobile variants
    v = variant.lower().strip()
    if v in ("desktop", "all"):
        logger.info(f"    OS targeting: skipped ({v} variant)")
    elif config.has_os_targeting:
        _configure_os_targeting(page, config)
    else:
        if v == "ios":
            _auto_os_for_variant(page, ["iOS"], config)
        elif v == "android":
            _auto_os_for_variant(page, ["Android"], config)
        elif v in ("all_mobile", "mobile"):
            _auto_os_for_variant(page, ["iOS", "Android"], config)

    # Browser targeting
    if config.has_browser_targeting:
        _configure_browser_targeting(page, config)

    # Browser language
    if config.has_browser_language:
        _configure_browser_language(page, config)

    # Postal codes
    if config.has_postal_codes:
        _configure_postal_codes(page, config)

    # ISP targeting
    if config.has_isp_targeting:
        _configure_isp(page, config)

    # IP range targeting
    if config.has_ip_targeting:
        _configure_ip_range(page, config)

    # Income / public segment
    if config.has_income_targeting:
        _configure_income(page, config)

    # Retargeting
    if config.has_retargeting:
        _configure_retargeting(page, config)

    # VR targeting
    if config.has_vr_targeting:
        _configure_vr(page, config)

    # Segment targeting
    if config.has_segment_targeting:
        _configure_segments(page, config)


# ─── Geo ──────────────────────────────────────────────────────────

def _add_geos(page: Page, geo_list: list):
    """Add all geos via select2 dropdown."""
    # Wait for the geo section to be ready
    try:
        page.wait_for_selector(
            'span[id="select2-geo_country-container"]',
            state="visible", timeout=15000,
        )
    except Exception:
        logger.warning("    Geo selector not found, waiting longer...")
        time.sleep(3)

    # Remove existing geo if present
    try:
        remove_links = page.locator('a.removeTargetedLocation')
        for i in range(remove_links.count()):
            link = remove_links.nth(0)  # always click first — they shift
            if link.is_visible(timeout=1000):
                link.click()
                time.sleep(0.5)
    except Exception:
        pass

    added = 0
    for geo in geo_list:
        country_name = COUNTRY_MAP.get(geo.upper(), geo)
        try:
            page.click('span[id="select2-geo_country-container"]')
            time.sleep(0.5)
            search = page.locator('input.select2-search__field[placeholder="Type here to search"]')
            search.fill(country_name)
            time.sleep(1)
            # Wait for results to settle and click the matching option
            option = page.locator('li.select2-results__option').filter(has_text=country_name).first
            option.click(timeout=5000)
            time.sleep(0.3)
            # Wait for Add button to be enabled, then click
            page.wait_for_selector('button#addLocation:not([disabled])', timeout=5000)
            page.click('button#addLocation')
            time.sleep(0.5)
            added += 1
        except Exception as e:
            logger.warning(f"    Could not add geo '{geo}' ({country_name}): {e}")
            # Close any open dropdown before continuing
            try:
                page.keyboard.press("Escape")
                time.sleep(0.3)
            except Exception:
                pass

    logger.info(f"    Geo: {added}/{len(geo_list)} added")


# ─── OS Targeting ─────────────────────────────────────────────────

def _enable_os_section(page: Page):
    """Enable the OS targeting section — scroll, toggle, and force-show content.

    On live campaign edit pages, the toggle may already be ON (inherited from template).
    Check the checkbox state before clicking to avoid accidentally disabling it.
    """
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_operatingSystemsTargeting");
        if (!section) return;
        section.scrollIntoView({block: "center"});
    }''')
    time.sleep(0.5)

    # Check if already enabled
    is_on = page.evaluate('''() => {
        const cb = document.querySelector("#operating_systems");
        if (cb) return cb.checked;
        // Fallback: check inside the section
        const section = document.querySelector("#campaign_operatingSystemsTargeting");
        if (section) {
            const cb2 = section.querySelector("input[type='checkbox']");
            return cb2 ? cb2.checked : false;
        }
        return false;
    }''')

    if not is_on:
        # Click the onoffswitch label to enable
        page.click('.onoffswitch-label[data-input="#operating_systems"]')
        time.sleep(1.5)
    else:
        logger.info("    OS targeting: already enabled")
        time.sleep(0.5)

    # Verify the select2 is now visible
    try:
        page.wait_for_selector(
            'span[id="select2-operating_systems_list_include-container"]',
            state="visible", timeout=5000,
        )
        logger.info("    OS targeting: section enabled")
    except Exception:
        # Force-show via JS as last resort
        page.evaluate('''() => {
            const section = document.querySelector("#campaign_operatingSystemsTargeting");
            if (section) {
                section.querySelectorAll('[style*="display: none"]').forEach(el => {
                    el.style.display = '';
                });
                const content = section.querySelector('.section-content, .toggle-content');
                if (content) content.style.display = '';
            }
        }''')
        time.sleep(1)
        logger.warning("    OS targeting: force-showed via JS")

def _auto_os_for_variant(page: Page, os_names: list, config: V4CampaignConfig):
    """Auto-derive OS targeting from variant (no explicit CSV column set)."""
    _enable_os_section(page)
    time.sleep(1)

    # Remove existing OS entries (safely)
    try:
        remove_all = page.locator('a.removeAll[data-selection="include"]')
        if remove_all.count() > 0 and remove_all.first.is_visible(timeout=2000):
            remove_all.first.click()
            time.sleep(0.5)
    except Exception:
        pass

    try:
        for _ in range(10):
            btn = page.locator('a.removeOsTarget')
            if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                btn.first.click()
                time.sleep(0.3)
            else:
                break
    except Exception:
        pass

    for os_name in os_names:
        _add_single_os(page, os_name, config)

    logger.info(f"    OS targeting (auto): {', '.join(os_names)}")


def _configure_os_targeting(page: Page, config: V4CampaignConfig):
    """Configure OS targeting from explicit CSV columns."""
    _enable_os_section(page)
    time.sleep(1)

    # Remove existing (safely — check visibility before clicking)
    try:
        remove_all = page.locator('a.removeAll[data-selection="include"]')
        if remove_all.count() > 0 and remove_all.first.is_visible(timeout=2000):
            remove_all.first.click()
            time.sleep(0.5)
    except Exception:
        pass

    try:
        for _ in range(10):
            btn = page.locator('a.removeOsTarget')
            if btn.count() > 0 and btn.first.is_visible(timeout=1000):
                btn.first.click()
                time.sleep(0.3)
            else:
                break
    except Exception:
        pass

    # Include
    if config.os_include:
        for os_name in config.os_include.split(";"):
            os_name = os_name.strip()
            if os_name:
                _add_single_os(page, os_name, config)
        logger.info(f"    OS include: {config.os_include}")

    # Exclude (uses separate selector)
    if config.os_exclude:
        for os_name in config.os_exclude.split(";"):
            os_name = os_name.strip()
            if os_name:
                _add_single_os_exclude(page, os_name)
        logger.info(f"    OS exclude: {config.os_exclude}")


def _add_single_os(page: Page, os_name: str, config: V4CampaignConfig):
    """Add a single OS to the include list with optional version constraint."""
    os_select = page.locator('span[id="select2-operating_systems_list_include-container"]')
    try:
        os_select.wait_for(state="visible", timeout=10000)
        os_select.scroll_into_view_if_needed()
        os_select.click(timeout=5000)
    except Exception:
        logger.warning("    OS select2 not visible after waiting")
        raise
    time.sleep(0.5)
    page.click(f'li.select2-results__option:has-text("{os_name}")')
    time.sleep(0.3)

    # Version constraint
    version_op = ""
    version_val = ""
    if os_name == "iOS":
        version_op = config.ios_version_op
        version_val = config.ios_version
    elif os_name == "Android":
        version_op = config.android_version_op
        version_val = config.android_version

    if version_op and version_val:
        _set_version_constraint(page, version_op, version_val)

    page.click('button.smallButton.greenButton.addOsTarget[data-selection="include"]')
    time.sleep(0.5)
    page.click('body')
    time.sleep(0.3)


def _add_single_os_exclude(page: Page, os_name: str):
    """Add a single OS to the exclude list."""
    try:
        page.click('span[id="select2-operating_systems_list_exclude-container"]')
        time.sleep(0.5)
        page.click(f'li.select2-results__option:has-text("{os_name}")')
        time.sleep(0.3)
        page.click('button.smallButton.redButton.addOsTarget[data-selection="exclude"]')
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"    Could not exclude OS {os_name}: {e}")


def _set_version_constraint(page: Page, op: str, version: str):
    """Set the version operator and version number."""
    op_label_map = {
        "newer_than": "Newer than",
        "older_than": "Older than",
        "equal": "Equal to",
    }
    label = op_label_map.get(op.lower())
    if not label:
        return

    try:
        page.click('span[id="select2-operating_system_selectors_include-container"]')
        time.sleep(0.5)
        page.click(f'li.select2-results__option:has-text("{label}")')
        time.sleep(0.5)

        page.click('span[id="select2-single_version_include-container"]')
        time.sleep(0.5)
        search = page.locator(
            'input.select2-search__field[aria-controls="select2-single_version_include-results"]'
        )
        search.type(version, delay=100)
        time.sleep(0.5)
        page.wait_for_selector('li.select2-results__option--highlighted', timeout=5000)
        page.click('li.select2-results__option--highlighted')
        time.sleep(0.3)
        logger.info(f"    Version constraint: {label} {version}")
    except Exception as e:
        logger.warning(f"    Could not set version constraint: {e}")


# ─── Browser Targeting ────────────────────────────────────────────

def _configure_browser_targeting(page: Page, config: V4CampaignConfig):
    """Enable browser targeting toggle and check individual browser checkboxes.

    The toggle checkbox is #browser_targeting (not inside a campaign_ section).
    On live edits it may already be on — check before toggling.
    """
    # Check if already enabled
    is_on = page.evaluate('''() => {
        const cb = document.getElementById("browser_targeting");
        return cb ? cb.checked : false;
    }''')

    if not is_on:
        # Try onoffswitch label first, then fallback to enable_toggle
        try:
            page.click('.onoffswitch-label[data-input="#browser_targeting"]', timeout=3000)
        except Exception:
            enable_toggle(page, "campaign_browserTargeting")
        time.sleep(1)
    else:
        logger.info("    Browser targeting: already enabled")

    # Uncheck all browsers first to start clean
    page.evaluate('''() => {
        document.querySelectorAll("input[name='browsers_list[]']:checked").forEach(cb => {
            cb.checked = false;
            cb.dispatchEvent(new Event("change", {bubbles: true}));
        });
    }''')
    time.sleep(0.3)

    # Check the specified browsers (use case-insensitive substring match)
    for browser_name in config.browsers_include:
        checked = page.evaluate('''(name) => {
            const nameLower = name.toLowerCase();
            // First try: browsers_list[] checkboxes with matching labels
            const checkboxes = document.querySelectorAll("input[name='browsers_list[]']");
            for (const cb of checkboxes) {
                const label = document.querySelector("label[for='" + cb.id + "']");
                const labelText = label ? label.textContent.trim().toLowerCase() : "";
                if (labelText === nameLower || labelText.includes(nameLower)) {
                    if (!cb.checked) {
                        cb.checked = true;
                        cb.click();
                        cb.dispatchEvent(new Event("change", {bubbles: true}));
                        return "checked: " + (label ? label.textContent.trim() : cb.id);
                    }
                    return "already: " + (label ? label.textContent.trim() : cb.id);
                }
            }
            // Second try: any label containing the browser name
            const labels = document.querySelectorAll("label");
            for (const label of labels) {
                if (label.textContent.trim().toLowerCase().includes(nameLower)) {
                    const forId = label.getAttribute("for");
                    const cb = forId ? document.getElementById(forId) : null;
                    if (cb && cb.type === "checkbox" && !cb.checked) {
                        cb.checked = true;
                        cb.click();
                        cb.dispatchEvent(new Event("change", {bubbles: true}));
                        return "checked: " + label.textContent.trim();
                    }
                    if (cb && cb.checked) return "already: " + label.textContent.trim();
                }
            }
            return "not_found";
        }''', browser_name)
        if "not_found" in checked:
            logger.warning(f"    Browser {browser_name}: not found")
        else:
            logger.info(f"    Browser {browser_name}: {checked}")

    logger.info(f"    Browsers: {', '.join(config.browsers_include)}")


# ─── Browser Language ─────────────────────────────────────────────

def _configure_browser_language(page: Page, config: V4CampaignConfig):
    """Enable browser language toggle and select the language."""
    lang_name = LANGUAGE_MAP.get(config.browser_language.upper(), config.browser_language)

    enable_toggle(page, "campaign_browserLanguageTargeting")
    time.sleep(0.5)

    section = page.locator("#campaign_browserLanguageTargeting")
    section.scroll_into_view_if_needed()

    # Remove existing languages
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_browserLanguageTargeting");
        if (!section) return;
        section.querySelectorAll(
            "a.removeBtn, a.removeBrowserLanguage, a[class*='remove'], "
            + "button[class*='remove'], .select2-selection__choice__remove"
        ).forEach(btn => btn.click());
    }''')
    time.sleep(0.5)

    # Also click visible remove buttons via Playwright
    while True:
        rm = section.locator("a[class*='remove'], .select2-selection__choice__remove").first
        if rm.count() > 0 and rm.is_visible():
            try:
                rm.click(timeout=1000)
                time.sleep(0.2)
            except Exception:
                break
        else:
            break

    # Select new language via select2
    s2 = section.locator(".select2-container").first
    s2.scroll_into_view_if_needed()
    time.sleep(0.3)
    s2.click()
    time.sleep(0.5)

    search = page.locator(".select2-container--open .select2-search__field")
    search.fill(lang_name)
    time.sleep(0.5)
    page.locator(".select2-results__option").filter(has_text=lang_name).first.click()
    time.sleep(0.3)

    if page.locator(".select2-container--open").count() > 0:
        page.keyboard.press("Escape")
        time.sleep(0.3)

    logger.info(f"    Browser language: {lang_name}")


# ─── Postal Code Targeting ───────────────────────────────────────

def _configure_postal_codes(page: Page, config: V4CampaignConfig):
    """Enable postal code toggle and fill codes."""
    enable_toggle(page, "campaign_postalCodeTargeting")
    time.sleep(0.5)

    # Set country (reuse first geo)
    if config.geo:
        try:
            select2_choose(
                page,
                'span[id="select2-postal_code_country-container"]',
                config.geo[0],
            )
        except Exception:
            pass

    # Fill postal codes textarea
    codes_text = ",".join(config.postal_codes)
    try:
        page.fill('#postal_codes', codes_text)
        time.sleep(0.3)
    except Exception as e:
        logger.warning(f"    Could not fill postal codes: {e}")

    logger.info(f"    Postal codes: {codes_text}")


# ─── ISP Targeting ────────────────────────────────────────────────

def _configure_isp(page: Page, config: V4CampaignConfig):
    """Enable ISP targeting toggle and select ISP."""
    enable_toggle(page, "campaign_ispTargeting")
    time.sleep(0.5)

    # Country
    try:
        select2_choose(
            page,
            'span[id="select2-isp_country-container"]',
            config.isp_country,
        )
    except Exception:
        pass
    time.sleep(0.5)

    # ISP name
    try:
        select2_choose(
            page,
            '#isp_name + .select2-container, span[id*="isp_name"]',
            config.isp_name,
        )
    except Exception as e:
        logger.warning(f"    Could not select ISP: {e}")

    logger.info(f"    ISP: {config.isp_country} / {config.isp_name}")


# ─── IP Range Targeting ──────────────────────────────────────────

def _configure_ip_range(page: Page, config: V4CampaignConfig):
    """Enable IP targeting toggle and fill start/end."""
    enable_toggle(page, "campaign_ipTargeting")
    time.sleep(0.5)

    try:
        page.fill('#ip_range_start', config.ip_range_start)
        page.fill('#ip_range_end', config.ip_range_end)
        time.sleep(0.3)
    except Exception as e:
        logger.warning(f"    Could not set IP range: {e}")

    logger.info(f"    IP range: {config.ip_range_start} – {config.ip_range_end}")


# ─── Income / Public Segment ─────────────────────────────────────

def _configure_income(page: Page, config: V4CampaignConfig):
    """Enable public segment toggle and select income segment."""
    enable_toggle(page, "campaign_publicSegmentTargeting")
    time.sleep(0.5)

    # Select "Income" as segment type
    try:
        page.click('#public_segment_type_income', timeout=3000)
        time.sleep(0.5)
    except Exception:
        safe_click(page, 'label:has-text("Income")')
        time.sleep(0.5)

    # Select specific income segment
    try:
        select2_choose(
            page,
            '#public_segment_income + .select2-container, span[id*="public_segment_income"]',
            config.income_segment,
        )
    except Exception as e:
        logger.warning(f"    Could not select income segment: {e}")

    logger.info(f"    Income segment: {config.income_segment}")


# ─── Retargeting ─────────────────────────────────────────────────

def _configure_retargeting(page: Page, config: V4CampaignConfig):
    """Enable retargeting toggle and configure type/mode/value.

    Two retargeting modes on TJ:
    - click/impression: Uses #retargeting_value select2 (campaign audience)
    - cookie: Uses #cookie select2 + Add button for each cookie, stores in #retargeting_list
    """
    # Scroll to and enable the retargeting toggle
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_retargeting");
        if (section) section.scrollIntoView({block: "center"});
    }''')
    time.sleep(0.5)
    enable_toggle(page, "campaign_retargeting")
    time.sleep(1)

    # Type: click, impression, or cookie
    rt_type = (config.retargeting_type or "click").lower()
    try:
        page.evaluate(f'''() => {{
            const radio = document.getElementById("retargeting_type_{rt_type}");
            if (radio) {{
                radio.checked = true;
                radio.click();
                radio.dispatchEvent(new Event("change", {{bubbles: true}}));
                // Also click the parent label for Bootstrap btn-group
                const label = radio.closest("label");
                if (label) label.click();
            }}
        }}''')
        time.sleep(1)
    except Exception:
        safe_click(page, f'label:has(#retargeting_type_{rt_type})')
        time.sleep(1)

    if rt_type == "cookie":
        _configure_cookie_retargeting(page, config)
    else:
        _configure_audience_retargeting(page, config)


def _configure_audience_retargeting(page: Page, config: V4CampaignConfig):
    """Configure click/impression audience retargeting via #retargeting_value select2."""
    # Mode: include or exclude
    if config.retargeting_mode:
        try:
            page.click(f'#retargeting_mode_{config.retargeting_mode}', timeout=3000)
        except Exception:
            safe_click(page, f'label:has-text("{config.retargeting_mode.title()}")')
        time.sleep(0.3)

    if config.retargeting_value:
        try:
            select2_choose(
                page,
                '#retargeting_value + .select2-container, span[id*="retargeting_value"]',
                config.retargeting_value,
                timeout=90000,
            )
        except Exception as e:
            logger.warning(f"    Could not select retargeting value: {e}")

    logger.info(
        f"    Retargeting: {config.retargeting_type} / "
        f"{config.retargeting_mode} / {config.retargeting_value}"
    )


def _configure_cookie_retargeting(page: Page, config: V4CampaignConfig):
    """Configure cookie/pixel retargeting.

    DOM (2026-04-14):
    - select#cookie with select2 container #select2-cookie-container
    - After selecting a cookie, fields auto-fill and Add button enables
    - button.addNewCookie — click to add each cookie to #retargeting_list
    - Repeat for each cookie in the comma-separated retargeting_value
    """
    # Parse cookie names from retargeting_value (comma or semicolon separated)
    raw = config.retargeting_value or ""
    sep = ";" if ";" in raw else ","
    cookie_names = [c.strip() for c in raw.split(sep) if c.strip()]

    if not cookie_names:
        logger.warning("    No cookie names specified in retargeting_value")
        return

    added = 0
    for cookie_name in cookie_names:
        try:
            # Click the cookie select2 container to open dropdown
            page.click('#select2-cookie-container', timeout=5000)
            time.sleep(1)

            # Type the cookie name in the search field
            search = page.locator('.select2-container--open .select2-search__field')
            search.fill(cookie_name)
            time.sleep(2)  # Wait for results to load (can be slow)

            # Click the matching option
            option = page.locator('li.select2-results__option').filter(
                has_text=cookie_name
            ).first
            try:
                option.wait_for(state="visible", timeout=10000)
                option.click()
            except Exception:
                # Try clicking first available option
                page.locator('li.select2-results__option').first.click(timeout=5000)
            time.sleep(1)

            # Click Add button (enabled after cookie selection)
            add_btn = page.locator('button.addNewCookie')
            try:
                add_btn.wait_for(state="visible", timeout=5000)
                # Remove disabled if still set
                page.evaluate('''() => {
                    const btn = document.querySelector("button.addNewCookie");
                    if (btn) btn.removeAttribute("disabled");
                }''')
                time.sleep(0.3)
                add_btn.click(force=True)
                time.sleep(1)
                added += 1
                logger.info(f"    Cookie added: {cookie_name}")
            except Exception as e:
                logger.warning(f"    Could not click Add for cookie '{cookie_name}': {e}")

        except Exception as e:
            logger.warning(f"    Could not select cookie '{cookie_name}': {e}")
            # Close any open dropdown
            try:
                page.keyboard.press("Escape")
                time.sleep(0.3)
            except Exception:
                pass

    # Verify cookies were added by checking retargeting_list
    cookie_list = page.evaluate('''() => {
        const input = document.getElementById("retargeting_list");
        return input ? input.value : "not_found";
    }''')
    logger.info(
        f"    Cookie retargeting: {added}/{len(cookie_names)} added "
        f"(retargeting_list={cookie_list})"
    )


# ─── VR Targeting ────────────────────────────────────────────────

def _configure_vr(page: Page, config: V4CampaignConfig):
    """Enable VR targeting toggle and select VR/non-VR.

    Uses onoffswitch-label click pattern — enable_toggle() targets the wrong
    element on live campaign edit pages.
    """
    is_on = page.evaluate('''() => {
        const cb = document.getElementById("virtual_reality");
        if (cb) return cb.checked;
        const section = document.getElementById("campaign_virtualReality");
        if (section) {
            const cb2 = section.querySelector("input[type='checkbox']");
            return cb2 ? cb2.checked : false;
        }
        return false;
    }''')

    if not is_on:
        try:
            page.click('.onoffswitch-label[data-input="#virtual_reality"]', timeout=3000)
        except Exception:
            enable_toggle(page, "campaign_virtualReality")
        time.sleep(1)

    if config.vr_mode.lower() == "vr":
        safe_click(page, '#virtual_realityVR')
    else:
        safe_click(page, '#virtual_realitynonVR')
    time.sleep(0.3)

    logger.info(f"    VR mode: {config.vr_mode}")


# ─── Segment Targeting ───────────────────────────────────────────

def _configure_segments(page: Page, config: V4CampaignConfig):
    """Enable segment targeting toggle and select segments via TJ modal.

    Supports multiple segments separated by semicolons:
      "Intent to buy AI;Interested in AI"
    """
    # Enable the toggle by clicking the visible onoffswitch label (not the hidden checkbox).
    # Clicking the label triggers TJ's JS that reveals the segment links and initializes
    # form bindings. Clicking the hidden checkbox directly via enable_toggle() doesn't
    # trigger the full UI initialization.
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_segmentTargeting");
        if (section) section.scrollIntoView({block: "center"});
    }''')
    time.sleep(0.5)

    # Check if already enabled
    is_on = page.evaluate('''() => {
        const section = document.querySelector("#campaign_segmentTargeting");
        if (!section) return false;
        const cb = section.querySelector("input[type='checkbox']");
        return cb ? cb.checked : false;
    }''')

    if not is_on:
        # Click the visible onoffswitch label (same pattern as OS targeting)
        try:
            page.click('.onoffswitch-label[data-input="#segment_targeting"]', timeout=5000)
        except Exception:
            # Fallback: try other label patterns
            try:
                page.click('#campaign_segmentTargeting .onoffswitch-label', timeout=3000)
            except Exception:
                # Last resort: use enable_toggle
                enable_toggle(page, "campaign_segmentTargeting")
        time.sleep(1.5)
    else:
        time.sleep(0.5)

    segments = [s.strip() for s in config.segment_targeting.split(";") if s.strip()]

    try:
        # Remove existing segments first (prevents duplicates on cloned campaigns)
        page.evaluate('''() => {
            const removeLinks = document.querySelectorAll(
                'a.removeSegment, a[data-action="removeSegment"], ' +
                '#campaign_segmentTargeting a[class*="remove"]'
            );
            removeLinks.forEach(a => a.click());
        }''')
        time.sleep(0.5)

        # Scroll to segment section and click via JS (section may be collapsed)
        clicked = page.evaluate('''() => {
            const section = document.querySelector("#campaign_segmentTargeting");
            if (section) section.scrollIntoView({behavior: "instant", block: "center"});
            const link = document.querySelector('a.openSegmentTargetingModal[data-targeting-segment-type="included"]');
            if (link) { link.click(); return true; }
            return false;
        }''')
        if not clicked:
            logger.warning("    Select segment link not found via JS")
            return
        time.sleep(2)

        # Wait for modal to fully load (not just "Loading...")
        for _ in range(15):
            loading = page.evaluate('''() => {
                const modals = document.querySelectorAll('[class*="modal"]');
                for (const m of modals) {
                    if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                }
                return false;
            }''')
            if not loading:
                break
            time.sleep(1)
        time.sleep(1)

        search_input = page.locator('input[placeholder*="VOD"], input[placeholder*="Try"]').first

        for segment_name in segments:
            search_input.fill("")
            search_input.fill(segment_name)
            time.sleep(1)

            # Wait for search results to load
            for _ in range(10):
                loading = page.evaluate('''() => {
                    const modals = document.querySelectorAll('[class*="modal"]');
                    for (const m of modals) {
                        if (m.offsetHeight > 0 && m.innerText.includes("Loading")) return true;
                    }
                    return false;
                }''')
                if not loading:
                    break
                time.sleep(1)
            time.sleep(0.5)

            # Click checkbox via JS (find item containing the segment name text)
            checked = page.evaluate('''(name) => {
                const items = document.querySelectorAll('label, li, [class*="segment"], [class*="Segment"]');
                for (const item of items) {
                    if (item.textContent.includes(name)) {
                        const cb = item.querySelector('input[type="checkbox"]');
                        if (cb && !cb.checked) {
                            cb.click();
                            cb.dispatchEvent(new Event("change", {bubbles: true}));
                            return "checked";
                        }
                        if (cb && cb.checked) return "already checked";
                    }
                }
                return "not found";
            }''', segment_name)

            if "checked" in checked:
                logger.info(f"    ✓ Segment: {segment_name}")
            else:
                logger.warning(f"    Segment '{segment_name}': {checked}")

        # Click "Include Segment" button
        page.evaluate('''() => {
            const buttons = document.querySelectorAll('button');
            for (const b of buttons) {
                if (b.textContent.includes("Include Segment") && b.offsetHeight > 0) {
                    b.click();
                    return true;
                }
            }
            return false;
        }''')
        time.sleep(1)

        logger.info(f"    Segment targeting: {len(segments)} segment(s) configured")
    except Exception as e:
        logger.warning(f"    Could not set segment targeting: {e}")
