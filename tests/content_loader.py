"""Shared dataset loader and helpers for Oxford Word Skills E2E tests."""

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESOURCES_DIR = os.path.join(BASE_DIR, "Resources")
SETTINGS_XML_PATH = os.path.join(RESOURCES_DIR, "settings.xml")
EXTRAWORDLIST_XML_PATH = os.path.join(RESOURCES_DIR, "extrawordlist.xml")
DEFINITIONS_JSON_PATH = os.path.join(RESOURCES_DIR, "definitions.json")

ALLOWED_POS: Set[str] = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "idiom",
    "phrase",
    "pronoun",
    "preposition",
    "conjunction",
    "exclamation",
}

# Known US spellings that should be UK spellings in learner definitions
US_SPELLING_PATTERNS: List[Tuple[str, str, str]] = [
    (r"\b([a-z]+)ize\b", r"\1ise", "-ize -> -ise"),
    (r"\b([a-z]+)izing\b", r"\1ising", "-izing -> -ising"),
    (r"\b([a-z]+)ized\b", r"\1ised", "-ized -> -ised"),
    (r"\b([a-z]+)ization\b", r"\1isation", "-ization -> -isation"),
    (r"\b([a-z]+)izations\b", r"\1isations", "-izations -> -isations"),
    (r"\bcolor\b", "colour", "color -> colour"),
    (r"\bcolors\b", "colours", "colors -> colours"),
    (r"\bcolored\b", "coloured", "colored -> coloured"),
    (r"\bcoloring\b", "colouring", "coloring -> colouring"),
    (r"\bflavor\b", "flavour", "flavor -> flavour"),
    (r"\bflavors\b", "flavours", "flavors -> flavours"),
    (r"\bflavored\b", "flavoured", "flavored -> flavoured"),
    (r"\bflavoring\b", "flavouring", "flavoring -> flavouring"),
    (r"\bhonor\b", "honour", "honor -> honour"),
    (r"\bhonors\b", "honours", "honors -> honours"),
    (r"\bhonored\b", "honoured", "honored -> honoured"),
    (r"\bhonoring\b", "honouring", "honoring -> honouring"),
    (r"\bhumor\b", "humour", "humor -> humour"),
    (r"\bhumors\b", "humours", "humors -> humours"),
    (r"\blabor\b", "labour", "labor -> labour"),
    (r"\blabors\b", "labours", "labors -> labours"),
    (r"\blabored\b", "laboured", "labored -> laboured"),
    (r"\blaboring\b", "labouring", "laboring -> labouring"),
    (r"\bneighbor\b", "neighbour", "neighbor -> neighbour"),
    (r"\bneighbors\b", "neighbours", "neighbors -> neighbours"),
    (r"\bneighborhood\b", "neighbourhood", "neighborhood -> neighbourhood"),
    (r"\bbehavior\b", "behaviour", "behavior -> behaviour"),
    (r"\bbehaviors\b", "behaviours", "behaviors -> behaviours"),
    (r"\bbehavioral\b", "behavioural", "behavioral -> behavioural"),
    (r"\bfavor\b", "favour", "favor -> favour"),
    (r"\bfavors\b", "favours", "favors -> favours"),
    (r"\bfavored\b", "favoured", "favored -> favoured"),
    (r"\bfavoring\b", "favouring", "favoring -> favouring"),
    (r"\bfavorite\b", "favourite", "favorite -> favourite"),
    (r"\bfavorites\b", "favourites", "favorites -> favourites"),
    (r"\bcenter\b", "centre", "center -> centre"),
    (r"\bcenters\b", "centres", "centers -> centres"),
    (r"\bcentered\b", "centred", "centered -> centred"),
    (r"\bcentering\b", "centring", "centering -> centring"),
    (r"\btheater\b", "theatre", "theater -> theatre"),
    (r"\btheaters\b", "theatres", "theaters -> theatres"),
    (r"\bmeter\b", "metre", "meter -> metre (measuring unit)"),
    (r"\bmeters\b", "metres", "meters -> metres (measuring unit)"),
    (r"\bfiber\b", "fibre", "fiber -> fibre"),
    (r"\bfibers\b", "fibres", "fibers -> fibres"),
    (r"\bliter\b", "litre", "liter -> litre"),
    (r"\bliters\b", "litres", "liters -> litres"),
    (r"\bdefense\b", "defence", "defense -> defence"),
    (r"\bdefenses\b", "defences", "defenses -> defences"),
    (r"\boffense\b", "offence", "offense -> offence"),
    (r"\boffenses\b", "offences", "offenses -> offences"),
    (r"\bpretense\b", "pretence", "pretense -> pretence"),
    (r"\banalyze\b", "analyse", "analyze -> analyse"),
    (r"\banalyzed\b", "analysed", "analyzed -> analysed"),
    (r"\banalyzing\b", "analysing", "analyzing -> analysing"),
    (r"\bparalyze\b", "paralyse", "paralyze -> paralyse"),
    (r"\bparalyzed\b", "paralysed", "paralyzed -> paralysed"),
]

# Corrupt token patterns
CORRUPT_TOKENS = [
    "🍑",
    "∵",
    "BS",
    "bullshit",
    "DgammaDtime",
    "dog and bone (Cockney rhyming slang)",
]


@dataclass
class SectionData:
    title: str
    sec_type: str


@dataclass
class UnitData:
    number: Int = 0
    title: str = ""
    sections: List[SectionData] = field(default_factory=list)


@dataclass
class ModuleData:
    title: str
    units: List[UnitData] = field(default_factory=list)


@dataclass
class RawWordData:
    word: str
    ipa: str
    unit_numbers: List[int]
    has_audio: bool


@dataclass
class WordDefinitionData:
    part_of_speech: str
    definition: str
    example: str


@dataclass
class RuntimeWord:
    word: str
    ipa: str
    unit_numbers: List[int]
    has_audio: bool
    definitions: List[WordDefinitionData] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    @property
    def short_definition(self) -> str:
        if self.definitions:
            return self.definitions[0].definition
        return "No definition available"

    @property
    def part_of_speech(self) -> str:
        if self.definitions:
            return self.definitions[0].part_of_speech
        return ""

    @property
    def persistence_key(self) -> str:
        sorted_units = ",".join(str(u) for u in sorted(self.unit_numbers))
        return f"{self.word}|{sorted_units}"


def is_valid_swift_word(word_str: str) -> bool:
    """Matches Swift ContentParser.isValidWord: trimmed.count >= 2, no leading/trailing hyphen."""
    trimmed = word_str.strip()
    if len(trimmed) < 2:
        return False
    if trimmed.startswith("-") or trimmed.endswith("-"):
        return False
    return True


def load_settings_xml() -> Tuple[ET.ElementTree, List[ModuleData]]:
    """Loads and parses settings.xml into ModuleData and UnitData."""
    tree = ET.parse(SETTINGS_XML_PATH)
    root = tree.getroot()
    modules: List[ModuleData] = []

    for mod_elem in root.findall("module"):
        mod_title = mod_elem.attrib.get("title", "")
        units: List[UnitData] = []
        for unit_elem in mod_elem.findall("unit"):
            unit_num = int(unit_elem.attrib.get("number", "0"))
            unit_title = unit_elem.attrib.get("title", "")
            sections: List[SectionData] = []
            for sec_elem in unit_elem.findall("section"):
                sec_title = sec_elem.attrib.get("title", "")
                sec_type = sec_elem.attrib.get("type", "")
                sections.append(SectionData(title=sec_title, sec_type=sec_type))
            units.append(UnitData(number=unit_num, title=unit_title, sections=sections))
        modules.append(ModuleData(title=mod_title, units=units))

    return tree, modules


def sampa_to_ipa(sampa: str) -> str:
    """Converts legacy Oxford SAMPA / ASCII phonetic encoding into standard British Unicode IPA."""
    if not sampa:
        return ""
    trimmed = sampa.strip()
    if not trimmed:
        return ""
    if trimmed.startswith("/") and trimmed.endswith("/"):
        return trimmed

    text = trimmed
    text = text.replace("”", "\"")
    text = text.replace("Í", "tS")
    text = text.replace("Ù", "dZ")
    text = text.replace("2@", "@")
    text = text.replace("Ww", "w")
    text = text.replace("2", "@")

    replacements = [
        ("\"", "ˈ"),
        ("%", "ˌ"),
        ("tS", "tʃ"),
        ("dZ", "dʒ"),
        ("eI", "eɪ"),
        ("aI", "aɪ"),
        ("OI", "ɔɪ"),
        ("aU", "aʊ"),
        ("@U", "əʊ"),
        ("I@", "ɪə"),
        ("e@", "eə"),
        ("U@", "ʊə"),
        ("3:", "ɜː"),
        ("3", "ɜː"),
        ("i:", "iː"),
        ("u:", "uː"),
        ("A:", "ɑː"),
        ("O:", "ɔː"),
        (":", "ː"),
        ("@", "ə"),
        ("&", "æ"),
        ("A", "ɑː"),
        ("V", "ʌ"),
        ("O", "ɔː"),
        ("Q", "ɒ"),
        ("U", "ʊ"),
        ("I", "ɪ"),
        ("E", "e"),
        ("T", "θ"),
        ("D", "ð"),
        ("S", "ʃ"),
        ("Z", "ʒ"),
        ("N", "ŋ"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()
    return f"/{text}/"


def load_extrawordlist_xml() -> Tuple[ET.ElementTree, List[RawWordData]]:
    """Loads and parses extrawordlist.xml into RawWordData."""
    tree = ET.parse(EXTRAWORDLIST_XML_PATH)
    root = tree.getroot()
    words: List[RawWordData] = []

    for word_elem in root.findall(".//word"):
        word_str = word_elem.attrib.get("str", "")
        unit_str = word_elem.attrib.get("unit", "")
        unit_numbers: List[int] = []
        for part in unit_str.split(","):
            part_clean = part.strip()
            if part_clean.isdigit():
                unit_numbers.append(int(part_clean))

        ipa_elem = word_elem.find("ipa")
        raw_ipa = ipa_elem.text if ipa_elem is not None and ipa_elem.text else ""
        ipa = sampa_to_ipa(raw_ipa)

        audio_nodes = word_elem.findall("audio")
        has_audio = len(audio_nodes) > 0

        words.append(
            RawWordData(
                word=word_str,
                ipa=ipa,
                unit_numbers=unit_numbers,
                has_audio=has_audio,
            )
        )

    return tree, words


def load_definitions_json() -> Dict[str, Any]:
    """Loads definitions.json as a dictionary."""
    with open(DEFINITIONS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_runtime_modules() -> Tuple[List[ModuleData], List[RuntimeWord], Dict[int, List[RuntimeWord]]]:
    """Replicates Swift ContentParser.buildModules() pipeline."""
    _, modules = load_settings_xml()
    _, raw_words = load_extrawordlist_xml()
    defs_dict = load_definitions_json()

    # Filter by isValidWord
    valid_raw_words = [w for w in raw_words if is_valid_swift_word(w.word)]

    runtime_words: List[RuntimeWord] = []
    for raw in valid_raw_words:
        rw = RuntimeWord(
            word=raw.word,
            ipa=raw.ipa,
            unit_numbers=raw.unit_numbers,
            has_audio=raw.has_audio,
        )
        if raw.word in defs_dict:
            detail = defs_dict[raw.word]
            defs: List[WordDefinitionData] = []
            all_syns: List[str] = []
            all_ants: List[str] = []
            all_exs: List[str] = []

            for meaning in detail.get("meanings", []):
                pos = meaning.get("partOfSpeech", "")
                for d in meaning.get("definitions", []):
                    def_text = d.get("definition", "")
                    ex_text = d.get("example", "")
                    defs.append(WordDefinitionData(part_of_speech=pos, definition=def_text, example=ex_text))
                    if ex_text:
                        all_exs.append(ex_text)
                all_syns.extend(meaning.get("synonyms", []))
                all_ants.extend(meaning.get("antonyms", []))

            rw.definitions = defs
            rw.synonyms = unique_preserve_order(all_syns)[:10]
            rw.antonyms = unique_preserve_order(all_ants)[:10]
            rw.examples = unique_preserve_order(all_exs)[:5]

        runtime_words.append(rw)

    # Group by unit
    words_by_unit: Dict[int, List[RuntimeWord]] = {}
    for rw in runtime_words:
        for u in rw.unit_numbers:
            if u not in words_by_unit:
                words_by_unit[u] = []
            words_by_unit[u].append(rw)

    # Sort within units alphabetically
    for u in words_by_unit:
        words_by_unit[u].sort(key=lambda w: w.word.lower())

    return modules, runtime_words, words_by_unit
