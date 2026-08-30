#!/usr/bin/env python3
"""Master E2E Test Suite Runner for Oxford Word Skills.

Executes all 4 tiers of tests:
- Tier 1: Feature Coverage (F1 to F9)
- Tier 2: Boundary & Corner Cases
- Tier 3: Cross-Feature Combinations
- Tier 4: Real-World Application Scenarios

Outputs structured summary reports and exits with code 0 on complete pass,
or code 1 on any test failure.
"""

import argparse
import json
import os
import sys
import time
import unittest
from io import StringIO
from typing import Any, Dict, List

# ANSI Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class StructuredTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_records: List[Dict[str, Any]] = []

    def startTest(self, test):
        super().startTest(test)
        self._start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        self.test_records.append({
            "test_id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "doc": getattr(test, "_testMethodDoc", "") or "",
            "status": "PASS",
            "duration": round(elapsed, 4),
            "error": None,
        })
        sys.stdout.write(f"  {GREEN}✓ [PASS]{RESET} {test.id()}\n")
        sys.stdout.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        err_msg = self._exc_info_to_string(err, test)
        self.test_records.append({
            "test_id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "doc": getattr(test, "_testMethodDoc", "") or "",
            "status": "FAIL",
            "duration": round(elapsed, 4),
            "error": err_msg,
        })
        sys.stdout.write(f"  {RED}✗ [FAIL]{RESET} {test.id()}\n")
        sys.stdout.flush()

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = time.time() - getattr(self, "_start_time", time.time())
        err_msg = self._exc_info_to_string(err, test)
        self.test_records.append({
            "test_id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "doc": getattr(test, "_testMethodDoc", "") or "",
            "status": "ERROR",
            "duration": round(elapsed, 4),
            "error": err_msg,
        })
        sys.stdout.write(f"  {RED}⚠ [ERROR]{RESET} {test.id()}\n")
        sys.stdout.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_records.append({
            "test_id": test.id(),
            "name": getattr(test, "_testMethodName", str(test)),
            "doc": getattr(test, "_testMethodDoc", "") or "",
            "status": "SKIP",
            "duration": 0.0,
            "error": reason,
        })
        sys.stdout.write(f"  {YELLOW}○ [SKIP]{RESET} {test.id()} ({reason})\n")
        sys.stdout.flush()


def run_test_module(module_name: str) -> Tuple[unittest.TestSuite, StructuredTestResult]:
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(module_name)
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, resultclass=StructuredTestResult, verbosity=0)
    result = runner.run(suite)
    return suite, result


def main():
    parser = argparse.ArgumentParser(description="Run Oxford Word Skills E2E Test Suite")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Test Tier to run")
    parser.add_argument("--json-out", help="Path to write JSON summary report")
    args = parser.parse_args()

    # Ensure project root is on sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print(f"\n{BOLD}{CYAN}======================================================={RESET}")
    print(f"{BOLD}{CYAN}   Oxford Word Skills — End-to-End Test Suite Runner   {RESET}")
    print(f"{BOLD}{CYAN}======================================================={RESET}\n")

    tier_modules = {
        "Tier 1: Feature Coverage (F1–F9)": "tests.test_tier1_features",
        "Tier 2: Boundary & Corner Cases": "tests.test_tier2_boundary",
        "Tier 3: Cross-Feature Combinations": "tests.test_tier3_combinations",
        "Tier 4: Real-World Scenarios": "tests.test_tier4_scenarios",
    }

    if args.tier != "all":
        tier_key = [k for k in tier_modules.keys() if f"Tier {args.tier}:" in k][0]
        tier_modules = {tier_key: tier_modules[tier_key]}

    all_records = []
    tier_summaries = {}
    overall_start = time.time()

    for tier_name, module_path in tier_modules.items():
        print(f"\n{BOLD}>>> Executing {tier_name} ({module_path})...{RESET}")
        _, result = run_test_module(module_path)
        all_records.extend(result.test_records)
        
        passed = sum(1 for r in result.test_records if r["status"] == "PASS")
        failed = sum(1 for r in result.test_records if r["status"] in ("FAIL", "ERROR"))
        skipped = sum(1 for r in result.test_records if r["status"] == "SKIP")
        total = len(result.test_records)

        tier_summaries[tier_name] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    total_elapsed = round(time.time() - overall_start, 3)
    total_tests = len(all_records)
    total_passed = sum(1 for r in all_records if r["status"] == "PASS")
    total_failed = sum(1 for r in all_records if r["status"] in ("FAIL", "ERROR"))
    total_skipped = sum(1 for r in all_records if r["status"] == "SKIP")

    # Tier Breakdown Table
    print(f"\n{BOLD}=================== Tier Summary Breakdown ==================={RESET}")
    print(f"{'Tier Name':<42} | {'Total':<6} | {'Pass':<6} | {'Fail':<6} | {'Skip':<6}")
    print("-" * 75)
    for t_name, stats in tier_summaries.items():
        color = GREEN if stats["failed"] == 0 else RED
        print(
            f"{t_name:<42} | {stats['total']:<6} | {GREEN}{stats['passed']:<6}{RESET} | "
            f"{color}{stats['failed']:<6}{RESET} | {YELLOW}{stats['skipped']:<6}{RESET}"
        )
    print("-" * 75)
    print(
        f"{'TOTAL OVERALL':<42} | {total_tests:<6} | {GREEN}{total_passed:<6}{RESET} | "
        f"{RED if total_failed > 0 else GREEN}{total_failed:<6}{RESET} | {YELLOW}{total_skipped:<6}{RESET}"
    )
    print(f"Elapsed Time: {total_elapsed}s\n")

    # Detailed Failure Logs if any
    failures = [r for r in all_records if r["status"] in ("FAIL", "ERROR")]
    if failures:
        print(f"\n{BOLD}{RED}=================== Failure Details ({len(failures)}) ==================={RESET}")
        for i, f in enumerate(failures, 1):
            print(f"\n{BOLD}[{i}] {RED}{f['test_id']}{RESET}")
            if f.get("doc"):
                print(f"    {CYAN}Objective:{RESET} {f['doc'].strip()}")
            if f.get("error"):
                # Print first few lines of traceback/assertion error
                err_lines = f["error"].strip().split("\n")
                print(f"    {YELLOW}Assertion:{RESET} {err_lines[-1]}")
                if len(err_lines) > 1:
                    print(f"    {YELLOW}Location:{RESET} {err_lines[-2].strip()}")

    # Export JSON if requested
    if args.json_out:
        summary_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "elapsed_seconds": total_elapsed,
            "tier_breakdown": tier_summaries,
            "test_records": all_records,
        }
        with open(args.json_out, "w", encoding="utf-8") as jf:
            json.dump(summary_payload, jf, indent=2)
        print(f"\nSaved structured test report to: {args.json_out}")

    print(f"\n{BOLD}======================================================={RESET}")
    if total_failed == 0:
        print(f"{BOLD}{GREEN}  >>> ALL {total_tests} TESTS PASSED SUCCESSFULLY! (Exit Code: 0) <<<{RESET}")
        print(f"{BOLD}=======================================================\n")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}  >>> {total_failed} / {total_tests} TESTS FAILED (Exit Code: 1) <<<{RESET}")
        print(f"{BOLD}=======================================================\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
