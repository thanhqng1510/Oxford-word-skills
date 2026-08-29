# Oxford Word Skills

A macOS vocabulary learning companion for the *Oxford Word Skills* textbook series.

![macOS 26+](https://img.shields.io/badge/macOS-26.0+-blue)
![Swift 5](https://img.shields.io/badge/Swift-5.0-orange)
![Xcode 26](https://img.shields.io/badge/Xcode-26+-147EFB)

## Overview

Oxford Word Skills is a desktop study tool that helps English language learners practice and track their progress through a large vocabulary organized into **12 modules** and **80 thematic units**. It includes over **11,800 words** with IPA pronunciation, definitions, synonyms, antonyms, and example sentences — all bundled in the app.

## Features

### Six Exercise Modes

| Exercise | Description |
|---|---|
| **Flashcards** | Swipe through shuffled word cards with definitions, examples, and pronunciation |
| **Word → Definition Quiz** | See the word, choose the correct definition from 4 options |
| **Definition → Word Quiz** | See the definition, choose the correct word from 4 options |
| **Listening & Spelling** | Hear British English pronunciation, type the word you hear |
| **Synonym Match** | Match words with their synonyms in a two-column layout |
| **Categorization** | Sort words into their correct unit categories |

### Vocabulary Browser

- Full word table with word, definition, unit assignment, and learned toggle
- Per-unit views with progress header and quick exercise launch
- Search across all vocabulary

### Progress Tracking

- Mark individual words as learned
- Per-unit and per-module progress bars
- Overall statistics dashboard (total, learned, remaining, percentage)
- Reset progress per unit or globally
- Progress persists across sessions via UserDefaults

### Additional

- British English text-to-speech for pronunciation
- IPA phonetic transcription for every word
- Zero third-party dependencies — Apple frameworks only

## Requirements

- **macOS 26.0** (Tahoe) or later
- **Xcode 26** or later
- **Swift 5.0**

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/thanhqng1510/Oxford-word-skills.git
   ```
2. Open the project:
   ```bash
   open OxfordWordSkills.xcodeproj
   ```
3. Select the **OxfordWordSkills** scheme and a macOS destination.
4. Build and run (**Cmd + R**).

## Project Structure

```
OxfordWordSkills/
├── OxfordWordSkillsApp.swift       # App entry point
├── OxfordWordSkills.entitlements   # Sandbox + network entitlements
├── Models/
│   └── DataModels.swift            # Word, Unit, Module, ExerciseType, etc.
├── ViewModels/
│   └── ContentViewModel.swift      # Central @Observable state
├── Views/
│   ├── ContentView.swift           # Root NavigationSplitView
│   ├── SidebarView.swift           # Module/unit navigation sidebar
│   ├── VocabularyListView.swift    # Word table + unit detail view
│   ├── FlashcardView.swift         # Flashcard exercise
│   ├── QuizView.swift              # Multiple-choice quiz
│   ├── FillInBlankView.swift       # Listening & spelling exercise
│   ├── MatchingView.swift          # Synonym matching exercise
│   ├── CategorizationView.swift    # Word categorization exercise
│   ├── ExerciseContainerView.swift # Exercise type router
│   └── ProgressDashboardView.swift # Statistics overview
├── Utilities/
│   ├── ContentParser.swift         # XML/JSON data pipeline
│   └── SpeechService.swift         # Text-to-speech (British English)
├── Resources/
│   ├── settings.xml                # Module/unit/section structure
│   ├── extrawordlist.xml           # Vocabulary with IPA pronunciation
│   └── definitions.json            # Definitions, synonyms, antonyms
└── OxfordWordSkills.xcodeproj/
```

## Architecture

### Single ViewModel

All app state flows through one `ContentViewModel` (using `@Observable`) owned by `ContentView`. Views receive it via init and use `@Bindable` for two-way binding. No child-to-child communication or `@EnvironmentObject`.

### Enum-Driven Navigation

A `NavigationTarget` enum drives the detail view through a `switch` statement — no `NavigationLink` or `NavigationStack`. The four targets are: `.allWords`, `.unit(Int)`, `.exercise(ExerciseType, Int?)`, and `.progress`.

### Data Pipeline

`ContentParser.buildModules()` orchestrates the full data pipeline:
1. Parse `settings.xml` → module/unit hierarchy
2. Parse `extrawordlist.xml` → word list with IPA and unit assignments
3. Parse `definitions.json` → rich definitions
4. Merge and group into `[Module] → [Unit] → [Word]`

### Progress Persistence

Learned word IDs are stored as a `Set<String>` serialized to UserDefaults. The word key format is `"word|sorted,unit,numbers"`.

## Data Sources

| File | Format | Content |
|---|---|---|
| `settings.xml` | XML | 12 modules, 80 units with titles and section metadata |
| `extrawordlist.xml` | XML | ~11,800 vocabulary words with IPA pronunciation |
| `definitions.json` | JSON | Definitions, parts of speech, synonyms, antonyms |

## License

<!-- TODO: Add license -->
