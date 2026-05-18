# VoxLit Content

This is the story library for **VoxLit** — an Android app for learning English through active reading.

Each story is a short, level-tagged chapter (~600–900 words) in English, written to feel natural and engaging rather than like a language textbook. The app narrates each paragraph with a human-quality voice, highlights every word as it plays, and lets you tap any word for a Spanish translation and pronunciation.

**The app is currently in development and coming soon to Google Play.**

---

## What's in here

```
voxlit-content/
├── catalog.json          ← index of all downloadable stories
├── story_004/            ← The Clockmaker's Secret (B1)
├── story_005/            ← The Last Train (A2)
├── story_006/            ← Sunday Soup (A2)
├── story_007/            ← The Night Shift (B1)
├── story_008/            ← Salt and Sea (A2)
├── story_009/            ← The Translator (B1)
├── story_010/            ← Footprints in the Snow (A2)
├── story_011/            ← The Inheritance (B1)
├── story_012/            ← The Repair Shop (A2)
└── story_013/            ← Red Line (B1)
```

Each story folder contains:
- `story.json` — paragraphs, metadata, audio file references
- `dictionary.json` — word list with Spanish translations used by the in-app tap-to-translate feature
- `cover.webp` — library card image (720×960)
- `scene_XX.webp` — in-reader illustrations (1280×640)
- `p00.opus`, `p01.opus`... — narration audio, one file per paragraph

The app fetches `catalog.json` on every session and downloads individual story ZIPs from GitHub Releases on demand — no APK update needed to add new stories.

---

## Story levels

| Level | Description |
|-------|-------------|
| A2 | Elementary — short sentences, common vocabulary, clear plot |
| B1 | Intermediate — more nuanced language, richer vocabulary, some complexity |

Levels follow the CEFR scale used by most language learning platforms.

---

## How the app uses this repo

```
App launch
  └─ fetches catalog.json
       ├─ success → shows available stories, marks new ones
       └─ fail    → uses last cached version

User taps Download on a story
  └─ fetches story_XXX.zip from GitHub Releases
       └─ extracts to device storage → story available offline
```

Stories bundled inside the APK (story_001 to story_003) are not in this repo — they ship with the app.

---

## About the content

Stories are written with AI assistance and reviewed by a human editor for tone, pacing, and pedagogical fit. Each chapter is designed to work as a standalone reading unit while leaving a hook for the next chapter.

---

## VoxLit

VoxLit is an Android app for Spanish speakers learning English. It pairs short, level-appropriate stories with synchronized narration and instant word translation — the kind of tool that makes 10 minutes of daily reading actually feel like progress.

**Coming soon to Google Play.**