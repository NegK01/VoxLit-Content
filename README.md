# VoxLit Content

This repository hosts the catalog and downloadable books for **VoxLit**.

## Repository contents

```text
VoxLit-Content/
├── catalog.json
└── story_001/
    ├── story.json
    ├── cover.webp
    ├── scene_01.webp
    └── lexicon.json
```

| File | Purpose |
| --- | --- |
| `catalog.json` | Book titles, authors, reading levels, descriptions, and links to covers and downloadable editions. |
| `story.json` | Story text, exercises, and references to illustrations and audio. |
| `cover.webp`, `scene_*.webp` | Library cover art and illustrations shown in the reader. |
| `lexicon.json` | Optional Spanish translations, IPA, and parts of speech for exact words and expressions. |
| `audio.opus`, `timestamps.json` | Narration and word timings for synchronized highlighting, when available. |

## How VoxLit uses this repository

VoxLit can add books to its library without an app update.

```text
Open VoxLit
  ├── Load the saved catalog or the copy included with the app
  └── Check for an updated catalog in the background

Browse the library
  └── Load covers as needed

Download a book
  └── Fetch its versioned ZIP from GitHub Releases
       └── Install the book for offline reading
```

## About the content

The library includes complete adaptations of classic short stories for different English reading levels. The exercises draw on each story's vocabulary and events.

## VoxLit

VoxLit is an Android app for Spanish speakers learning English through reading. Tap a word to see its Spanish translation, IPA pronunciation, and part of speech when available. Books with narration can highlight the text in sync with the audio.

The app is in development for release on Google Play.
