#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys

def validate_curriculum(settings_path="Resources/settings.xml", wordlist_path="Resources/extrawordlist.xml"):
    errors = []

    # 1. Parse settings.xml
    try:
        stree = ET.parse(settings_path)
        sroot = stree.getroot()
    except Exception as e:
        print(f"FAIL: Unable to parse settings.xml: {e}")
        return False

    modules = sroot.findall(".//module")
    if len(modules) != 13:
        errors.append(f"Expected 13 modules, found {len(modules)}")

    units = sroot.findall(".//unit")
    if len(units) != 80:
        errors.append(f"Expected 80 units, found {len(units)}")

    unit_nums = [int(u.attrib.get("number", "0")) for u in units]
    if sorted(unit_nums) != list(range(1, 81)):
        errors.append("Units are not contiguous from 1 to 80")

    sections = sroot.findall(".//section")
    if len(sections) != 148:
        errors.append(f"Expected 148 sections, found {len(sections)}")

    # 2. Parse extrawordlist.xml
    try:
        wtree = ET.parse(wordlist_path)
        wroot = wtree.getroot()
    except Exception as e:
        print(f"FAIL: Unable to parse extrawordlist.xml: {e}")
        return False

    word_nodes = wroot.findall(".//word")
    if len(word_nodes) != 2783:
        errors.append(f"Expected 2783 word nodes, found {len(word_nodes)}")

    valid_words = []
    filtered_words = []
    multi_unit_words = []
    active_assignments = 0

    for w in word_nodes:
        s = w.attrib.get("str", "")
        trimmed = s.strip()
        is_valid = len(trimmed) >= 2 and not trimmed.startswith("-") and not trimmed.endswith("-")
        
        u_attr = w.attrib.get("unit", "")
        u_nums = [int(x.strip()) for x in u_attr.split(",") if x.strip()]

        for un in u_nums:
            if un < 1 or un > 80:
                errors.append(f"Word '{s}' references out-of-bounds unit {un}")

        if is_valid:
            valid_words.append((s, u_nums))
            active_assignments += len(u_nums)
            if len(u_nums) > 1:
                multi_unit_words.append((s, u_nums))
        else:
            filtered_words.append((s, u_nums))

    if len(valid_words) != 2781:
        errors.append(f"Expected 2781 valid words, found {len(valid_words)}")
    if len(filtered_words) != 2:
        errors.append(f"Expected 2 filtered words, found {len(filtered_words)}")
    if len(multi_unit_words) != 226:
        errors.append(f"Expected 226 multi-unit words, found {len(multi_unit_words)}")
    if active_assignments != 3031:
        errors.append(f"Expected 3031 active unit assignments, found {active_assignments}")

    if errors:
        print("FAIL: Curriculum validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("PASS: Curriculum verification succeeded (13 modules, 80 units, 148 sections, 2781 valid words, 226 multi-unit words, 3031 assignments).")
    return True

if __name__ == "__main__":
    if not validate_curriculum():
        sys.exit(1)
