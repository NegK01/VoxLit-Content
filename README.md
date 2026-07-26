# VoxLit Content

This is the story library for **VoxLit** — an Android app for learning English through active reading.

Each story is a short, level-tagged chapter (~600–900 words) in English, written to feel natural and engaging rather than like a language textbook. The app narrates each paragraph with a human-quality voice, highlights every word as it plays, and lets you tap any word for a Spanish translation and pronunciation.

**The app is currently in development and coming soon to Google Play.**

---

## What's in here

```
voxlit-content/
├── catalog.json          ← index of all downloadable stories
├── story_005/            ← The Wrong Address (A2)
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
- `audio.opus` — full narrated audio for the entire chapter
- `cover.webp` — library card image (720×960)
- `dictionary.json` — word list with Spanish translations used by the in-app tap-to-translate feature
- `scene_XX.webp` — in-reader illustrations (1280×640)
- `story.json` — paragraphs, metadata, audio file references
- `timestamps.json` — word-level timing data for synchronized highlighting

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

VoxLit uses a hybrid architecture to keep the app installation small while allowing the library to grow indefinitely without requiring updates from the Google Play Store.

**The Hybrid Catalog**
To make sure users never see an empty screen, the app uses a smart fallback system:
1. **Live Catalog**: When the app opens with internet access, it quietly downloads `catalog.json` from this repository and saves it locally.
2. **Offline Fallback**: If it's the user's very first time opening the app and they have no internet, VoxLit uses a pre-packaged, basic catalog included in the app itself.

**User Flow**
```text
App launch (Online)
  └─ Fetches catalog.json in the background
       ├─ If there are updates → Refreshes the library to show new stories
       └─ If nothing changed → Uses the saved catalog to save data

User browses the library
  └─ Cover art and background images for remote books are downloaded on-the-fly.

User taps "Download" on a story
  └─ Fetches story_XXX.zip from GitHub Releases
       └─ Extracts everything to the device → Story becomes permanently available offline
```

**Offline Resilience**
Once the app has fetched the catalog at least once, the user will always be able to browse the titles, descriptions, and levels of all available stories—even if they lose their internet connection. The core reading experience is designed to never break.

*(Note: Stories 001 to 004 are fully bundled inside the app to guarantee a rich Day-1 experience even without internet, so they are not tracked in this repository).*

---

## About the content

Stories are written with AI assistance and reviewed by a human editor for tone, pacing, and pedagogical fit. Each chapter is designed to work as a standalone reading unit while leaving a hook for the next chapter.

---

## VoxLit

VoxLit is an Android app for Spanish speakers learning English. It pairs short, level-appropriate stories with synchronized narration and instant word translation — the kind of tool that makes 10 minutes of daily reading actually feel like progress.

**Coming soon to Google Play.**