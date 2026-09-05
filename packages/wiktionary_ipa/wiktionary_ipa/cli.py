"""
cli.py — Command-line interface for wiktionary-ipa library.
"""

import argparse
import json
import sys
from . import batch_lookup, lookup, verify_word, normalize_ipa, is_valid_ipa


def main():
    parser = argparse.ArgumentParser(
        prog="wiktionary-ipa",
        description="Extract and verify British English (RP) IPA pronunciations from en.wiktionary.org live."
    )
    parser.add_argument("words", nargs="*", help="Word(s) to look up live on Wiktionary")
    parser.add_argument("--verify", nargs=2, metavar=("WORD", "EXPECTED_IPA"), help="Verify expected IPA against live web")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.verify:
        word, expected = args.verify
        res = verify_word(word, expected)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            status = res["status"]
            print(f"Word: {word}")
            print(f"Status: {status}")
            print(f"Expected: {res['expected_ipa']}")
            print(f"Live Web: {res.get('web_ipa')}")
        sys.exit(0 if res["status"] in ("MATCH", "EQUIVALENT") else 1)

    if not args.words:
        parser.print_help()
        sys.exit(0)

    if len(args.words) == 1:
        w = args.words[0]
        ipa = lookup(w)
        if args.json:
            print(json.dumps({"word": w, "ipa": ipa}, indent=2))
        else:
            if ipa:
                print(f"{w}: {ipa}")
            else:
                print(f"{w}: Not found on Wiktionary (or no British RP transcription)")
                sys.exit(1)
    else:
        results = batch_lookup(args.words)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for w, ipa in results.items():
                print(f"{w:25s}: {ipa or 'NOT FOUND'}")


if __name__ == "__main__":
    main()
