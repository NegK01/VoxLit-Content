#!/usr/bin/env python3
"""
Content and Story Validator for VoxLit-Content.
Executed by GitHub Actions on every Push and Pull Request.

VALIDATION RULES:
1. catalog.json: Every object in 'downloadable_stories' must contain 12 mandatory properties:
   id, title, level, author, description, genre, is_premium, cover_url, version, zip_url, zip_size_bytes, sha256.
   - UNIQUENESS RULE: No story 'id' can be duplicated in catalog.json.
2. Catalog vs Disk Comparison (X/Y):
   - X = Stories registered in catalog.json.
   - Y = story_XXX directories present in repository root.
   - Unregistered directories are treated as 'Work In Progress / Draft' (non-blocking WARN/INFO).
3. Files in story_XXX directory:
   - Mandatory (ERROR if missing): cover.webp, story.json, and the header_scene (e.g., scene_01.webp).
   - Audio Pair: audio.opus and timestamps.json are optional, but IF ONE EXISTS, THE OTHER MUST ALSO EXIST (ERROR if only one is present).
   - Optional: dictionary.json.
4. Mandatory properties in story.json:
   id, title, level, description, genre, is_premium, header_scene, audio_file, paragraphs, quizzes.
   - ID MATCHING RULE: Internal 'id' in story.json MUST match directory name.
"""

import json
import sys
from pathlib import Path

# Configure stdout for UTF-8 compatibility on Windows and Linux runners
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Root directory of VoxLit-Content repository
REPO_ROOT = Path(__file__).resolve().parent.parent

# Mandatory properties in catalog.json objects
MANDATORY_CATALOG_KEYS = [
    "id",
    "title",
    "level",
    "author",
    "description",
    "genre",
    "is_premium",
    "cover_url",
    "version",
    "zip_url",
    "zip_size_bytes",
    "sha256",
]

# Mandatory properties in story.json root
MANDATORY_STORY_JSON_KEYS = [
    "id",
    "title",
    "level",
    "description",
    "genre",
    "is_premium",
    "header_scene",
    "audio_file",
    "paragraphs",
    "quizzes",
]


def print_separator(title: str = "", tag: str = "STORY"):
    divider = "-" * 65
    if title:
        print(f"\n{divider}\n[{tag}] {title}\n{divider}")
    else:
        print(f"\n{divider}")


def log_success(msg: str):
    print(f"  [OK]    {msg}")


def log_error(msg: str):
    print(f"  [ERROR] {msg}")


def log_warning(msg: str):
    print(f"  [WARN]  {msg}")


def log_info(msg: str):
    print(f"  [INFO]  {msg}")


def validate_catalog() -> tuple[bool, list[dict], set[str]]:
    print("=" * 65)
    print("CATALOG AUDIT (catalog.json)")
    print("=" * 65)

    catalog_file = REPO_ROOT / "catalog.json"
    if not catalog_file.exists():
        log_error("catalog.json file does not exist in repository root.")
        return False, [], set()

    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
    except json.JSONDecodeError as e:
        log_error(f"catalog.json contains invalid JSON syntax: {e}")
        return False, [], set()

    if isinstance(catalog_data, dict):
        if "downloadable_stories" in catalog_data:
            stories = catalog_data["downloadable_stories"]
        elif "stories" in catalog_data:
            stories = catalog_data["stories"]
        else:
            log_error("catalog.json must contain 'downloadable_stories' or 'stories' key.")
            return False, [], set()
    elif isinstance(catalog_data, list):
        stories = catalog_data
    else:
        log_error("catalog.json must be a JSON array or object.")
        return False, [], set()

    catalog_story_ids = set()
    errors = 0

    for idx, story in enumerate(stories):
        story_id = story.get("id", f"Entry #{idx + 1}")

        # Duplicate ID check
        if "id" in story and isinstance(story["id"], str):
            if story["id"] in catalog_story_ids:
                log_error(f"Catalog: Duplicate story ID '{story['id']}' found in catalog.json.")
                errors += 1
            else:
                catalog_story_ids.add(story["id"])

        # Mandatory fields check
        for key in MANDATORY_CATALOG_KEYS:
            if key not in story or story[key] is None:
                log_error(f"Catalog [{story_id}]: Missing mandatory property '{key}'.")
                errors += 1

        # Type checks
        if "genre" in story and not isinstance(story["genre"], list):
            log_error(f"Catalog [{story_id}]: 'genre' must be an array/list.")
            errors += 1
        if "is_premium" in story and not isinstance(story["is_premium"], bool):
            log_error(f"Catalog [{story_id}]: 'is_premium' must be a boolean.")
            errors += 1
        if "version" in story and not isinstance(story["version"], int):
            log_error(f"Catalog [{story_id}]: 'version' must be an integer.")
            errors += 1
        if "zip_size_bytes" in story and not isinstance(story["zip_size_bytes"], int):
            log_error(f"Catalog [{story_id}]: 'zip_size_bytes' must be an integer.")
            errors += 1

    if errors == 0:
        log_success(f"catalog.json loaded successfully ({len(catalog_story_ids)} unique & valid IDs).")

    return errors == 0, stories, catalog_story_ids


def validate_quizzes(story_id: str, quizzes: list) -> int:
    errors = 0
    if not isinstance(quizzes, list):
        log_error("story.json: 'quizzes' must be an array/list.")
        return 1

    for q_idx, quiz in enumerate(quizzes):
        if not isinstance(quiz, dict):
            log_error(f"story.json: Quiz #{q_idx + 1} is not a valid JSON object.")
            errors += 1
            continue

        q_type = quiz.get("type")
        if not q_type:
            log_error(f"story.json: Quiz #{q_idx + 1} is missing 'type' field.")
            errors += 1
            continue

        if "id" not in quiz or "after_paragraph_id" not in quiz:
            log_error(f"story.json: Quiz #{q_idx + 1} ({q_type}) must contain 'id' and 'after_paragraph_id'.")
            errors += 1

        # Quiz type schema checks
        if q_type == "translation":
            req_fields = ["word", "correct", "options"]
            for field in req_fields:
                if field not in quiz:
                    log_error(f"story.json: Translation quiz ({quiz.get('id')}) missing field '{field}'.")
                    errors += 1
            if "options" in quiz and not isinstance(quiz["options"], list):
                log_error(f"story.json: Translation quiz ({quiz.get('id')}) 'options' must be an array.")
                errors += 1

        elif q_type == "matching":
            if "pairs" not in quiz or not isinstance(quiz["pairs"], list):
                log_error(f"story.json: Matching quiz ({quiz.get('id')}) requires a 'pairs' array.")
                errors += 1
            else:
                for p_idx, pair in enumerate(quiz["pairs"]):
                    if not isinstance(pair, dict) or "en" not in pair or "es" not in pair:
                        log_error(f"story.json: Matching quiz ({quiz.get('id')}) pair #{p_idx + 1} must contain 'en' and 'es'.")
                        errors += 1

        elif q_type == "comprehension":
            req_fields = ["question", "options", "correct_index"]
            for field in req_fields:
                if field not in quiz:
                    log_error(f"story.json: Comprehension quiz ({quiz.get('id')}) missing field '{field}'.")
                    errors += 1
            if "options" in quiz and not isinstance(quiz["options"], list):
                log_error(f"story.json: Comprehension quiz ({quiz.get('id')}) 'options' must be an array.")
                errors += 1
            if "correct_index" in quiz and not isinstance(quiz["correct_index"], int):
                log_error(f"story.json: Comprehension quiz ({quiz.get('id')}) 'correct_index' must be an integer.")
                errors += 1
        else:
            log_warning(f"story.json: Quiz #{q_idx + 1} has unknown type '{q_type}'.")

    return errors


def validate_story_directory(story_dir: Path, is_in_catalog: bool) -> bool:
    story_id = story_dir.name
    tag = "REGISTERED STORY" if is_in_catalog else "DRAFT / WORK IN PROGRESS"
    print_separator(story_id, tag=tag)

    if not is_in_catalog:
        log_warning("This story directory exists on disk but is NOT registered in catalog.json yet.")

    errors = 0
    story_json_path = story_dir / "story.json"
    header_scene_file = "scene_01.webp"

    # 1. Validate mandatory existence of story.json
    if not story_json_path.exists():
        log_error("Missing mandatory file 'story.json'.")
        return False
    elif story_json_path.stat().st_size == 0:
        log_error("File 'story.json' is empty (0 bytes).")
        return False

    # Read story.json for schema data
    try:
        with open(story_json_path, "r", encoding="utf-8") as f:
            story_data = json.load(f)

        header_scene_file = story_data.get("header_scene", "scene_01.webp")

        # Internal ID matching folder name check
        internal_id = story_data.get("id")
        if internal_id != story_id:
            log_error(f"story.json: Internal ID ('{internal_id}') does NOT match directory name ('{story_id}').")
            errors += 1

        # Root mandatory keys check
        for key in MANDATORY_STORY_JSON_KEYS:
            if key not in story_data or story_data[key] is None:
                log_error(f"story.json: Missing mandatory property '{key}'.")
                errors += 1

        # Paragraphs check
        paragraphs = story_data.get("paragraphs")
        if not isinstance(paragraphs, list) or len(paragraphs) == 0:
            log_error("story.json: 'paragraphs' must be a list containing at least 1 paragraph.")
            errors += 1

        # Quizzes check
        quizzes = story_data.get("quizzes", [])
        errors += validate_quizzes(story_id, quizzes)

    except json.JSONDecodeError as e:
        log_error(f"story.json: Invalid JSON syntax: {e}")
        return False

    # 2. Validate mandatory image assets (cover.webp and header_scene)
    cover_path = story_dir / "cover.webp"
    if not cover_path.exists():
        log_error("Missing mandatory image 'cover.webp'.")
        errors += 1
    elif cover_path.stat().st_size == 0:
        log_error("Image 'cover.webp' is empty (0 bytes).")
        errors += 1

    scene_path = story_dir / header_scene_file
    if not scene_path.exists():
        log_error(f"Missing mandatory scene image '{header_scene_file}'.")
        errors += 1
    elif scene_path.stat().st_size == 0:
        log_error(f"Scene image '{header_scene_file}' is empty (0 bytes).")
        errors += 1

    # 3. Audio Pair Rule (audio.opus <-> timestamps.json)
    audio_path = story_dir / "audio.opus"
    timestamps_path = story_dir / "timestamps.json"

    has_audio = audio_path.exists() and audio_path.stat().st_size > 0
    has_timestamps = timestamps_path.exists() and timestamps_path.stat().st_size > 0

    if has_audio and not has_timestamps:
        log_error("Contains 'audio.opus' but is missing mandatory pair 'timestamps.json'.")
        errors += 1
    elif has_timestamps and not has_audio:
        log_error("Contains 'timestamps.json' but is missing mandatory pair 'audio.opus'.")
        errors += 1
    elif not has_audio and not has_timestamps:
        log_warning("Story has no audio (does not contain audio.opus or timestamps.json).")

    # 4. Optional dictionary.json check
    dict_path = story_dir / "dictionary.json"
    if dict_path.exists():
        if dict_path.stat().st_size == 0:
            log_error("'dictionary.json' is empty (0 bytes).")
            errors += 1
        else:
            try:
                with open(dict_path, "r", encoding="utf-8") as f:
                    dict_data = json.load(f)
                if not isinstance(dict_data, (dict, list)):
                    log_error("dictionary.json: Must be a valid JSON object or list.")
                    errors += 1
            except json.JSONDecodeError as e:
                log_error(f"dictionary.json: Invalid JSON syntax: {e}")
                errors += 1

    if errors == 0:
        log_success("All files and schemas are valid.")

    return errors == 0


def main():
    catalog_ok, catalog_stories, catalog_ids = validate_catalog()
    if not catalog_ok:
        log_error("catalog.json validation failed.")
        sys.exit(1)

    story_dirs = [d for d in REPO_ROOT.iterdir() if d.is_dir() and d.name.startswith("story_")]
    x_catalog = len(catalog_ids)
    y_disk = len(story_dirs)

    log_info(f"Stories Overview: ({x_catalog}/{y_disk}) -> {x_catalog} registered in catalog / {y_disk} directories on disk.")

    total_errors = 0
    for story_dir in sorted(story_dirs):
        is_in_catalog = story_dir.name in catalog_ids
        if not validate_story_directory(story_dir, is_in_catalog=is_in_catalog):
            total_errors += 1

    print("=" * 65)
    print("FINAL AUDIT SUMMARY")
    print("=" * 65)
    print(f"  [INFO]  Metrics: ({x_catalog}/{y_disk}) catalog stories vs disk directories.")
    if total_errors > 0:
        print(f"  [ERROR] Audit failed for {total_errors} story directory/directories.")
        sys.exit(1)
    else:
        print("  [OK] All stories and catalog are 100% valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()
