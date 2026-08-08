#!/usr/bin/env python3
"""
Validador de Contenido y Historias para VoxLit-Content.
Este script es ejecutado por GitHub Actions en cada Push o Pull Request.

REGLAS DE VALIDACIÓN:
1. catalog.json: Cada objeto en 'downloadable_stories' debe contener las 12 propiedades obligatorias:
    id, title, level, author, description, genre, is_premium, cover_url, version, zip_url, zip_size_bytes, sha256.
    - REGLA DE UNICIDAD: Ningún 'id' de historia puede estar duplicado en catalog.json.
2. Comparación Catálogo vs Disco (X/Y):
    - X = Historias registradas en catalog.json.
    - Y = Carpetas story_XXX presentes en el repositorio.
    - Las carpetas no registradas en catalog.json se consideran 'En Desarrollo / Borrador' (WARN/INFO no bloqueante).
3. Archivos en carpeta story_XXX:
    - Obligatorios (ERROR si falta): cover.webp, story.json, y el header_scene (ej: scene_01.webp).
    - Opcionales / Par de Audio: audio.opus y timestamps.json son opcionales, pero SI EXISTE UNO, EL OTRO TAMBIÉN DEBE EXISTIR (ERROR si solo hay uno).
    - Opcionales: dictionary.json.
4. Propiedades obligatorias en story.json:
    id, title, level, description, genre, is_premium, header_scene, audio_file, paragraphs, quizzes.
    - REGLA DE COINCIDENCIA DE ID: El 'id' dentro de story.json DEBE coincidir con el nombre de la carpeta.
"""

import json
import sys
from pathlib import Path

# Configurar stdout para soportar caracteres UTF-8 en consolas Windows y Linux
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Directorio raíz del repositorio VoxLit-Content
REPO_ROOT = Path(__file__).resolve().parent.parent

# Propiedades obligatorias exactas en cada objeto de catalog.json
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

# Propiedades obligatorias exactas en la raíz de story.json
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


def print_separator(title: str = "", tag: str = "HISTORIA"):
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
    print("AUDITORIA DE CATALOGO (catalog.json)")
    print("=" * 65)

    catalog_file = REPO_ROOT / "catalog.json"
    if not catalog_file.exists():
        log_error("El archivo catalog.json no existe en la raíz del repositorio.")
        return False, [], set()

    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
    except json.JSONDecodeError as e:
        log_error(f"catalog.json contiene sintaxis JSON inválida: {e}")
        return False, [], set()

    if isinstance(catalog_data, dict):
        if "downloadable_stories" in catalog_data:
            stories = catalog_data["downloadable_stories"]
        elif "stories" in catalog_data:
            stories = catalog_data["stories"]
        else:
            log_error("catalog.json debe contener la clave 'downloadable_stories' o 'stories'.")
            return False, [], set()
    elif isinstance(catalog_data, list):
        stories = catalog_data
    else:
        log_error("catalog.json debe ser una lista o un objeto JSON.")
        return False, [], set()

    catalog_story_ids = set()
    errors = 0

    for idx, story in enumerate(stories):
        story_id = story.get("id", f"Entrada #{idx + 1}")

        # Validación de duplicados de ID
        if "id" in story and isinstance(story["id"], str):
            if story["id"] in catalog_story_ids:
                log_error(f"Catálogo: El ID de historia '{story['id']}' se encuentra DUPLICADO en catalog.json.")
                errors += 1
            else:
                catalog_story_ids.add(story["id"])

        # Validación de campos obligatorios
        for key in MANDATORY_CATALOG_KEYS:
            if key not in story or story[key] is None:
                log_error(f"Catálogo [{story_id}]: Carece de la propiedad obligatoria '{key}'.")
                errors += 1

        # Validaciones de tipo
        if "genre" in story and not isinstance(story["genre"], list):
            log_error(f"Catálogo [{story_id}]: 'genre' debe ser un array/lista.")
            errors += 1
        if "is_premium" in story and not isinstance(story["is_premium"], bool):
            log_error(f"Catálogo [{story_id}]: 'is_premium' debe ser un booleano (true/false).")
            errors += 1
        if "version" in story and not isinstance(story["version"], int):
            log_error(f"Catálogo [{story_id}]: 'version' debe ser un entero.")
            errors += 1
        if "zip_size_bytes" in story and not isinstance(story["zip_size_bytes"], int):
            log_error(f"Catálogo [{story_id}]: 'zip_size_bytes' debe ser un entero.")
            errors += 1

    if errors == 0:
        log_success(f"catalog.json cargado correctamente ({len(catalog_story_ids)} IDs únicos e íntegros).")

    return errors == 0, stories, catalog_story_ids


def validate_quizzes(story_id: str, quizzes: list) -> int:
    errors = 0
    if not isinstance(quizzes, list):
        log_error(f"story.json: 'quizzes' debe ser una lista/array.")
        return 1

    for q_idx, quiz in enumerate(quizzes):
        if not isinstance(quiz, dict):
            log_error(f"story.json: Quiz #{q_idx + 1} no es un objeto válido.")
            errors += 1
            continue

        q_type = quiz.get("type")
        if not q_type:
            log_error(f"story.json: Quiz #{q_idx + 1} carece del campo 'type'.")
            errors += 1
            continue

        if "id" not in quiz or "after_paragraph_id" not in quiz:
            log_error(f"story.json: Quiz #{q_idx + 1} ({q_type}) debe tener 'id' y 'after_paragraph_id'.")
            errors += 1

        # Esquemas por tipo de Quiz
        if q_type == "translation":
            req_fields = ["word", "correct", "options"]
            for field in req_fields:
                if field not in quiz:
                    log_error(f"story.json: Quiz translation ({quiz.get('id')}) carece del campo '{field}'.")
                    errors += 1
            if "options" in quiz and not isinstance(quiz["options"], list):
                log_error(f"story.json: Quiz translation ({quiz.get('id')}) 'options' debe ser un array.")
                errors += 1

        elif q_type == "matching":
            if "pairs" not in quiz or not isinstance(quiz["pairs"], list):
                log_error(f"story.json: Quiz matching ({quiz.get('id')}) requiere un array 'pairs'.")
                errors += 1
            else:
                for p_idx, pair in enumerate(quiz["pairs"]):
                    if not isinstance(pair, dict) or "en" not in pair or "es" not in pair:
                        log_error(f"story.json: Quiz matching ({quiz.get('id')}) par #{p_idx + 1} debe contener 'en' y 'es'.")
                        errors += 1

        elif q_type == "comprehension":
            req_fields = ["question", "options", "correct_index"]
            for field in req_fields:
                if field not in quiz:
                    log_error(f"story.json: Quiz comprehension ({quiz.get('id')}) carece del campo '{field}'.")
                    errors += 1
            if "options" in quiz and not isinstance(quiz["options"], list):
                log_error(f"story.json: Quiz comprehension ({quiz.get('id')}) 'options' debe ser un array.")
                errors += 1
            if "correct_index" in quiz and not isinstance(quiz["correct_index"], int):
                log_error(f"story.json: Quiz comprehension ({quiz.get('id')}) 'correct_index' debe ser un entero.")
                errors += 1
        else:
            log_warning(f"story.json: Quiz #{q_idx + 1} tiene un tipo desconocido: '{q_type}'.")

    return errors


def validate_story_directory(story_dir: Path, is_in_catalog: bool) -> bool:
    story_id = story_dir.name
    tag = "HISTORIA REGISTRADA" if is_in_catalog else "BORRADOR / EN DESARROLLO"
    print_separator(story_id, tag=tag)

    if not is_in_catalog:
        log_warning("Esta historia está en la raíz pero aún NO está registrada en catalog.json.")

    errors = 0
    story_json_path = story_dir / "story.json"
    header_scene_file = "scene_01.webp"

    # 1. Validar existencia obligatoria de story.json
    if not story_json_path.exists():
        log_error("Falta el archivo obligatorio 'story.json'.")
        return False
    elif story_json_path.stat().st_size == 0:
        log_error("El archivo 'story.json' está vacío (0 bytes).")
        return False

    # Leer story.json para obtener datos
    try:
        with open(story_json_path, "r", encoding="utf-8") as f:
            story_data = json.load(f)

        header_scene_file = story_data.get("header_scene", "scene_01.webp")

        # Validar que el ID interno de story.json coincida exactamente con el nombre de la carpeta
        internal_id = story_data.get("id")
        if internal_id != story_id:
            log_error(f"story.json: El ID interno ('{internal_id}') NO coincide con el nombre de la carpeta ('{story_id}').")
            errors += 1

        # Validar propiedades obligatorias en la raíz de story.json
        for key in MANDATORY_STORY_JSON_KEYS:
            if key not in story_data or story_data[key] is None:
                log_error(f"story.json: Falta la propiedad obligatoria '{key}'.")
                errors += 1

        # Validar paragraphs
        paragraphs = story_data.get("paragraphs")
        if not isinstance(paragraphs, list) or len(paragraphs) == 0:
            log_error("story.json: 'paragraphs' debe ser una lista con al menos 1 párrafo.")
            errors += 1

        # Validar quizzes
        quizzes = story_data.get("quizzes", [])
        errors += validate_quizzes(story_id, quizzes)

    except json.JSONDecodeError as e:
        log_error(f"story.json: Sintaxis JSON inválida: {e}")
        return False

    # 2. Validar archivos de imagen obligatorios (cover.webp y header_scene)
    cover_path = story_dir / "cover.webp"
    if not cover_path.exists():
        log_error("Falta la imagen obligatoria 'cover.webp'.")
        errors += 1
    elif cover_path.stat().st_size == 0:
        log_error("La imagen 'cover.webp' está vacía (0 bytes).")
        errors += 1

    scene_path = story_dir / header_scene_file
    if not scene_path.exists():
        log_error(f"Falta la imagen de escena obligatoria '{header_scene_file}'.")
        errors += 1
    elif scene_path.stat().st_size == 0:
        log_error(f"La imagen de escena '{header_scene_file}' está vacía (0 bytes).")
        errors += 1

    # 3. Regla de Par de Audio (audio.opus <-> timestamps.json)
    audio_path = story_dir / "audio.opus"
    timestamps_path = story_dir / "timestamps.json"

    has_audio = audio_path.exists() and audio_path.stat().st_size > 0
    has_timestamps = timestamps_path.exists() and timestamps_path.stat().st_size > 0

    if has_audio and not has_timestamps:
        log_error("Contiene 'audio.opus' pero falta su par obligatorio 'timestamps.json'.")
        errors += 1
    elif has_timestamps and not has_audio:
        log_error("Contiene 'timestamps.json' pero falta su par obligatorio 'audio.opus'.")
        errors += 1
    elif not has_audio and not has_timestamps:
        log_warning("Historia sin audio (no contiene audio.opus ni timestamps.json).")

    # 4. Validar dictionary.json si existe (opcional)
    dict_path = story_dir / "dictionary.json"
    if dict_path.exists():
        if dict_path.stat().st_size == 0:
            log_error("'dictionary.json' está vacío (0 bytes).")
            errors += 1
        else:
            try:
                with open(dict_path, "r", encoding="utf-8") as f:
                    dict_data = json.load(f)
                if not isinstance(dict_data, (dict, list)):
                    log_error("dictionary.json: Debe ser un objeto o lista JSON.")
                    errors += 1
            except json.JSONDecodeError as e:
                log_error(f"dictionary.json: Sintaxis JSON inválida: {e}")
                errors += 1

    if errors == 0:
        log_success("Todos los archivos y esquemas están correctos.")

    return errors == 0


def main():
    catalog_ok, catalog_stories, catalog_ids = validate_catalog()
    if not catalog_ok:
        log_error("La validación de catalog.json ha fallado.")
        sys.exit(1)

    story_dirs = [d for d in REPO_ROOT.iterdir() if d.is_dir() and d.name.startswith("story_")]
    x_catalog = len(catalog_ids)
    y_disk = len(story_dirs)

    log_info(f"Resumen de historias: ({x_catalog}/{y_disk}) -> {x_catalog} registradas en catálogo / {y_disk} carpetas en disco.")

    total_errors = 0
    for story_dir in sorted(story_dirs):
        is_in_catalog = story_dir.name in catalog_ids
        if not validate_story_directory(story_dir, is_in_catalog=is_in_catalog):
            total_errors += 1

    print("=" * 65)
    print("RESUMEN FINAL DE AUDITORIA")
    print("=" * 65)
    print(f"  [INFO]  Métricas: ({x_catalog}/{y_disk}) historias en catálogo vs carpetas en disco.")
    if total_errors > 0:
        print(f"  [ERROR] Se encontraron fallos en {total_errors} historia(s).")
        sys.exit(1)
    else:
        print("  [OK] ¡Todas las historias y el catálogo están 100% válidos!")
        sys.exit(0)


if __name__ == "__main__":
    main()
