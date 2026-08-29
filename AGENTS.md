# Agents Guide — Oxford Word Skills

## Project at a Glance

- macOS 26 SwiftUI vocabulary learning app
- 12 modules, 80 units, ~11,800 words with IPA, definitions, synonyms, antonyms
- Zero dependencies — Apple frameworks only (SwiftUI, Foundation, AVFoundation)
- Build: `xcodebuild build -scheme OxfordWordSkills -destination 'platform=macOS'`

## File Map

```
Models/DataModels.swift          # Word, Unit, Module, ExerciseType, NavigationTarget
ViewModels/ContentViewModel.swift # Single @Observable state owner
Views/                           # 10 SwiftUI views (see README for full list)
Utilities/ContentParser.swift    # XML/JSON parsing, data pipeline
Utilities/SpeechService.swift    # British English TTS singleton
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

## What to Avoid

- No SPM dependencies — the project is dependency-free
- No `@Published` / `ObservableObject` — use `@Observable`
- No iOS-only APIs — this is macOS-only
- No hardcoded `Color` values — use semantic styles
- No forced unwrapping
- No `.ultraThinMaterial` — use `.glassEffect()` instead
- No `NavigationLink` — use enum-driven routing
