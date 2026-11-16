#!/usr/bin/env python3
"""Validate the catalog and story sources. Optionally check locally built ZIPs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_BASE = "https://raw.githubusercontent.com/negk01/voxlit-content/main"
RELEASE_BASE = "https://github.com/negk01/voxlit-content/releases/download"
METADATA_KEYS = ("title", "level", "author", "description", "genre", "is_premium")
QUIZ_TYPES = ("translation", "matching", "comprehension")
LEXICON_FIELDS = {"ipa", "pos", "translationEs"}
COMMON_LEXICON_SECTIONS = {"articles", "pronouns", "connectors", "prepositions", "other"}


def package_name(entry: dict) -> str:
    story_id, version = entry["id"], entry["version"]
    if not isinstance(story_id, str) or re.fullmatch(r"story_\d{3}", story_id) is None:
        raise ValueError("Invalid catalog story ID")
    if type(version) is not int or version < 1:
        raise ValueError(f"{story_id}: version must be a positive integer")
    return f"{story_id}_v{version}.zip"


def release_url(entry: dict) -> str:
    name = package_name(entry)
    tag = entry["id"]
    return f"{RELEASE_BASE}/{tag}/{name}"


def story_files(story_dir: Path) -> dict[str, Path]:
    if story_dir.is_symlink() or not story_dir.is_dir():
        raise ValueError(f"Invalid story directory: {story_dir}")
    files = {}
    for path in sorted(story_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Story contains a symbolic link: {path}")
        if path.is_file():
            files[path.relative_to(story_dir).as_posix()] = path
    return files


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_json_object)
    except ValueError as error:
        raise ValueError(f"{path.name}: {error}") from error


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def validate_lexicon(path: Path, *, common: bool = False) -> None:
    data = read_json(path)
    try:
        if common:
            require(isinstance(data, dict) and data.keys() == COMMON_LEXICON_SECTIONS, "Invalid common lexicon sections")
        forms = set()
        for entries in data.values() if common else (data,):
            require(isinstance(entries, dict), "Lexicon must be an object")
            for form, entry in entries.items():
                require_string(form, "Lexicon form")
                key = form.strip().lower()
                require(key not in forms, f"Duplicate lexicon form: {form!r}")
                forms.add(key)
                require(isinstance(entry, dict) and bool(entry) and entry.keys() <= LEXICON_FIELDS, f"Invalid lexicon entry: {form!r}")
                for field, value in entry.items():
                    require_string(value, f"Lexicon field {form!r}.{field}")
    except ValueError as error:
        raise ValueError(f"{path.name}: {error}") from error


def valid_relative(name: object) -> str:
    require(isinstance(name, str) and bool(name.strip()), "Empty or invalid file path")
    require(not name.startswith(("/", "\\")) and "\\" not in name, f"Unsafe path: {name}")
    require(re.match(r"^[A-Za-z]:", name) is None, f"Absolute path: {name}")
    require(all(part not in ("", ".", "..") for part in name.split("/")), f"Unsafe path: {name}")
    return name


def require_string(value: object, label: str) -> None:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonempty string")


def require_integer(value: object, label: str, minimum: int = 0) -> None:
    require(type(value) is int and value >= minimum, f"{label} must be an integer >= {minimum}")


def check_media(story_dir: Path, reference: object) -> None:
    if reference is None:
        return
    require(isinstance(reference, str), "Media reference must be a string or null")
    if not reference.strip():
        return
    path = story_dir / valid_relative(reference)
    require(path.resolve().is_relative_to(story_dir.resolve()), f"Media escapes story directory: {reference}")
    require(path.is_file() and path.stat().st_size > 0, f"Missing or empty media: {reference}")


def validate_quizzes(quizzes: object, paragraph_ids: list[int]) -> None:
    require(isinstance(quizzes, list), "quizzes must be an array")
    quiz_ids = set()
    for quiz in quizzes:
        require(isinstance(quiz, dict), "Quiz must be an object")
        require_string(quiz.get("id"), "Quiz id")
        require(quiz["id"] not in quiz_ids, f"Duplicate quiz ID: {quiz['id']}")
        quiz_ids.add(quiz["id"])
        require_integer(quiz.get("after_paragraph_id"), "Quiz paragraph reference")
        require(quiz["after_paragraph_id"] in paragraph_ids, f"Quiz {quiz['id']} references an unknown paragraph")
        quiz_type = quiz.get("type")
        require(quiz_type in QUIZ_TYPES, f"Unsupported quiz type: {quiz_type}")
        if quiz_type == "matching":
            pairs = quiz.get("pairs")
            require(isinstance(pairs, list) and bool(pairs), "Matching quiz requires pairs")
            labels_by_language = {"en": set(), "es": set()}
            for pair in pairs:
                require(isinstance(pair, dict), "Matching pair must be an object")
                for language, labels in labels_by_language.items():
                    label = pair.get(language)
                    require_string(label, f"Matching pair {language}")
                    require(label not in labels, f"Matching quiz {quiz['id']} repeats {language} label: {label!r}")
                    labels.add(label)
        else:
            options = quiz.get("options")
            require(isinstance(options, list) and len(options) >= 2, "Quiz requires at least two options")
            for option in options:
                require_string(option, "Quiz option")
            require(len(set(options)) == len(options), "Quiz options must be unique")
            if quiz_type == "translation":
                require_string(quiz.get("word"), "Translation word")
                require_string(quiz.get("correct"), "Translation correct answer")
                require(quiz["correct"] in options, "Translation answer is absent from options")
            else:
                require_string(quiz.get("question"), "Comprehension question")
                require_integer(quiz.get("correct_index"), "Comprehension correct_index")
                require(quiz["correct_index"] < len(options), "Comprehension answer index is outside options")


def validate_optional_json(story_dir: Path, paragraph_ids: list[int]) -> None:
    for name in ("dictionary.json", "words.json"):
        require(not (story_dir / name).exists(), f"Legacy lexicon file remains in sources: {name}")
    lexicon = story_dir / "lexicon.json"
    if lexicon.exists():
        validate_lexicon(lexicon)
    timestamps = story_dir / "timestamps.json"
    if timestamps.exists():
        data = read_json(timestamps)
        require(isinstance(data, list), "timestamps.json must be an array")
        for timestamp in data:
            require(isinstance(timestamp, dict), "Timestamp must be an object")
            for key in ("p", "w", "ms"):
                require_integer(timestamp.get(key), f"Timestamp {key}")
            require(timestamp["p"] in paragraph_ids, "Timestamp references an unknown paragraph")
            require(isinstance(timestamp.get("t"), str), "Timestamp t must be a string")


def validate_story(story_dir: Path, entry: dict) -> None:
    story_files(story_dir)
    story = read_json(story_dir / "story.json")
    require(isinstance(story, dict), "story.json must be an object")
    require(story.get("id") == story_dir.name, "story.json ID does not match its directory")
    require(story.get("id") == entry["id"], "story.json ID does not match catalog")
    for key in METADATA_KEYS:
        require(key not in story, f"Metadata belongs in catalog.json, not story.json: {key}")
    paragraphs = story.get("paragraphs", [])
    require(isinstance(paragraphs, list) and bool(paragraphs), "Story requires paragraphs")
    ids = []
    for paragraph in paragraphs:
        require(isinstance(paragraph, dict), "Paragraph must be an object")
        require_integer(paragraph.get("id"), "Paragraph ID")
        require(isinstance(paragraph.get("text"), str), "Paragraph text must be a string")
        ids.append(paragraph["id"])
        if paragraph.get("start_ms") is not None:
            require_integer(paragraph["start_ms"], "Paragraph start_ms")
        check_media(story_dir, paragraph.get("audio_file"))
        check_media(story_dir, paragraph.get("scene_image"))
    require(ids == list(range(len(ids))), "Paragraph IDs must be continuous and ordered from zero")
    require(any(paragraph["text"].strip() for paragraph in paragraphs), "Story has no readable paragraphs")
    validate_quizzes(story.get("quizzes", []), ids)
    check_media(story_dir, "cover.webp")
    check_media(story_dir, story.get("header_scene"))
    check_media(story_dir, story.get("audio_file"))
    validate_optional_json(story_dir, ids)
    print(f"[OK] {story_dir.name}: {len(ids)} paragraphs, {len(story.get('quizzes', []))} quizzes")


def validate_catalog(root: Path) -> list[dict]:
    catalog = read_json(root / "catalog.json")
    require(isinstance(catalog, dict), "catalog.json must be an object")
    entries = catalog.get("downloadable_stories")
    require(isinstance(entries, list) and bool(entries), "Catalog requires downloadable_stories")
    ids = set()
    for entry in entries:
        require(isinstance(entry, dict), "Catalog entry must be an object")
        expected_zip_url = release_url(entry)
        require(entry["id"] not in ids, f"Duplicate catalog ID: {entry['id']}")
        ids.add(entry["id"])
        for field in ("id", "title", "level", "author", "description"):
            require_string(entry.get(field), f"Catalog {field}")
        require(type(entry.get("is_premium")) is bool, "is_premium must be a boolean")
        require(isinstance(entry.get("genre"), list), "genre must be an array")
        for genre in entry["genre"]:
            require_string(genre, "Genre")
        require_integer(entry.get("zip_size_bytes"), "ZIP size", minimum=1)
        require(isinstance(entry.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None, "Invalid SHA256")
        require(entry.get("zip_url") == expected_zip_url, "ZIP URL does not match versioned package")
        require(entry.get("cover_url") == f"{RAW_BASE}/{entry['id']}/cover.webp", "Cover URL does not match story directory")
    directories = {path.name for path in root.glob("story_*") if path.is_dir()}
    require(directories == ids, f"Catalog/directory mismatch: catalog={sorted(ids)}, disk={sorted(directories)}")
    return entries


def validate_package(root: Path, entry: dict) -> None:
    archive_path = root / "packages" / package_name(entry)
    data = archive_path.read_bytes()
    require(len(data) == entry["zip_size_bytes"], "ZIP byte size differs from catalog")
    require(hashlib.sha256(data).hexdigest() == entry["sha256"], "ZIP SHA256 differs from catalog")
    sources = story_files(root / entry["id"])
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        require(bool(infos), "ZIP is empty")
        names = [valid_relative(info.filename) for info in infos]
        require(len(names) == len(set(names)), "ZIP contains duplicate paths")
        require(set(names) == set(sources), "ZIP contents differ from story directory")
        require(sum(info.file_size for info in infos) <= max(len(data) * 10, 50 * 1024 * 1024), "ZIP exceeds app extraction limit")
        require(archive.testzip() is None, "ZIP contains a damaged entry")
        for info in infos:
            require(not info.is_dir(), "ZIP must contain files directly, without a story wrapper directory")
            require(archive.read(info) == sources[info.filename].read_bytes(), f"ZIP payload differs: {info.filename}")
    print(f"[OK] {archive_path.name}: integrity and payload match")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--sources-only", action="store_true", help="Validate only the catalog and story sources (default).")
    modes.add_argument("--check-packages", action="store_true", help="Also check ZIPs in packages/ against the catalog and sources.")
    args = parser.parse_args()
    errors = 0
    try:
        entries = validate_catalog(REPO_ROOT)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"[ERROR] Catalog: {error}")
        sys.exit(1)
    for entry in entries:
        try:
            validate_story(REPO_ROOT / entry["id"], entry)
            if args.check_packages:
                validate_package(REPO_ROOT, entry)
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            print(f"[ERROR] {entry['id']}: {error}")
            errors += 1
    if errors:
        sys.exit(1)
    if args.check_packages:
        print(f"[OK] Catalog, sources and all {len(entries)} local ZIPs are valid")
    else:
        print(f"[OK] Catalog and all {len(entries)} story sources are valid")


if __name__ == "__main__":
    main()
