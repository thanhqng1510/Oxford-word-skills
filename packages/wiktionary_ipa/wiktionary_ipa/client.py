"""
client.py — Live batch client for MediaWiki Action API on en.wiktionary.org.
"""

import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

WIKTIONARY_API_URL = "https://en.wiktionary.org/w/api.php"
DEFAULT_USER_AGENT = (
    "WiktionaryIPABot/1.0 "
    "(https://github.com/thanhqng1510/Oxford-word-skills; contact: dev@example.com) "
    "Python-urllib/3"
)
DEFAULT_BATCH_SIZE = 50
DEFAULT_RATE_LIMIT_DELAY = 0.35  # seconds between batch requests
MAX_RETRIES = 5


class WiktionaryClient:
    """Live batch client for en.wiktionary.org with rate limiting and exponential backoff."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        batch_size: int = DEFAULT_BATCH_SIZE,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    ):
        self.user_agent = user_agent
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0.0

    def _throttle(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def fetch_batch(self, titles: List[str]) -> Dict[str, Optional[str]]:
        """Fetches a batch of up to 50 titles directly from the live MediaWiki Action API."""
        if not titles:
            return {}

        params = {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "revisions",
            "rvslots": "main",
            "rvprop": "content",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        }
        url = f"{WIKTIONARY_API_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip",
            },
        )

        results: Dict[str, Optional[str]] = {}

        for attempt in range(MAX_RETRIES):
            self._throttle()
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw_data = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip" or raw_data.startswith(b"\x1f\x8b"):
                        raw_data = gzip.decompress(raw_data)
                    data = json.loads(raw_data.decode("utf-8", errors="replace"))

                    query_data = data.get("query", {})
                    norm_map: Dict[str, str] = {}
                    for n in query_data.get("normalized", []):
                        norm_map[n.get("to")] = n.get("from")
                    for r in query_data.get("redirects", []):
                        to_t = r.get("to")
                        from_t = r.get("from")
                        norm_map[to_t] = norm_map.get(from_t, from_t)

                    for p in query_data.get("pages", []):
                        title = p.get("title", "")
                        orig_title = norm_map.get(title, title)
                        if p.get("missing"):
                            results[orig_title] = None
                            results[title] = None
                        else:
                            revs = p.get("revisions", [])
                            content = revs[0].get("slots", {}).get("main", {}).get("content", "") if revs else ""
                            results[orig_title] = content
                            results[title] = content

                    for t in titles:
                        if t not in results:
                            results[t] = None

                    return results

            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    delay = (attempt + 1) * 2
                    time.sleep(delay)
                else:
                    break
            except Exception:
                time.sleep(1)

        return {t: None for t in titles}

    def fetch_all(self, titles: List[str], verbose: bool = False) -> Dict[str, Optional[str]]:
        """Fetches wikitext for all titles in batches."""
        unique = sorted(list(set(titles)))
        batches = [unique[i:i + self.batch_size] for i in range(0, len(unique), self.batch_size)]
        pages: Dict[str, Optional[str]] = {}

        for idx, b in enumerate(batches):
            res = self.fetch_batch(b)
            pages.update(res)
            if verbose and ((idx + 1) % 10 == 0 or idx == len(batches) - 1):
                print(f"  [WiktionaryClient] Batch {idx + 1}/{len(batches)} completed")

        return pages

    def fetch_page(self, title: str) -> Optional[str]:
        """Fetches wikitext for a single title."""
        res = self.fetch_batch([title])
        return res.get(title)
