"""Step 5 — Ad Settings: delete inherited ads, upload CSV, set rotation."""

import csv
import tempfile
import time
import logging
from pathlib import Path
from playwright.sync_api import Page

from ..models import V4CampaignConfig
from ..utils import dismiss_modals

logger = logging.getLogger(__name__)

# Minimum required columns per format (must be non-empty)
REQUIRED_BY_FORMAT = {
    "native": {"Ad Name", "Target URL", "Video Creative ID", "Thumbnail Creative ID", "Headline", "Brand Name"},
    "preroll": {"Ad Name", "Target URL", "Creative ID"},
    "default": {"Ad Name", "Target URL"},
}


def configure_step5(page: Page, config: V4CampaignConfig, csv_dir: str, campaign_name: str):
    """Delete existing ads, upload ad CSV, and configure ad rotation."""
    logger.info("  [Step 5] Configuring ad settings...")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(2)
    dismiss_modals(page)

    is_pop = config.ad_format_type == "pop"

    if config.csv_file:
        # 1. Validate and clean the ad CSV before anything else
        csv_path = Path(csv_dir) / config.csv_file
        if csv_path.exists():
            csv_path = _validate_and_clean_csv(csv_path)

        # 2. Delete existing ads
        _delete_all_ads(page)

        # 3. Upload ad CSV
        upload_ok = False
        if csv_path.exists():
            if is_pop:
                _upload_pop_csv(page, csv_path)
                upload_ok = True  # Pop uploads don't have structured error detection
            else:
                upload_ok = _upload_ad_csv(page, csv_path, campaign_name, config)
        else:
            logger.warning(f"    Ad CSV not found: {csv_path}")

        # 4. Check for upload errors before proceeding
        if not upload_ok:
            upload_errors = _check_upload_errors(page)
            if upload_errors:
                logger.error(f"    CSV upload errors detected — aborting finish: {upload_errors}")
                return
            logger.warning("    CSV upload returned non-success but no visible errors — attempting finish")

        # 5. Configure ad rotation to Autopilot (CTR) — must be after ads exist
        if not is_pop:
            _configure_ad_rotation(page)
    else:
        logger.info("    No csv_file — keeping template ads or leaving as draft")

    # 6. Try to finish campaign. If it fails (e.g. no ads), leave as draft —
    #    fields are already saved from steps 1-4
    _finish_campaign(page)


def _validate_and_clean_csv(csv_path: Path) -> Path:
    """Validate an ad CSV and write a cleaned version if problems are found.

    Handles:
    - Rows concatenated without newlines (missing newline glues next row onto
      the end of the current row's Brand Name field)
    - Rows missing required fields (Thumbnail ID, Headline, Brand Name)
    - Extra trailing commas creating phantom columns

    Returns the path to the cleaned CSV (temp file if modified, original if clean).
    """
    try:
        raw = csv_path.read_text(encoding="utf-8-sig")
    except Exception as e:
        logger.error(f"    Cannot read CSV {csv_path}: {e}")
        return csv_path

    # Pre-process: fix concatenated rows before CSV parsing.
    # Pattern: the last field (Brand Name) is quoted, and the next row's Ad Name
    # is glued right after the closing quote with no newline.
    # e.g.: ..."Dream, Build, Fuck Her"EN_General_Dogo_25sec_ID-80EB1C4B,https://clk...
    # Fix: insert a newline when a closing quote is immediately followed by text
    # that contains a URL (confirming it's a new ad row, not just a normal CSV field).
    import re
    # Match: closing quote + text + comma + https:// on same stretch (no newline between)
    # This only fires when a new URL-bearing row is concatenated.
    raw = re.sub(r'"([A-Z][A-Za-z0-9_-]+,https?://)', r'"\n\1', raw)

    lines = raw.split("\n")
    if len(lines) < 2:
        logger.warning(f"    CSV has no data rows: {csv_path.name}")
        return csv_path

    header = lines[0].strip()
    header_cols = [c.strip() for c in next(csv.reader([header]))]
    expected_count = len(header_cols)

    # Detect format from header to pick the right required fields
    if "Thumbnail Creative ID" in header_cols:
        required = REQUIRED_BY_FORMAT["native"]
    elif "Creative ID" in header_cols and expected_count >= 10:
        required = REQUIRED_BY_FORMAT["preroll"]
    else:
        required = REQUIRED_BY_FORMAT["default"]

    cleaned_rows = []
    dropped = []

    for i, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue

        try:
            cols = next(csv.reader([line]))
        except Exception:
            dropped.append(f"row {i}: CSV parse error: {line[:60]}")
            continue

        # Strip trailing empty columns beyond expected count
        while len(cols) > expected_count and not cols[-1].strip():
            cols.pop()

        if len(cols) < expected_count:
            # Pad with empty strings for optional trailing columns
            cols.extend([""] * (expected_count - len(cols)))

        if len(cols) > expected_count:
            cols = cols[:expected_count]

        # Check required fields are non-empty
        row_ok = True
        for req_col in required:
            if req_col in header_cols:
                idx = header_cols.index(req_col)
                if idx < len(cols) and not cols[idx].strip():
                    dropped.append(f"row {i}: empty {req_col}: {cols[0][:50]}")
                    row_ok = False
                    break

        if row_ok:
            cleaned_rows.append(cols)

    if dropped:
        logger.warning(f"    CSV validation dropped {len(dropped)} rows from {csv_path.name}:")
        for d in dropped:
            logger.warning(f"      {d}")

        # Write cleaned CSV to temp file
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(header_cols)
        writer.writerows(cleaned_rows)

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=f"_{csv_path.stem}_clean.csv",
            delete=False, encoding="utf-8",
        )
        tmp.write(buf.getvalue())
        tmp.close()
        logger.info(f"    Cleaned CSV: {len(cleaned_rows)} valid rows → {tmp.name}")
        return Path(tmp.name)

    logger.info(f"    CSV validated OK: {len(cleaned_rows)} rows in {csv_path.name}")
    return csv_path


def _upload_pop_csv(page: Page, csv_path: Path):
    """Upload a pop ad CSV using TJ mass create with CSV flow.

    Pop ad page has:
    - Radio: Manual selection / Mass create with CSV
    - File input for CSV upload
    - Submit button to create ads
    CSV format: "Ad Name","Source URL"
    """
    try:
        dismiss_modals(page)
        time.sleep(1)

        # Select "Mass create with CSV" radio
        clicked = page.evaluate("""() => {
            const labels = document.querySelectorAll('label');
            for (const label of labels) {
                if (label.textContent.toLowerCase().includes('mass create') ||
                    label.textContent.toLowerCase().includes('csv')) {
                    const radio = label.querySelector('input[type="radio"]') ||
                                  document.getElementById(label.getAttribute('for'));
                    if (radio) radio.click();
                    else label.click();
                    return true;
                }
            }
            const radios = document.querySelectorAll('input[type="radio"]');
            for (const r of radios) {
                const lbl = document.querySelector('label[for="' + r.id + '"]');
                if (lbl && lbl.textContent.toLowerCase().includes('csv')) {
                    r.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            time.sleep(1)
            logger.info("    Pop: selected mass CSV upload")

        # Upload the CSV file
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(csv_path))
        time.sleep(2)
        logger.info(f"    Pop: CSV file set: {csv_path.name}")

        # Step 1: Click "Create CSV Preview" button
        page.evaluate("""() => {
            const buttons = document.querySelectorAll('button, a.smallButton');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create csv preview') || text.includes('preview')) {
                    btn.scrollIntoView({behavior: "instant", block: "center"});
                    btn.click();
                    return text;
                }
            }
            // Fallback: click any button with "create" in text
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create')) {
                    btn.scrollIntoView({behavior: "instant", block: "center"});
                    btn.click();
                    return text;
                }
            }
            return null;
        }""")
        time.sleep(3)
        logger.info("    Pop: clicked Create CSV Preview")

        # Step 2: Handle the csvPreviewModal — click "Create Ad(s)" inside it
        confirmed = page.evaluate("""() => {
            const modal = document.querySelector('#csvPreviewModal');
            if (!modal) return 'no_modal';
            // Find confirm/create button inside modal
            const buttons = modal.querySelectorAll('button, a');
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('create ad') || text.includes('confirm')) {
                    btn.click();
                    return 'confirmed: ' + btn.textContent.trim();
                }
            }
            // Fallback: click green button in modal
            for (const btn of buttons) {
                if (btn.classList.contains('greenButton') || btn.classList.contains('btn-success') || btn.classList.contains('confirmAds')) {
                    btn.click();
                    return 'green: ' + btn.textContent.trim();
                }
            }
            return 'no_button_in_modal';
        }""")
        logger.info(f"    Pop: preview modal result: {confirmed}")

        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(2)

        # Dismiss any remaining modals
        page.evaluate("""() => {
            document.querySelectorAll('.modal.show .close, .modal.show [data-dismiss="modal"]').forEach(el => el.click());
        }""")
        time.sleep(1)

        logger.info("    Pop: CSV upload complete")

    except Exception as e:
        logger.error(f"    Pop CSV upload failed: {e}")


def _delete_all_ads(page: Page):
    """Delete all existing ads on the ads page."""
    dismiss_modals(page)
    try:
        length_dropdown = page.query_selector('select[name="adsTable_length"]')
        if length_dropdown:
            page.select_option('select[name="adsTable_length"]', '100')
            time.sleep(1)

        select_all = page.query_selector(
            'input[type="checkbox"].checkUncheckAll[data-table="adsTable"]'
        )
        if not select_all:
            logger.info("    No ads to delete")
            return

        select_all.click()
        time.sleep(0.5)

        delete_btn = page.query_selector(
            'button.massDeleteButton.redButton.smallButton'
        )
        if delete_btn and delete_btn.is_visible():
            delete_btn.click()
            time.sleep(0.5)

            try:
                yes_btn = page.query_selector(
                    'a[data-function="adsManagement.deleteAds"].smallButton.greenButton'
                )
                if yes_btn:
                    yes_btn.click()
                else:
                    page.click('button:has-text("Yes")', timeout=2000)
                time.sleep(2)
            except Exception:
                pass

            logger.info("    Deleted existing ads")

    except Exception as e:
        logger.debug(f"    Ad deletion: {e}")


def _configure_ad_rotation(page: Page):
    """Set ad rotation to Autopilot (CTR).

    Must dismiss #reviewYourBidsModal first — it appears after page reload
    on Step 5 and blocks all clicks.
    """
    dismiss_modals(page)
    time.sleep(0.5)

    # Handle reviewYourBidsModal — appears when bids are below min CPM.
    # Click "Manually Adjust Bids" to dismiss it (TJ auto-floors bids at min).
    page.evaluate('''() => {
        const modal = document.getElementById("reviewYourBidsModal");
        if (modal && (modal.classList.contains("show") || modal.classList.contains("in"))) {
            const adjustBtn = document.getElementById("adjustBids");
            if (adjustBtn) { adjustBtn.click(); return; }
            // Fallback: force-hide
            modal.style.display = "none";
            modal.classList.remove("show", "in");
            modal.setAttribute("aria-hidden", "true");
        }
        document.querySelectorAll(".modal-backdrop").forEach(el => el.remove());
        document.body.classList.remove("modal-open");
        document.body.style.overflow = "";
    }''')
    time.sleep(0.5)

    try:
        page.get_by_text("Autopilot", exact=True).click(timeout=5000)
        time.sleep(0.3)
        page.get_by_text("CTR", exact=True).click(timeout=5000)
        time.sleep(0.3)
        logger.info("    Ad rotation: Autopilot (CTR)")
    except Exception as e:
        logger.warning(f"    Could not set ad rotation: {e}")


def _finish_campaign(page: Page):
    """Click Finish Campaign on Step 5, then handle success modal.

    DOM inspection (2026-04-14) confirmed the button is:
        <a class="smallButton greenButton saveContinue mr-2"
           data-gtm-index="saveContinueStepFive">Finish Campaign</a>

    Despite the `saveContinue` class name, this IS the finish/publish button.
    There's also a `button#saveChanges` ("Save Changes") which only saves the draft.
    """
    dismiss_modals(page)
    time.sleep(1)

    url_before = page.url

    for attempt in range(3):
        # Remove overlays, dismiss reviewYourBidsModal, unhide save button
        page.evaluate("""() => {
            // Dismiss reviewYourBidsModal if showing (bids below min CPM warning)
            const bidsModal = document.getElementById('reviewYourBidsModal');
            if (bidsModal && (bidsModal.classList.contains('show') || bidsModal.classList.contains('in'))) {
                const adjustBtn = document.getElementById('adjustBids');
                if (adjustBtn) adjustBtn.click();
                else {
                    bidsModal.style.display = 'none';
                    bidsModal.classList.remove('show', 'in');
                }
            }
            document.querySelectorAll('.disabledInterface').forEach(el => el.classList.remove('disabledInterface'));
            document.querySelectorAll('.saveButtonContainer').forEach(el => {
                el.classList.remove('d-none');
                el.style.display = '';
                el.style.visibility = 'visible';
            });
            // Force-show all save buttons and scroll to them
            document.querySelectorAll('a.saveContinue, button#saveChanges').forEach(el => {
                el.style.display = '';
                el.style.visibility = 'visible';
                el.style.pointerEvents = 'auto';
            });
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        }""")
        time.sleep(0.5)

        logger.info(f"    [Finish] Clicking Finish Campaign (attempt {attempt+1})")

        # Click the confirmed "Finish Campaign" link
        clicked = page.evaluate("""() => {
            // Primary: the exact Finish Campaign link
            const finish = document.querySelector('a.saveContinue[data-gtm-index="saveContinueStepFive"]');
            if (finish) {
                finish.style.display = '';
                finish.style.visibility = 'visible';
                finish.style.pointerEvents = 'auto';
                finish.scrollIntoView({behavior: "instant", block: "center"});
                finish.click();
                return "finishCampaign";
            }
            // Fallback: any a.saveContinue
            const fallback = document.querySelector('a.saveContinue');
            if (fallback) {
                fallback.style.display = '';
                fallback.style.visibility = 'visible';
                fallback.style.pointerEvents = 'auto';
                fallback.click();
                return "saveContinue_fallback";
            }
            // Last resort: Save Changes button (saves draft only)
            const save = document.getElementById('saveChanges');
            if (save) { save.click(); return "saveChanges_only"; }
            return null;
        }""")

        if not clicked:
            logger.warning("    [Finish] No finish/save button found")
            time.sleep(2)
            continue

        logger.info(f"    [Finish] Clicked: {clicked}")
        time.sleep(3)

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        time.sleep(2)

        # Check for success modal ("Go to Campaigns" link)
        go_link = page.locator('a.smallButton.greenButton:has-text("Go to Campaigns")')
        try:
            go_link.first.wait_for(state="visible", timeout=10000)
            # Capture modal content — look for live campaign ID in any link/text
            try:
                modal_info = page.evaluate("""() => {
                    const modals = document.querySelectorAll('.modal.show, .modal.in, .modal[style*="display: block"]');
                    for (const m of modals) {
                        const links = m.querySelectorAll('a');
                        const hrefs = Array.from(links).map(a => a.href).filter(h => h);
                        const text = m.textContent.trim().substring(0, 200);
                        // Look for campaign ID pattern in any link
                        for (const h of hrefs) {
                            const match = h.match(/campaign\\/(\\d{10,})/);
                            if (match) return {live_id: match[1], hrefs: hrefs};
                        }
                        return {live_id: null, hrefs: hrefs, text: text};
                    }
                    return {live_id: null};
                }""")
                if modal_info.get("live_id"):
                    logger.info(f"    [Finish] Live ID from modal: {modal_info['live_id']}")
                else:
                    logger.info(f"    [Finish] Modal links: {modal_info.get('hrefs', [])}")
            except Exception:
                pass
            logger.info("    [Finish] Success modal — clicking Go to Campaigns")
            go_link.first.click(timeout=5000)
            time.sleep(2)
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except Exception:
                # Navigation may destroy context — that's fine, it means success
                logger.info("    Campaign finished (navigation in progress)")
                return
            if page.url != url_before and "ad-settings" not in page.url:
                logger.info(f"    Campaign finished — navigated to: {page.url}")
                return
        except Exception:
            pass

        if page.url != url_before and "ad-settings" not in page.url:
            logger.info(f"    Campaign finished — navigated to: {page.url}")
            return

        # Check for validation errors (may fail if page navigated)
        try:
            errors = page.evaluate("""() => {
                const msgs = [];
                document.querySelectorAll('.alert-danger, .error-message, .text-danger, .validation-error').forEach(el => {
                    if (el.offsetHeight > 0) msgs.push(el.textContent.trim().substring(0, 100));
                });
                document.querySelectorAll('.modal.show').forEach(m => {
                    const text = m.textContent.trim();
                    if (text.includes('error') || text.includes('Error') || text.includes('required')) {
                        msgs.push(text.substring(0, 100));
                    }
                });
                return msgs;
            }""")
            if errors:
                logger.warning(f"    [Finish] Validation errors: {errors}")
            else:
                logger.info(f"    [Finish] Still on: {page.url}")
        except Exception:
            # Context destroyed = navigation happened = likely success
            logger.info("    [Finish] Page navigated (context destroyed) — likely success")
            return

        try:
            page.screenshot(path=f"screenshots/step5_finish_fail_attempt{attempt+1}.png")
        except Exception:
            pass

        if attempt < 2:
            time.sleep(2)

    if "ad-settings" in page.url:
        logger.warning(f"    Could not finish campaign — still on {page.url}")


def _check_upload_errors(page: Page) -> list:
    """Check the ad settings page for CSV upload error messages.

    Returns a list of error strings, or empty list if no errors found.
    """
    try:
        errors = page.evaluate('''() => {
            const msgs = [];
            // TJ error containers
            const selectors = [
                '.alert-danger',
                '.error-message',
                '.text-danger',
                '.validation-error',
                '.upload-error',
                '.csv-error',
                '.errorMsg',
                '#uploadError',
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    if (el.offsetHeight > 0) {
                        const text = el.textContent.trim();
                        if (text) msgs.push(text.substring(0, 200));
                    }
                });
            }
            // Check for any visible modal with error content
            document.querySelectorAll('.modal.show, .modal.in, .modal[style*="display: block"]').forEach(m => {
                const text = (m.textContent || '').trim().toLowerCase();
                if (text.includes('error') || text.includes('failed') || text.includes('invalid')) {
                    msgs.push('Modal error: ' + m.textContent.trim().substring(0, 200));
                }
            });
            // Check for empty ads table (upload succeeded but created 0 ads)
            const adsTable = document.querySelector('#adsTable tbody');
            if (adsTable && adsTable.querySelectorAll('tr').length === 0) {
                msgs.push('Ads table is empty — upload may have created 0 ads');
            }
            return msgs;
        }''')
        return errors or []
    except Exception:
        return []


def _upload_ad_csv(page: Page, csv_path: Path, campaign_name: str, config: V4CampaignConfig) -> bool:
    """Upload ad CSV using NativeUploader or TJUploader. Returns True on success."""
    use_native = (config.format_type == "native")

    try:
        if use_native:
            from native_uploader import NativeUploader
            uploader = NativeUploader(dry_run=False)
        else:
            from uploader import TJUploader
            uploader = TJUploader(dry_run=False)

        result = uploader.upload_to_campaign(
            page=page,
            campaign_id="current",
            csv_path=csv_path,
            campaign_name=campaign_name,
            skip_navigation=True,
        )

        if result.get("status") == "success":
            ads_created = result.get("ads_created", 0)
            logger.info(f"    CSV uploaded: {ads_created} ads created")
            return ads_created > 0
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"    CSV upload failed: {error}")
            return False

    except ImportError as e:
        logger.warning(f"    Uploader not available ({e}) — skipping CSV upload")
        return False
    except Exception as e:
        logger.error(f"    CSV upload failed: {e}")
        return False
