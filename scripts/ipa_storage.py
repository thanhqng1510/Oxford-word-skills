"""
ipa_storage.py — Shared storage helpers, XML serialization, and environment setup for IPA maintenance.
"""

import json
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "Resources")
DEFINITIONS_JSON = os.path.join(RESOURCES_DIR, "definitions.json")
EXTRAWORDLIST_XML = os.path.join(RESOURCES_DIR, "extrawordlist.xml")


def ensure_wiktionary_ipa():
    """
    Ensures wiktionary_ipa is importable.
    Falls back to sibling repository ../wiktionary-ipa/src if present during local development,
    or exits with clear installation guidance.
    """
    try:
        import wiktionary_ipa
        return wiktionary_ipa
    except ImportError:
        local_pkg = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "wiktionary-ipa", "src"))
        if os.path.isdir(local_pkg) and local_pkg not in sys.path:
            sys.path.insert(0, local_pkg)
        try:
            import wiktionary_ipa
            return wiktionary_ipa
        except ImportError:
            sys.exit(
                "Error: 'wiktionary-ipa' package is required.\n"
                "Install via: pip install git+https://github.com/thanhqng1510/wiktionary-ipa.git\n"
                "Or: pip install wiktionary-ipa"
            )


def update_definitions_json(fixes: Dict[str, str]) -> int:
    """Updates definitions.json with new phonetic values in a single pass."""
    if not fixes or not os.path.isfile(DEFINITIONS_JSON):
        return 0

    with open(DEFINITIONS_JSON, "r", encoding="utf-8") as f:
        defs = json.load(f)

    updated_count = 0
    for word, ipa in fixes.items():
        if word in defs:
            defs[word]["phonetic"] = ipa
            updated_count += 1

    if updated_count > 0:
        with open(DEFINITIONS_JSON, "w", encoding="utf-8") as f:
            json.dump(defs, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return updated_count


def update_extrawordlist_xml(fixes: Dict[str, str]) -> int:
    """
    Updates <ipa> elements in extrawordlist.xml with new IPA strings,
    strictly preserving <![CDATA[/.../]]> blocks, XML comments, and whitespace indentation.
    """
    if not fixes or not os.path.isfile(EXTRAWORDLIST_XML):
        return 0

    with open(EXTRAWORDLIST_XML, "r", encoding="utf-8") as f:
        content = f.read()

    updated_count = 0

    def replace_word_block(match: re.Match) -> str:
        nonlocal updated_count
        word_str = match.group(1)
        if word_str in fixes:
            new_ipa = fixes[word_str]
            updated_count += 1
            before_ipa = match.group(2)
            after_ipa = match.group(3)
            return f'<word str="{word_str}"{before_ipa}<ipa><![CDATA[{new_ipa}]]></ipa>{after_ipa}'
        return match.group(0)

    pattern = re.compile(
        r'<word str="([^"]+)"([^>]*>[\s\r\n]*?)<ipa>.*?<\/ipa>(.*?<\/word>)',
        re.DOTALL,
    )
    new_content = pattern.sub(replace_word_block, content)

    if updated_count > 0:
        with open(EXTRAWORDLIST_XML, "w", encoding="utf-8") as f:
            f.write(new_content)

    return updated_count


def save_vocabulary_fixes(fixes: Dict[str, str]) -> Tuple[int, int]:
    """
    Persists vocabulary IPA updates across both definitions.json and extrawordlist.xml
    in a single pass.
    """
    defs_count = update_definitions_json(fixes)
    xml_count = update_extrawordlist_xml(fixes)
    return defs_count, xml_count
