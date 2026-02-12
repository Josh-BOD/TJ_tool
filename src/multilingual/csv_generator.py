"""
Multilingual CSV generator.

Reads a languages CSV + base ads CSV, and generates:
1. Per-language ad CSVs with translated copy and sub14 tracking
2. A campaign creation CSV consumable by create_campaigns_v2_sync.py

The languages CSV has a `lang_code` column that is comma-separated:
- "es,en" = create Spanish + English campaigns for that geo
- "es"    = create Spanish only
- "en"    = create English only (no translation, no sub14)
"""

import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from .translator import Translator

logger = logging.getLogger(__name__)

# Translatable columns by ad format
TRANSLATABLE_COLUMNS = {
    "NATIVE": ["Headline", "Brand Name"],
    "INSTREAM": ["Custom CTA Text", "Banner CTA Title", "Banner CTA Subtitle"],
}

# Max character lengths for TJ fields (enforced after translation)
COLUMN_MAX_LENGTHS = {
    "Brand Name": 25,
    "Headline": 87,
    "Custom CTA Text": 25,
    "Banner CTA Title": 25,
    "Banner CTA Subtitle": 30,
}

# Columns containing URLs that need sub14 appended
URL_COLUMNS = {
    "NATIVE": ["Target URL"],
    "INSTREAM": ["Target URL", "Custom CTA URL", "Banner CTA URL"],
}

# Built-in language code -> name mapping for translation
LANG_NAMES = {
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "pl": "Polish",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ru": "Russian",
    "tr": "Turkish",
    "ar": "Arabic",
    "cs": "Czech",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "hu": "Hungarian",
    "ro": "Romanian",
    "th": "Thai",
}


class MultilingualCSVGenerator:
    """Generates multilingual ad CSVs and campaign creation CSVs."""

    def __init__(
        self,
        translator: Optional[Translator],
        ad_format: str,
        group_name: str,
        output_dir: Path,
        dry_run: bool = True,
    ):
        self.translator = translator
        self.ad_format = ad_format.upper()
        self.group_name = group_name
        self.output_dir = output_dir
        self.dry_run = dry_run

        # Create output dirs
        self.ads_dir = output_dir / "ads"
        self.ads_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        languages: List[Dict],
        base_ads_path: Optional[Path] = None,
    ) -> Path:
        """
        Generate all ad CSVs and the campaign creation CSV.

        Per row in languages CSV:
        - lang_code: comma-separated languages (e.g., "es,en" or "es" or "en")
        - lang_name: display name for the primary non-English language (used for translation)
        - categories: comma-separated (e.g., "straight,gay,trans"), default "straight"
        - types: comma-separated (e.g., "standard,remarketing"), default "standard"
        - ad_csv_straight, ad_csv_gay, ad_csv_trans: per-category base ad CSV paths

        Args:
            languages: List of language config dicts
            base_ads_path: Optional fallback base ads CSV (used if per-category columns missing)

        Returns:
            Path to the generated campaign creation CSV
        """
        campaign_rows = []
        # Cache translated ads per (lang_code, category) to avoid re-translating
        translated_cache = {}  # (lang_code, category) -> translated ads list

        for lang in languages:
            if not lang.get("enabled", True):
                continue

            lang_codes = self._parse_list(lang["lang_code"])
            lang_name = lang.get("lang_name", "")
            geo_raw = lang["geo"].strip().upper()
            geo_name = lang.get("geo_name", "").strip()
            # For file naming: use geo_name if provided, otherwise first geo code
            geo_label = geo_name if geo_name else geo_raw.replace(";", "-").replace(",", "-")

            categories = self._parse_list(lang.get("categories", "straight"))
            types = self._parse_list(lang.get("types", "standard"))

            logger.info(f"\n--- {geo_label} ({geo_raw}) [{','.join(c.upper() for c in lang_codes)}] ---")
            logger.info(f"  Categories: {', '.join(categories)} | Types: {', '.join(types)}")

            # Generate ad CSVs per category per language code
            # ads_files[(category, lang_code)] -> filename
            ads_files = {}

            for category in categories:
                # Resolve base ads path for this category
                cat_ads_path = self._resolve_ads_path(lang, category, base_ads_path)
                if not cat_ads_path:
                    logger.warning(f"  No ads CSV for category '{category}' in {geo_label}, skipping")
                    continue

                base_ads = self._read_ads_csv(cat_ads_path)
                if not base_ads:
                    logger.warning(f"  Empty ads CSV: {cat_ads_path}")
                    continue

                cat_suffix = f"_{category}" if category != "straight" else ""

                for code in lang_codes:
                    ads_filename = f"{self.group_name}_{self.ad_format}_{geo_label}{cat_suffix}_{code}.csv"
                    ads_out = self.ads_dir / ads_filename

                    if code == "en":
                        # English — no translation, no sub14
                        self._write_ads_csv(base_ads, ads_out, None)
                    else:
                        # Translate (use cache if same language+category already done)
                        cache_key = (code, category)
                        if cache_key not in translated_cache:
                            resolve_name = lang_name if lang_name else LANG_NAMES.get(code, code.title())
                            translated_cache[cache_key] = self._translate_ads(base_ads, code, resolve_name)
                        self._write_ads_csv(translated_cache[cache_key], ads_out, code)

                    ads_files[(category, code)] = ads_filename
                    logger.info(f"  {code.upper()} [{category}] ads: {ads_filename}")

            # Generate campaign rows: types x categories x lang_codes
            for campaign_type in types:
                is_remarketing = campaign_type.lower() == "remarketing"

                for category in categories:
                    cat_suffix = f"-{category.upper()}" if category != "straight" else ""
                    rmkt_suffix = "-RMKT" if is_remarketing else ""

                    for code in lang_codes:
                        if (category, code) not in ads_files:
                            continue  # No ads for this combo
                        row = self._build_campaign_row(lang, self.group_name, self.ad_format)
                        row["content_category"] = category
                        row["campaign_type"] = "Remarketing" if is_remarketing else "Standard"
                        row["group"] = lang.get("group", "") or self.group_name
                        row["language"] = lang.get("tj_language", "").strip().upper() or code.upper()
                        row["labels"] = lang.get("labels", "") or (lang_name if lang_name else "")
                        row["csv_file"] = f"ads/{ads_files[(category, code)]}"
                        if is_remarketing:
                            row["variants"] = "desktop,all mobile"
                        campaign_rows.append(row)

        # Write campaign creation CSV
        campaigns_filename = f"{self.group_name}_{self.ad_format}_campaigns.csv"
        campaigns_path = self.output_dir / campaigns_filename
        self._write_campaigns_csv(campaign_rows, campaigns_path)

        logger.info(f"\nCampaign CSV: {campaigns_path}")
        logger.info(f"Total campaign rows: {len(campaign_rows)}")

        return campaigns_path

    @staticmethod
    def _parse_list(value: str) -> List[str]:
        """Parse a comma-separated string into a list of lowercase trimmed values."""
        if not value or not value.strip():
            return ["straight"]
        return [v.strip().lower() for v in value.split(",") if v.strip()]

    def _resolve_ads_path(
        self,
        lang: Dict,
        category: str,
        fallback_path: Optional[Path],
    ) -> Optional[Path]:
        """Resolve the base ads CSV path for a given category.

        Checks language row columns in order:
        1. ad_csv_{category} (e.g., ad_csv_gay)
        2. ad_csv_straight (fallback within CSV)
        3. --ads CLI fallback
        """
        # Check per-category column
        col_key = f"ad_csv_{category}"
        path_str = lang.get(col_key, "").strip()

        # Fallback to straight if category column is empty
        if not path_str and category != "straight":
            path_str = lang.get("ad_csv_straight", "").strip()

        # Fallback to CLI --ads
        if not path_str:
            return fallback_path

        path = Path(path_str)
        if path.exists():
            return path

        # Try relative to languages CSV directory (stored in lang dict)
        if "_csv_dir" in lang:
            resolved = Path(lang["_csv_dir"]) / path_str
            if resolved.exists():
                return resolved

        logger.warning(f"  Ads CSV not found: {path_str}")
        return fallback_path

    # ------------------------------------------------------------------
    # Ad CSV operations
    # ------------------------------------------------------------------

    def _read_ads_csv(self, path: Path) -> List[Dict[str, str]]:
        """Read ad CSV into list of dicts."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _translate_ads(
        self,
        ads: List[Dict[str, str]],
        lang_code: str,
        lang_name: str,
    ) -> List[Dict[str, str]]:
        """Translate translatable fields in ad rows."""
        translatable_cols = TRANSLATABLE_COLUMNS.get(self.ad_format, [])

        # Collect all texts to translate with their character limits
        texts_to_translate = []
        max_lengths = []  # Per-text character limit (None = no limit)
        text_positions = []  # (row_idx, col_name)

        for i, ad in enumerate(ads):
            for col in translatable_cols:
                val = ad.get(col, "").strip()
                if val:
                    texts_to_translate.append(val)
                    max_lengths.append(COLUMN_MAX_LENGTHS.get(col))
                    text_positions.append((i, col))

        if not texts_to_translate:
            return [dict(ad) for ad in ads]

        # Translate — pass max_lengths so the API knows which texts are constrained
        if self.dry_run or self.translator is None:
            # Placeholder translations for dry run
            translated = [f"[{lang_name}] {t}" for t in texts_to_translate]
        else:
            translated = self.translator.translate_batch(
                texts_to_translate, lang_code, lang_name,
                max_lengths=max_lengths,
            )

        # Apply translations with max length enforcement
        result = [dict(ad) for ad in ads]
        for (row_idx, col_name), trans_text in zip(text_positions, translated):
            max_len = COLUMN_MAX_LENGTHS.get(col_name)
            if max_len and len(trans_text) > max_len:
                logger.warning(
                    f"  {col_name} translation too long ({len(trans_text)} > {max_len}): "
                    f"'{trans_text}' → truncated"
                )
                trans_text = trans_text[:max_len].rstrip()
            result[row_idx][col_name] = trans_text

        # Update Ad Name to reflect language (replace _EN_ or add lang suffix)
        for ad in result:
            ad_name = ad.get("Ad Name", "")
            if ad_name:
                # If ad name contains _EN_, replace with _LANG_
                if "_EN_" in ad_name:
                    ad["Ad Name"] = ad_name.replace("_EN_", f"_{lang_code.upper()}_")
                else:
                    # Append language code
                    ad["Ad Name"] = f"{ad_name}_{lang_code.upper()}"

        return result

    def _write_ads_csv(
        self,
        ads: List[Dict[str, str]],
        output_path: Path,
        lang_code: Optional[str],
        translate: bool = False,
    ):
        """Write ad CSV with sub14 param added to URLs (skipped for English)."""
        if not ads:
            return

        url_cols = URL_COLUMNS.get(self.ad_format, ["Target URL"])

        # Process each ad
        processed = []
        for ad in ads:
            row = dict(ad)
            if lang_code:  # None = English, skip sub14
                for col in url_cols:
                    url = row.get(col, "").strip()
                    if url:
                        row[col] = self._add_sub14(url, lang_code)
            processed.append(row)

        fieldnames = list(ads[0].keys())
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(processed)

    def _add_sub14(self, url: str, lang_code: str) -> str:
        """Add &sub14={lang_code} to a URL if not already present."""
        if not url:
            return url

        # Check if sub14 already exists
        if "sub14=" in url:
            # Replace existing sub14
            url = re.sub(r'sub14=[^&]*', f'sub14={lang_code}', url)
        else:
            # Add sub14 parameter
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sub14={lang_code}"

        return url

    # ------------------------------------------------------------------
    # Campaign CSV
    # ------------------------------------------------------------------

    def _build_campaign_row(
        self,
        lang: Dict,
        group_name: str,
        ad_format: str,
    ) -> Dict[str, str]:
        """Build base campaign row from language config."""
        # Normalize geo separators to semicolons for the V2 parser
        geo_raw = lang["geo"].strip().upper()
        geo_value = geo_raw.replace(",", ";") if "," in geo_raw else geo_raw
        return {
            "group": "",  # Set by caller (EN/native variant)
            "keywords": lang.get("keywords", ""),
            "keyword_matches": lang.get("keyword_matches", ""),
            "gender": lang.get("gender", "male"),
            "geo": geo_value,
            "csv_file": "",  # Set by caller
            "ad_format": ad_format,
            "campaign_type": lang.get("campaign_type", "Standard"),
            "bid_type": lang.get("bid_type", "CPA"),
            "language": "",  # Set by caller
            "content_category": "straight",  # Set by caller for gay/trans
            "geo_name": lang.get("geo_name", ""),
            "variants": lang.get("variants", "desktop,ios,android"),
            "target_cpa": lang.get("target_cpa", "50"),
            "per_source_budget": lang.get("per_source_budget", "200"),
            "max_bid": lang.get("max_bid", "10"),
            "frequency_cap": lang.get("frequency_cap", "2"),
            "max_daily_budget": lang.get("max_daily_budget", "250"),
            "cpm_adjust": lang.get("cpm_adjust", ""),
            "enabled": "TRUE",
        }

    def _write_campaigns_csv(
        self,
        rows: List[Dict[str, str]],
        output_path: Path,
    ):
        """Write campaign creation CSV."""
        if not rows:
            return

        fieldnames = [
            "group", "keywords", "keyword_matches", "gender", "geo", "geo_name",
            "csv_file", "ad_format", "campaign_type", "bid_type", "language",
            "content_category", "labels", "variants", "target_cpa", "per_source_budget",
            "max_bid", "frequency_cap", "max_daily_budget", "cpm_adjust", "enabled",
        ]

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def parse_languages_csv(path: Path) -> List[Dict]:
    """Parse languages CSV into list of config dicts."""
    languages = []
    csv_dir = str(path.parent)

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys
            row = {k.strip().lower(): v.strip() for k, v in row.items()}

            enabled = row.get("enabled", "true").lower()
            if enabled in ("false", "no", "0", "n"):
                lang = dict(row)
                lang["enabled"] = False
                lang["_csv_dir"] = csv_dir
                languages.append(lang)
                continue

            lang = dict(row)
            lang["enabled"] = True
            lang["_csv_dir"] = csv_dir
            languages.append(lang)

    return languages
