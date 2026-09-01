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
Views/                           # 10 SwiftUI views (see README for full list)
Utilities/ContentParser.swift    # XML/JSON parsing, data pipeline
Utilities/SpeechService.swift    # Multi-accent TTS service (@Observable)
Resources/settings.xml           # Module/unit structure
Resources/extrawordlist.xml      # Vocabulary with IPA
Resources/definitions.json       # Rich definitions
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

Affected files: `FlashcardView`, `QuizView`, `FillInBlankView`, `ProgressDashboardView`, `CategorizationView`.

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

### Python E2E Test Suite (80 Tests)
Verifies schema validity, curriculum alignment, definition completeness, and game mechanics:
```bash
python3 tests/run_all_tests.py
```

### Swift Engine Integration Tests
Verifies `ContentParser.buildModules()`, `WordDetail` decoding, and module hierarchy:
```bash
swift Models/DataModels.swift Utilities/ContentParser.swift tests/test_engine_pipeline.swift
```

### Swift Stress & Simulation Suites
Simulates 10,000+ quiz questions and 85,000+ categorization runs to verify 0 intra-unit distractor collisions and robust game state transitions:
```bash
swift Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_quiz_matching.swift
swift Models/DataModels.swift Utilities/ContentParser.swift tests/stress_test_headwords_and_categorization.swift
```

## Delivery Workflow

1. **Test**: Run `./run_e2e_tests.sh` + Swift stress tests.
2. **Install**: Build Release and install to `/Applications/OxfordWordSkills.app`.
3. **PR**: Push branch and open PR via `gh pr create` — **never auto-merge**.

## What to Avoid

- No SPM dependencies — the project is dependency-free
- No `@Published` / `ObservableObject` — use `@Observable`
- No iOS-only APIs — this is macOS-only
- No hardcoded `Color` values — use semantic styles
- No forced unwrapping
- No `.ultraThinMaterial` — use `.glassEffect()` instead
- No `NavigationLink` — use enum-driven routing

