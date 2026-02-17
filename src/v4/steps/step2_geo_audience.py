"""Step 2 — Geo & Audience: geo selection + all toggle-gated targeting sections."""

import time
import logging
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import enable_toggle, select2_choose, safe_click

logger = logging.getLogger(__name__)

COUNTRY_MAP = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom",
    "UK": "United Kingdom", "DE": "Germany", "FR": "France",
    "ES": "Spain", "IT": "Italy", "NL": "Netherlands",
    "AU": "Australia", "BR": "Brazil", "JP": "Japan", "MX": "Mexico",
    "IN": "India", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "FI": "Finland", "PL": "Poland", "CZ": "Czechia",
    "AT": "Austria", "CH": "Switzerland", "BE": "Belgium", "IE": "Ireland",
    "NZ": "New Zealand", "AR": "Argentina", "CO": "Colombia", "CL": "Chile",
    "PT": "Portugal", "RO": "Romania", "HU": "Hungary", "GR": "Greece",
    "ZA": "South Africa", "SG": "Singapore", "MY": "Malaysia", "PH": "Philippines",
    "TH": "Thailand", "ID": "Indonesia", "VN": "Vietnam", "KR": "South Korea",
    "TW": "Taiwan", "HK": "Hong Kong", "TR": "Turkey", "RU": "Russia",
    "UA": "Ukraine", "IL": "Israel", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya", "PE": "Peru",
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

    # Geo
    _add_geos(page, config.geo)

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

def _auto_os_for_variant(page: Page, os_names: list, config: V4CampaignConfig):
    """Auto-derive OS targeting from variant (no explicit CSV column set)."""
    page.evaluate('''() => {
        const section = document.querySelector("#campaign_operatingSystemsTargeting");
        if (section) section.scrollIntoView({block: "center"});
    }''')
    time.sleep(0.5)
    enable_toggle(page, "campaign_operatingSystemsTargeting")
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
    # Scroll to OS section and enable toggle
    toggled = page.evaluate('''() => {
        const section = document.querySelector("#campaign_operatingSystemsTargeting");
        if (!section) return "section_not_found";
        section.scrollIntoView({block: "center"});
        const cb = section.querySelector("input[type='checkbox']");
        if (!cb) return "checkbox_not_found";
        if (!cb.checked) {
            cb.click();
            cb.dispatchEvent(new Event("change", {bubbles: true}));
        }
        return cb.checked ? "enabled" : "failed";
    }''')
    logger.info(f"    OS toggle: {toggled}")
    time.sleep(1.5)

    # If the section-based toggle didn't work, try clicking the checkbox directly by ID
    if toggled != "enabled":
        page.evaluate('''() => {
            // Try alternative checkbox selectors
            const candidates = [
                document.getElementById("operating_systems"),
                document.querySelector("input[name='operating_systems']"),
                document.querySelector("#campaign_operatingSystemsTargeting input.toggleCheckbox"),
                document.querySelector("label[for*='operatingSystem'] input"),
            ];
            for (const cb of candidates) {
                if (cb && !cb.checked) {
                    cb.click();
                    cb.dispatchEvent(new Event("change", {bubbles: true}));
                    break;
                }
            }
        }''')
        time.sleep(1.5)

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
    # Try normal click first, fallback to force click
    os_select = page.locator('span[id="select2-operating_systems_list_include-container"]')
    try:
        os_select.scroll_into_view_if_needed()
        os_select.click(timeout=5000)
    except Exception:
        logger.info("    OS select2 not visible, trying force click...")
        os_select.click(force=True, timeout=5000)
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
    """Enable browser targeting toggle and check individual browser checkboxes."""
    enable_toggle(page, "campaign_browserTargeting")
    time.sleep(0.5)

    for browser_name in config.browsers_include:
        try:
            # Try clicking the checkbox label for this browser
            label = page.locator(f'label:has-text("{browser_name}")').first
            if label.count() > 0:
                label.click()
                time.sleep(0.2)
        except Exception as e:
            logger.warning(f"    Could not select browser {browser_name}: {e}")

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
    """Enable retargeting toggle and configure type/mode/value."""
    enable_toggle(page, "campaign_retargeting")
    time.sleep(0.5)

    # Type: click or impression
    if config.retargeting_type:
        try:
            page.click(f'#retargeting_type_{config.retargeting_type}', timeout=3000)
        except Exception:
            safe_click(page, f'label:has-text("{config.retargeting_type.title()}")')
        time.sleep(0.3)

    # Mode: include or exclude
    if config.retargeting_mode:
        try:
            page.click(f'#retargeting_mode_{config.retargeting_mode}', timeout=3000)
        except Exception:
            safe_click(page, f'label:has-text("{config.retargeting_mode.title()}")')
        time.sleep(0.3)

    # Value: audience/pixel name
    if config.retargeting_value:
        try:
            select2_choose(
                page,
                '#retargeting_value + .select2-container, span[id*="retargeting_value"]',
                config.retargeting_value,
            )
        except Exception as e:
            logger.warning(f"    Could not select retargeting value: {e}")

    logger.info(
        f"    Retargeting: {config.retargeting_type} / "
        f"{config.retargeting_mode} / {config.retargeting_value}"
    )


# ─── VR Targeting ────────────────────────────────────────────────

def _configure_vr(page: Page, config: V4CampaignConfig):
    """Enable VR targeting toggle and select VR/non-VR."""
    enable_toggle(page, "campaign_virtualReality")
    time.sleep(0.5)

    if config.vr_mode.lower() == "vr":
        safe_click(page, '#virtual_realityVR')
    else:
        safe_click(page, '#virtual_realitynonVR')
    time.sleep(0.3)

    logger.info(f"    VR mode: {config.vr_mode}")


# ─── Segment Targeting ───────────────────────────────────────────

def _configure_segments(page: Page, config: V4CampaignConfig):
    """Enable segment targeting toggle and select segment."""
    enable_toggle(page, "campaign_segmentTargeting")
    time.sleep(0.5)

    try:
        select2_choose(
            page,
            '#segments + .select2-container, span[id*="segments"]',
            config.segment_targeting,
        )
    except Exception as e:
        logger.warning(f"    Could not select segment: {e}")

    logger.info(f"    Segment: {config.segment_targeting}")
