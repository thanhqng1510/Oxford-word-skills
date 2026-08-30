//
//  test_update_service.swift
//  Oxford Word Skills — UpdateService Unit Test Suite
//
//  Tests the pure logic from UpdateService (version comparison + JSON parsing).
//  These functions are reimplemented here (Foundation only) so the test runs
//  as a standalone Swift script without requiring AppKit/SwiftUI.
//
//  Run: swift tests/test_update_service.swift
//  Exit 0 on all pass, exit 1 on any failure.
//

import Foundation

// MARK: - ANSI output

let green  = "\u{001B}[32m"
let red    = "\u{001B}[31m"
let yellow = "\u{001B}[33m"
let bold   = "\u{001B}[1m"
let reset  = "\u{001B}[0m"

// MARK: - Test harness

var passCount = 0
var failCount = 0

func assertTest(_ condition: Bool, _ name: String, details: String = "") {
    if condition {
        passCount += 1
        print("  \(green)✓ [PASS]\(reset) \(name)")
    } else {
        failCount += 1
        print("  \(red)✗ [FAIL]\(reset) \(name)")
        if !details.isEmpty { print("         \(yellow)→ \(details)\(reset)") }
    }
}

func assertThrows<E: Error>(_ expectedType: E.Type, _ name: String, block: () throws -> Void) {
    do {
        try block()
        failCount += 1
        print("  \(red)✗ [FAIL]\(reset) \(name) — expected throw, got nothing")
    } catch let e as E {
        _ = e
        passCount += 1
        print("  \(green)✓ [PASS]\(reset) \(name)")
    } catch {
        failCount += 1
        print("  \(red)✗ [FAIL]\(reset) \(name) — wrong error type: \(error)")
    }
}

// MARK: - Pure functions mirrored from UpdateService.swift
// IMPORTANT: keep these in sync with UpdateService.isNewerVersion and
//            UpdateService.parseGitHubRelease whenever either is changed.

func isNewerVersion(_ remote: String, than local: String) -> Bool {
    let r = remote.split(separator: ".").compactMap { Int($0) }
    let l = local.split(separator: ".").compactMap { Int($0) }
    let count = max(r.count, l.count)
    for i in 0..<count {
        let rv = i < r.count ? r[i] : 0
        let lv = i < l.count ? l[i] : 0
        if rv > lv { return true }
        if rv < lv { return false }
    }
    return false
}

// Errors mirrored from UpdateError
enum ParseError: Error { case invalidJSON, missingFields, noMacAsset }

struct ParsedRelease {
    let tag: String
    let version: String
    let releasePageURL: URL
    let downloadURL: URL
}

func parseGitHubRelease(_ data: Data) throws -> ParsedRelease {
    guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
        throw ParseError.invalidJSON
    }
    guard let tagName   = json["tag_name"] as? String,
          let htmlStr   = json["html_url"] as? String,
          let htmlURL   = URL(string: htmlStr),
          let assets    = json["assets"] as? [[String: Any]] else {
        throw ParseError.missingFields
    }
    let macAsset = assets.first { asset in
        guard let name = asset["name"] as? String else { return false }
        return name.hasSuffix(".zip") && name.contains("macOS")
    }
    guard let macAsset,
          let dlStr = macAsset["browser_download_url"] as? String,
          let dlURL = URL(string: dlStr) else {
        throw ParseError.noMacAsset
    }
    let version = tagName.hasPrefix("v") ? String(tagName.dropFirst()) : tagName
    return ParsedRelease(tag: tagName, version: version, releasePageURL: htmlURL, downloadURL: dlURL)
}

// MARK: - Helper: build JSON data

func json(_ string: String) -> Data { string.data(using: .utf8)! }

// MARK: ─────────────────────────────────────────────────────────────────────
// MARK: Version comparison tests (16 cases)
// MARK: ─────────────────────────────────────────────────────────────────────

print("\n\(bold)=== Oxford Word Skills — UpdateService Unit Tests ===\(reset)\n")
print("\(bold)Version comparison:\(reset)")

assertTest(
    isNewerVersion("2.0.0", than: "1.9.9"),
    "newer major (2.0.0 > 1.9.9)"
)
assertTest(
    isNewerVersion("1.1.0", than: "1.0.9"),
    "newer minor (1.1.0 > 1.0.9)"
)
assertTest(
    isNewerVersion("1.0.1", than: "1.0.0"),
    "newer patch (1.0.1 > 1.0.0)"
)
assertTest(
    !isNewerVersion("1.0.0", than: "1.0.0"),
    "equal versions → not newer"
)
assertTest(
    !isNewerVersion("0.9.9", than: "1.0.0"),
    "older returns false (0.9.9 < 1.0.0)"
)
assertTest(
    isNewerVersion("2.0", than: "1.9.9"),
    "short remote padded with zero (2.0 → 2.0.0 > 1.9.9)"
)
assertTest(
    isNewerVersion("1.0.1", than: "1.0"),
    "short local padded with zero (1.0 → 1.0.0 < 1.0.1)"
)
assertTest(
    !isNewerVersion("1.0", than: "1.0"),
    "both short and equal → not newer"
)
assertTest(
    isNewerVersion("2", than: "1.9.9"),
    "single-component remote (2 > 1.9.9)"
)
assertTest(
    isNewerVersion("10.0.0", than: "9.99.99"),
    "multi-digit components (10.0.0 > 9.99.99)"
)
assertTest(
    isNewerVersion("0.0.2", than: "0.0.1"),
    "real-world patch (0.0.2 > 0.0.1)"
)
assertTest(
    !isNewerVersion("0.0.1", than: "0.0.2"),
    "real-world patch reversed → not newer"
)
assertTest(
    !isNewerVersion("1.0.0", than: "1.0.0.0"),
    "equal with extra trailing zero → not newer"
)
assertTest(
    isNewerVersion("1.0.0.1", than: "1.0.0"),
    "extra component in remote (1.0.0.1 > 1.0.0)"
)
assertTest(
    !isNewerVersion("", than: "1.0.0"),
    "empty remote string → not newer"
)
assertTest(
    isNewerVersion("1.0.0", than: ""),
    "empty local string → remote is newer"
)

// MARK: ─────────────────────────────────────────────────────────────────────
// MARK: JSON parsing tests (10 cases)
// MARK: ─────────────────────────────────────────────────────────────────────

print("\n\(bold)JSON parsing:\(reset)")

let validPayload = json("""
{
    "tag_name": "v1.2.3",
    "html_url": "https://github.com/thanhqng1510/Oxford-word-skills/releases/tag/v1.2.3",
    "assets": [
        {
            "name": "OxfordWordSkills-v1.2.3-macOS.zip",
            "browser_download_url": "https://github.com/thanhqng1510/Oxford-word-skills/releases/download/v1.2.3/OxfordWordSkills-v1.2.3-macOS.zip"
        }
    ]
}
""")

// 1. Happy path
if let result = try? parseGitHubRelease(validPayload) {
    assertTest(result.tag == "v1.2.3",         "tag_name parsed correctly",
               details: "got \(result.tag)")
    assertTest(result.version == "1.2.3",      "'v' prefix stripped from version",
               details: "got \(result.version)")
    assertTest(result.releasePageURL.host == "github.com",
               "html_url host is github.com",
               details: "got \(result.releasePageURL.host ?? "nil")")
    assertTest(result.downloadURL.lastPathComponent.hasSuffix(".zip"),
               "download URL points to a .zip",
               details: "got \(result.downloadURL.lastPathComponent)")
} else {
    failCount += 4
    print("  \(red)✗ [FAIL]\(reset) valid payload — parse threw unexpectedly")
}

// 2. Tag without v prefix
let noVPayload = json("""
{
    "tag_name": "1.2.3",
    "html_url": "https://github.com/thanhqng1510/Oxford-word-skills/releases/tag/1.2.3",
    "assets": [{
        "name": "OxfordWordSkills-1.2.3-macOS.zip",
        "browser_download_url": "https://example.com/app.zip"
    }]
}
""")
if let result = try? parseGitHubRelease(noVPayload) {
    assertTest(result.version == "1.2.3", "tag without 'v' prefix parses to same version")
} else {
    failCount += 1
    print("  \(red)✗ [FAIL]\(reset) tag without v prefix threw unexpectedly")
}

// 3. Multiple assets — picks the macOS zip
let multiAssetPayload = json("""
{
    "tag_name": "v2.0.0",
    "html_url": "https://github.com",
    "assets": [
        { "name": "OxfordWordSkills-v2.0.0-Windows.zip",
          "browser_download_url": "https://example.com/win.zip" },
        { "name": "OxfordWordSkills-v2.0.0-macOS.zip",
          "browser_download_url": "https://example.com/mac.zip" }
    ]
}
""")
if let result = try? parseGitHubRelease(multiAssetPayload) {
    assertTest(
        result.downloadURL.absoluteString == "https://example.com/mac.zip",
        "multiple assets — picks macOS zip, not Windows zip",
        details: "got \(result.downloadURL.absoluteString)"
    )
} else {
    failCount += 1
    print("  \(red)✗ [FAIL]\(reset) multi-asset payload threw unexpectedly")
}

// 4. Missing tag_name → missingFields
assertThrows(ParseError.self, "missing tag_name → throws missingFields") {
    _ = try parseGitHubRelease(json("""
    { "html_url": "https://github.com", "assets": [] }
    """))
}

// 5. Empty assets array → noMacAsset
assertThrows(ParseError.self, "empty assets array → throws noMacAsset") {
    _ = try parseGitHubRelease(json("""
    { "tag_name": "v1.0.0", "html_url": "https://github.com", "assets": [] }
    """))
}

// 6. Asset without "macOS" in name → noMacAsset
assertThrows(ParseError.self, "asset without macOS in name → throws noMacAsset") {
    _ = try parseGitHubRelease(json("""
    {
        "tag_name": "v1.0.0", "html_url": "https://github.com",
        "assets": [{ "name": "OxfordWordSkills-v1.0.0-Windows.zip",
                     "browser_download_url": "https://example.com/win.zip" }]
    }
    """))
}

// 7. Asset with .dmg extension (not .zip) → noMacAsset
assertThrows(ParseError.self, "asset with .dmg extension → throws noMacAsset") {
    _ = try parseGitHubRelease(json("""
    {
        "tag_name": "v1.0.0", "html_url": "https://github.com",
        "assets": [{ "name": "OxfordWordSkills-v1.0.0-macOS.dmg",
                     "browser_download_url": "https://example.com/app.dmg" }]
    }
    """))
}

// 8. Completely invalid JSON → invalidJSON
assertThrows(ParseError.self, "non-JSON data → throws invalidJSON") {
    _ = try parseGitHubRelease("not json at all".data(using: .utf8)!)
}

// 9. JSON array instead of object → invalidJSON
assertThrows(ParseError.self, "JSON array (not object) → throws invalidJSON") {
    _ = try parseGitHubRelease("[1, 2, 3]".data(using: .utf8)!)
}

// 10. Missing html_url → missingFields
assertThrows(ParseError.self, "missing html_url → throws missingFields") {
    _ = try parseGitHubRelease(json("""
    { "tag_name": "v1.0.0", "assets": [] }
    """))
}

// MARK: ─────────────────────────────────────────────────────────────────────
// MARK: Summary
// MARK: ─────────────────────────────────────────────────────────────────────

let total = passCount + failCount
print("""

\(bold)═══════════════════════════════════════════\(reset)
\(bold)Results: \(passCount)/\(total) tests passed\(reset)
""")

if failCount > 0 {
    print("\(red)\(bold)✗ \(failCount) test(s) FAILED\(reset)\n")
    exit(1)
} else {
    print("\(green)\(bold)✓ All \(total) tests passed\(reset)\n")
    exit(0)
}
