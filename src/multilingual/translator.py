"""
OpenRouter translation client for multilingual ad copy.

Uses the OpenAI-compatible API at https://openrouter.ai/api/v1
with file-based caching per language.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache" / "translations"


class Translator:
    """Translates ad copy via OpenRouter API with caching."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self._cache: Dict[str, Dict[str, str]] = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate_batch(
        self,
        texts: List[str],
        target_lang_code: str,
        target_lang_name: str,
        max_lengths: Optional[List[Optional[int]]] = None,
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> List[str]:
        """
        Translate a list of texts to the target language.

        Checks cache first, only sends uncached texts to the API.
        max_lengths: optional per-text character limits (None = no limit).
        Returns translations in the same order as input.
        """
        cache = self._load_cache(target_lang_code)

        # Separate cached vs uncached
        results: List[Optional[str]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []
        uncached_max_lengths: List[Optional[int]] = []

        for i, text in enumerate(texts):
            cached = cache.get(text)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                uncached_max_lengths.append(
                    max_lengths[i] if max_lengths else None
                )

        if not uncached_texts:
            logger.info(f"  All {len(texts)} texts found in cache for {target_lang_code}")
            return results  # type: ignore[return-value]

        logger.info(
            f"  Translating {len(uncached_texts)} texts to {target_lang_name} "
            f"({len(texts) - len(uncached_texts)} cached)"
        )

        # Call API
        translated = self._call_api(
            uncached_texts, target_lang_name, temperature, max_retries,
            max_lengths=uncached_max_lengths,
        )

        # Merge results and update cache
        for idx, orig_text, trans_text in zip(
            uncached_indices, uncached_texts, translated
        ):
            results[idx] = trans_text
            cache[orig_text] = trans_text

        self._save_cache(target_lang_code, cache)
        return results  # type: ignore[return-value]

    def translate_single(
        self,
        text: str,
        target_lang_code: str,
        target_lang_name: str,
    ) -> str:
        """Convenience wrapper for translating a single string."""
        return self.translate_batch([text], target_lang_code, target_lang_name)[0]

    def clear_cache(self, lang_code: Optional[str] = None):
        """Clear translation cache. If lang_code is None, clears all."""
        if lang_code:
            cache_file = CACHE_DIR / f"{lang_code.lower()}.json"
            if cache_file.exists():
                cache_file.unlink()
            self._cache.pop(lang_code.lower(), None)
            logger.info(f"Cleared cache for {lang_code}")
        else:
            for f in CACHE_DIR.glob("*.json"):
                f.unlink()
            self._cache.clear()
            logger.info("Cleared all translation caches")

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------

    def _call_api(
        self,
        texts: List[str],
        target_lang_name: str,
        temperature: float,
        max_retries: int,
        max_lengths: Optional[List[Optional[int]]] = None,
    ) -> List[str]:
        """Send a numbered list to OpenRouter and parse results."""
        # Build numbered list, annotating character-limited texts
        lines = []
        has_limits = False
        for i, t in enumerate(texts):
            limit = max_lengths[i] if max_lengths else None
            if limit:
                lines.append(f"{i+1}. [MAX {limit} CHARS] {t}")
                has_limits = True
            else:
                lines.append(f"{i+1}. {t}")
        numbered = "\n".join(lines)

        # Build system prompt — include char limit rule only when needed
        limit_rule = ""
        if has_limits:
            limit_rule = (
                "- CRITICAL CHARACTER LIMITS: Items marked [MAX N CHARS] MUST have "
                "translations that are EXACTLY N characters or fewer (count every letter, "
                "space, and punctuation mark). This is a hard technical limit — the text "
                "will be rejected if it exceeds the limit. Shorten creatively (rephrase, "
                "use shorter synonyms) — do NOT just cut off the end.\n"
            )

        system_prompt = (
            "You are a professional advertising copywriter and translator. "
            "Translate the following numbered list of ad copy into "
            f"{target_lang_name}. CRITICAL RULES:\n"
            "- Translate EVERY word into the target language. Do NOT leave any English words untranslated.\n"
            "- Keep translations concise, punchy, and suitable for online adult advertising.\n"
            f"{limit_rule}"
            "- Use natural, native-sounding phrasing — not literal word-for-word translation.\n"
            "- Preserve any special characters, punctuation, or formatting.\n"
            "- Return ONLY the numbered translations in the exact same format "
            "(number followed by period and space, then translation). "
            "Do NOT include the [MAX N CHARS] tag in your response.\n"
            "- Do not add explanations, notes, or alternatives."
        )

        user_prompt = numbered

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self.API_URL, json=payload, headers=headers, timeout=60
                )
                resp.raise_for_status()
                data = resp.json()

                content = data["choices"][0]["message"]["content"].strip()
                parsed = self._parse_numbered_response(content, len(texts))

                if len(parsed) == len(texts):
                    return parsed

                logger.warning(
                    f"  Expected {len(texts)} translations, got {len(parsed)}. "
                    f"Attempt {attempt}/{max_retries}"
                )
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

                # Pad or truncate on final attempt
                return self._pad_results(parsed, texts)

            except requests.exceptions.RequestException as e:
                logger.warning(f"  API error (attempt {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"  Translation failed after {max_retries} attempts, using originals")
                    return list(texts)

        return list(texts)  # Fallback

    def _parse_numbered_response(self, content: str, expected: int) -> List[str]:
        """Parse numbered response like '1. Translation\\n2. Translation'."""
        results = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip leading number and period: "1. Text" -> "Text"
            parts = line.split(". ", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                results.append(parts[1].strip())
            elif results:
                # Continuation of previous line
                results[-1] += " " + line
        return results

    def _pad_results(self, parsed: List[str], originals: List[str]) -> List[str]:
        """Pad with originals if we got fewer translations than expected."""
        result = list(parsed)
        for i in range(len(parsed), len(originals)):
            result.append(originals[i])
            logger.warning(f"  Using original for item {i+1}: {originals[i]}")
        return result

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _load_cache(self, lang_code: str) -> Dict[str, str]:
        """Load cache from disk (memoized in memory)."""
        key = lang_code.lower()
        if key in self._cache:
            return self._cache[key]

        cache_file = CACHE_DIR / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cache[key] = data
                return data
            except (json.JSONDecodeError, IOError):
                pass

        self._cache[key] = {}
        return self._cache[key]

    def _save_cache(self, lang_code: str, cache: Dict[str, str]):
        """Persist cache to disk."""
        cache_file = CACHE_DIR / f"{lang_code.lower()}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
