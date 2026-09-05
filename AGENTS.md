# Agents Guide — Oxford Word Skills

## Project at a Glance

- macOS 26 SwiftUI vocabulary learning app
- 12 modules, 80 units, ~11,800 words with IPA, definitions, synonyms, antonyms
- Zero dependencies — Apple frameworks only (SwiftUI, Foundation, AVFoundation)
- Build: `xcodebuild build -scheme OxfordWordSkills -destination 'platform=macOS'`
- Test: `./run_e2e_tests.sh` or `python3 tests/run_all_tests.py`

## File Map

```
Models/DataModels.swift          # Word, Unit, Module, ExerciseType, NavigationTarget
ViewModels/ContentViewModel.swift # Single @Observable state owner
Views/                           # 9 SwiftUI views (see README for full list)
Utilities/ContentParser.swift    # XML/JSON parsing, data pipeline
Utilities/SpeechService.swift    # Multi-accent TTS service (@Observable)
Resources/settings.xml           # Module/unit structure
Resources/extrawordlist.xml      # Vocabulary with IPA (Unicode IPA, slash-enclosed)
Resources/definitions.json       # Rich definitions + phonetic IPA field
scripts/check_ipa.py             # Fast local IPA audit (< 1s, no network)
scripts/update_ipa.py            # Delta updater — fetches IPA for new words from Wiktionary
scripts/audit_wiktionary_ipa.py  # Full Wiktionary re-audit (periodic)
scripts/cache/wiktionary_cache.json  # Local Wiktionary cache (~3,000 entries)
```

## Architecture Patterns

### Single ViewModel

`ContentViewModel` is the only state owner. All views receive it via `init`. No child-to-child communication. No `@EnvironmentObject`.

### Navigation via Enum

`NavigationTarget` enum drives the detail view through a `switch`. No `NavigationLink`. No `NavigationStack`.

### Data Pipeline

`ContentParser.buildModules()` orchestrates:
- `settings.xml` → `Module` / `Unit` hierarchy
- `extrawordlist.xml` → `[Word]` with IPA and unit assignments
- `definitions.json` → rich definitions, synonyms, antonyms
- Merge → `[Module]` with nested `[Unit]` with nested `[Word]`

### Progress Persistence

Learned words stored as `Set<String>` in UserDefaults. Key: `"learnedWords"`. Word key format: `"word|sorted,unit,numbers"`.

## Coding Conventions

### Swift Style

- `@Observable` over `ObservableObject` / `@Published`
- `@Bindable` for two-way view binding
- Semantic colors: `.foregroundStyle(.secondary)`, not `Color.gray`
- No forced unwrapping — use `guard` / `if let`
- No third-party packages — ever

### SwiftUI Patterns

- `.listStyle(.sidebar)` for sidebar lists
- `ContentUnavailableView` for empty states
- `Table` with `TableColumn` for data (macOS-native)
- `LazyVGrid` with `.adaptive` for responsive grids
- Custom `Layout` protocol for `FlowLayout`

### Naming

- Views: `<Feature>View` (e.g., `FlashcardView`, `QuizView`)
- ViewModels: `<Feature>ViewModel`
- Models: plain names (`Word`, `Unit`, `Module`)
- Utilities: `<Purpose>Service` or `<Purpose>Parser`

## Liquid Glass (macOS 26)

### Core Rule

Glass is for **chrome**, not content. Apply to toolbars, sidebars, floating panels, and card surfaces — never to the main document area or text-heavy content.

### Migration: ultraThinMaterial → glassEffect()

Replace all `.ultraThinMaterial` backgrounds with `.glassEffect()`:

```swift
// BEFORE
RoundedRectangle(cornerRadius: 20)
    .fill(.ultraThinMaterial)

// AFTER
RoundedRectangle(cornerRadius: 20)
    .glassEffect()
```

Affected files: `FlashcardView`, `QuizView`, `FillInBlankView`, `ProgressDashboardView`.

### GlassEffectContainer

Group related glass elements in a `GlassEffectContainer`:

```swift
GlassEffectContainer {
    HStack {
        Button("Action") { /* ... */ }
            .glassEffect()
    }
}
```

### Toolbar Glass

Add Liquid Glass toolbar to `ContentView`:

```swift
.toolbar {
    ToolbarItemGroup(placement: .primaryAction) {
        Button("Search") { /* ... */ }
            .glassEffect()
    }
}
.windowToolbarStyle(.unified)
```

### Sidebar Glass

`SidebarView` uses `.listStyle(.sidebar)`. On macOS 26, the sidebar automatically adopts glass styling. Keep `.listStyle(.sidebar)` — no manual glass needed.

### Glass Tinting

Use tint for semantic meaning only, not decoration:

```swift
.glassEffect(.regular.tint(.blue))  // selected state
.glassEffect()                      // default, no tint
```

### Glass Don'ts

- Don't apply glass to content areas (document, table, text editor)
- Don't stack glass on glass — use `GlassEffectContainer` instead
- Don't use heavy tint opacity — it kills refraction and looks flat
- Don't mix glass variants in the same container

### Glass Variants

| Variant | Use |
|---|---|
| `.regular` | Standard glass (default) |
| `.clear` | Transparent glass |
| `.identity` | No visual effect |

## Animation

### Transitions

Use `withAnimation` for all state-driven view changes:

```swift
withAnimation(.smooth) { showingDetail = true }
withAnimation(.spring(duration: 0.6)) { /* card flip */ }
```

### Matched Geometry

Use `@Namespace` + `.matchedGeometryEffect` for:
- Flashcard flip animation
- Exercise type transitions in `ExerciseContainerView`
- Card expansion in `ProgressDashboardView`

### Symbol Effects

Use `.symbolEffect(.bounce)` on interactive SF Symbols:
- Checkmarks, stars, speaker icons
- Toggle states, navigation indicators

## Testing & Quality Assurance

### Master Test Runner
Run the full 3-phase automated validation suite (Python 4-tier tests, Swift engine integration, Xcode compilation):
```bash
./run_e2e_tests.sh
```

### Python E2E Test Suite (99 Tests)
Verifies schema validity, curriculum alignment, definition completeness, game mechanics,
and IPA correctness (completeness, format, SAMPA rejection, dialect validation):
```bash
python3 tests/run_all_tests.py
```

### Swift Engine Integration Tests
Verifies `ContentParser.buildModules()`, `WordDetail` decoding, and module hierarchy:
```bash
swift Models/DataModels.swift Utilities/ContentParser.swift tests/test_engine_pipeline.swift
```

### Swift Stress & Simulation Suites
Simulates 10,000+ quiz questions, distractor availability, and headword normalization across all 80 units:
```bash
swift Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_quiz_matching.swift
swift Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_headwords.swift
```

## IPA Maintenance Toolkit

All vocabulary in the app uses verified British English (Received Pronunciation) IPA
sourced from Wiktionary. Use these scripts for all IPA-related tasks.

### Fast local audit — no network, < 1 second
```bash
python3 scripts/check_ipa.py              # summary (exit 1 if any issues)
python3 scripts/check_ipa.py --verbose    # list every problem
python3 scripts/check_ipa.py --json       # machine-readable JSON (CI-friendly)
```
Run this **before every commit** that touches `definitions.json` or `extrawordlist.xml`.

### Adding new vocabulary — fetch IPA from Wiktionary
```bash
# Fetch and apply IPA for all new/missing entries (uses local cache first)
python3 scripts/update_ipa.py

# Single word
python3 scripts/update_ipa.py --word "ameliorate"

# Preview without writing
python3 scripts/update_ipa.py --dry-run
```

### Periodic full re-audit (quarterly or after major Wiktionary updates)
```bash
python3 scripts/audit_wiktionary_ipa.py
```

### IPA data sources & format rules
- **Source of truth**: English Wiktionary, UK/RP pronunciation (first choice)
- **Format**: Always `/unicode-ipa/` (slash-enclosed Unicode, no SAMPA, no `ː` ASCII colon)
- **`ContentParser.sampaToIPA()`** short-circuits when the input starts with `/`, so storing
  Unicode IPA directly in `extrawordlist.xml` `<ipa>` CDATA elements is the correct pattern
- **Forbidden**: `ɚ`, `ɝ`, `ɾ` (rhotic/tap — American English only)
- **Cache**: `scripts/cache/wiktionary_cache.json` (~42 MB, ~3,000 entries) — commit it

### IPA-related tests (in the 99-test suite)
| Test | Validates |
|---|---|
| `test_f9_07` | 100% non-empty, slash-enclosed runtime IPA |
| `test_f9_08` | Zero SAMPA residue in runtime words |
| `test_t2_13` | Valid IPA character set only |
| `test_t2_15` | No raw SAMPA tokens |
| `test_t2_17` | No `ɚ`/`ɝ`/`ɾ` (American English) |
| `test_t4_09` | Full 80-unit IPA audit |



1. **Test**: Run `./run_e2e_tests.sh` + Swift stress tests.
2. **Install**: Build Release and install to `/Applications/OxfordWordSkills.app`.
3. **PR**: Push branch and open PR via `gh pr create` — **never push directly to main, never auto-merge**.

## What to Avoid

- Never push directly to `main` — all changes (including docs, rules, and code) must go through a feature branch and PR
- No SPM dependencies — the project is dependency-free
- No `@Published` / `ObservableObject` — use `@Observable`
- No iOS-only APIs — this is macOS-only
- No hardcoded `Color` values — use semantic styles
- No forced unwrapping
- No `.ultraThinMaterial` — use `.glassEffect()` instead
- No `NavigationLink` — use enum-driven routing

