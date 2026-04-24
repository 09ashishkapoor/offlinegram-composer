from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PRESETS_CONFIG_PATH = Path(os.environ.get("OFFLINEGRAM_PRESETS_PATH", BASE_DIR / "presets.json")).expanduser().resolve()
STRUCTURED_BATCH_TEXT_SOURCES = {"number", "name", "caption", "title", "subtitle"}


class PresetConfigError(ValueError):
    pass


def _ensure_numeric_zone_value(
    value: Any,
    *,
    preset_id: str,
    zone_index: int,
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define a numeric '{field}'.") from exc

    if minimum is not None and number < minimum:
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define '{field}' >= {minimum}.")
    if maximum is not None and number > maximum:
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define '{field}' <= {maximum}.")
    return number


def _ensure_boolean_zone_value(
    value: Any,
    *,
    preset_id: str,
    zone_index: int,
    field: str,
) -> bool:
    if not isinstance(value, bool):
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define a boolean '{field}'.")
    return value


def _ensure_hex_color_value(
    value: Any,
    *,
    preset_id: str,
    zone_index: int,
    field: str,
) -> str:
    if not isinstance(value, str):
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define a hex '{field}'.")

    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", value.strip()):
        raise PresetConfigError(f"Preset '{preset_id}' zone #{zone_index} must define a valid 6-digit hex '{field}'.")

    return value.strip()


def _ensure_non_empty_string(value: Any, preset_id: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PresetConfigError(f"Preset '{preset_id}' must define a non-empty '{field}'.")
    return value.strip()


def _load_raw_config(config_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PresetConfigError("Preset config file was not found.") from exc
    except json.JSONDecodeError as exc:
        raise PresetConfigError("Preset config file is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise PresetConfigError("Preset config root must be an object.")
    return payload


def _write_raw_config(payload: dict[str, Any], config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=str(config_path.parent))
    tmp_file = Path(tmp_path)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_file, config_path)
    except Exception:
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)
        raise


def _coerce_id(candidate: Any, existing_ids: set[str], *, fallback_id: str, allow_auto_generate: bool) -> str:
    base_id = candidate.strip() if isinstance(candidate, str) else ""
    if not base_id:
        base_id = fallback_id.strip() or "preset"

    if base_id not in existing_ids:
        return base_id

    if not allow_auto_generate:
        raise PresetConfigError(f"Preset id '{base_id}' already exists.")

    for suffix in range(1, 9999):
        generated_id = f"{base_id}_{suffix}"
        if generated_id not in existing_ids:
            return generated_id

    raise PresetConfigError("Unable to generate a unique preset id.")


def _coerce_preset_payload(
    payload: dict[str, Any],
    *,
    fallback_id: str,
    existing_ids: set[str],
    allow_auto_generate: bool,
) -> dict[str, Any]:
    preset = dict(payload)
    requested_id = preset.get("id")
    should_auto_generate = "id" not in preset or not str(requested_id).strip()
    preset["id"] = _coerce_id(
        requested_id,
        existing_ids,
        fallback_id=fallback_id,
        allow_auto_generate=allow_auto_generate and should_auto_generate,
    )
    preset["label"] = str(preset.get("label") or "").strip()
    preset["description"] = str(preset.get("description") or "").strip()
    raw_zones = preset.get("zones")
    preset["zones"] = [dict(zone) if isinstance(zone, dict) else zone for zone in raw_zones] if isinstance(raw_zones, list) else raw_zones
    return preset


def _validate_preset(preset: dict[str, Any], /, *, preset_id: str | None = None) -> dict[str, Any]:
    required_fields = ("id", "label", "description", "zones")
    for field in required_fields:
        if field not in preset:
            if preset_id is None:
                raise PresetConfigError("Preset is missing required field 'id'.")
            raise PresetConfigError(f"Preset '{preset_id}' is missing required field '{field}'.")

    resolved_id = str(preset["id"]) if "id" in preset else (preset_id or "<unknown>")
    _ensure_non_empty_string(resolved_id, resolved_id, "id")
    preset["id"] = _ensure_non_empty_string(resolved_id, resolved_id, "id")
    preset["label"] = _ensure_non_empty_string(preset["label"], resolved_id, "label")
    preset["description"] = _ensure_non_empty_string(preset["description"], resolved_id, "description")

    zones = preset["zones"]
    _validate_zone_entries(zones, preset_id=preset["id"], require_non_empty=True)

    return preset


def _validate_zone_entries(zones: Any, *, preset_id: str, require_non_empty: bool) -> list[dict[str, Any]]:
    if not isinstance(zones, list) or (require_non_empty and not zones):
        raise PresetConfigError(f"Preset '{preset_id}' must define at least one zone.")

    for index, zone in enumerate(zones, start=1):
        if not isinstance(zone, dict):
            raise PresetConfigError(f"Preset '{preset_id}' zone #{index} must be an object.")

        if zone.get("type") == "text":
            if "font_size" in zone:
                _ensure_numeric_zone_value(zone.get("font_size"), preset_id=preset_id, zone_index=index, field="font_size", minimum=1)
            if "x_percent" in zone:
                _ensure_numeric_zone_value(zone.get("x_percent"), preset_id=preset_id, zone_index=index, field="x_percent", minimum=0, maximum=100)
            if "y_percent" in zone:
                _ensure_numeric_zone_value(zone.get("y_percent"), preset_id=preset_id, zone_index=index, field="y_percent", minimum=0, maximum=100)
            if "outline_thickness" in zone:
                _ensure_numeric_zone_value(zone.get("outline_thickness"), preset_id=preset_id, zone_index=index, field="outline_thickness", minimum=0)
            if "opacity" in zone:
                _ensure_numeric_zone_value(zone.get("opacity"), preset_id=preset_id, zone_index=index, field="opacity", minimum=0, maximum=1)
            if "max_width_percent" in zone:
                _ensure_numeric_zone_value(zone.get("max_width_percent"), preset_id=preset_id, zone_index=index, field="max_width_percent", minimum=1, maximum=100)
            if "bg_opacity" in zone:
                _ensure_numeric_zone_value(zone.get("bg_opacity"), preset_id=preset_id, zone_index=index, field="bg_opacity", minimum=0, maximum=1)
            if "bg_padding" in zone:
                _ensure_numeric_zone_value(zone.get("bg_padding"), preset_id=preset_id, zone_index=index, field="bg_padding", minimum=0)
            if "shadow_enabled" in zone:
                _ensure_boolean_zone_value(zone.get("shadow_enabled"), preset_id=preset_id, zone_index=index, field="shadow_enabled")
            if "shadow_dx" in zone:
                _ensure_numeric_zone_value(zone.get("shadow_dx"), preset_id=preset_id, zone_index=index, field="shadow_dx")
            if "shadow_dy" in zone:
                _ensure_numeric_zone_value(zone.get("shadow_dy"), preset_id=preset_id, zone_index=index, field="shadow_dy")
            if "shadow_blur" in zone:
                _ensure_numeric_zone_value(zone.get("shadow_blur"), preset_id=preset_id, zone_index=index, field="shadow_blur", minimum=0)
            if "shadow_opacity" in zone:
                _ensure_numeric_zone_value(zone.get("shadow_opacity"), preset_id=preset_id, zone_index=index, field="shadow_opacity", minimum=0, maximum=1)
            if "outline_enabled" in zone:
                _ensure_boolean_zone_value(zone.get("outline_enabled"), preset_id=preset_id, zone_index=index, field="outline_enabled")
            if "uppercase" in zone:
                _ensure_boolean_zone_value(zone.get("uppercase"), preset_id=preset_id, zone_index=index, field="uppercase")
            if "text_color" in zone:
                _ensure_hex_color_value(zone.get("text_color"), preset_id=preset_id, zone_index=index, field="text_color")
            if "bg_color" in zone:
                _ensure_hex_color_value(zone.get("bg_color"), preset_id=preset_id, zone_index=index, field="bg_color")
            if "shadow_color" in zone:
                _ensure_hex_color_value(zone.get("shadow_color"), preset_id=preset_id, zone_index=index, field="shadow_color")
            if "outline_color" in zone:
                _ensure_hex_color_value(zone.get("outline_color"), preset_id=preset_id, zone_index=index, field="outline_color")

    return zones


def validate_zone_list(zones: Any, *, preset_id: str = "overlay") -> list[dict[str, Any]]:
    return _validate_zone_entries(zones, preset_id=preset_id, require_non_empty=False)


def load_preset_catalog(config_path: Path = PRESETS_CONFIG_PATH) -> list[dict[str, Any]]:
    payload = _load_raw_config(config_path)
    presets = payload.get("presets")
    if not isinstance(presets, list) or not presets:
        raise PresetConfigError("Preset config must define a non-empty 'presets' list.")

    validated_presets: list[dict[str, Any]] = []
    for index, preset in enumerate(presets, start=1):
        if not isinstance(preset, dict):
            raise PresetConfigError(f"Preset entry #{index} must be an object.")
        validated_presets.append(_validate_preset(dict(preset)))
    return validated_presets


def _load_config_for_update(config_path: Path) -> list[dict[str, Any]]:
    return load_preset_catalog(config_path)


def _require_unique_preset_id(presets: list[dict[str, Any]], preset_id: str, *, current_index: int | None = None) -> None:
    for index, preset in enumerate(presets):
        if index == current_index:
            continue
        if preset["id"] == preset_id:
            raise PresetConfigError(f"Preset id '{preset_id}' already exists.")


def create_preset(preset: dict[str, Any], config_path: Path = PRESETS_CONFIG_PATH) -> dict[str, Any]:
    if not isinstance(preset, dict):
        raise PresetConfigError("Preset payload must be an object.")

    presets = _load_config_for_update(config_path)
    existing_ids = {item["id"] for item in presets}
    validated = _coerce_preset_payload(
        preset,
        fallback_id="preset",
        existing_ids=existing_ids,
        allow_auto_generate=True,
    )
    _validate_preset(validated)

    presets.append(validated)
    _write_raw_config({"presets": presets}, config_path)
    return validated


def update_preset(
    preset_id: str,
    patch: dict[str, Any],
    config_path: Path = PRESETS_CONFIG_PATH,
    *,
    replace: bool = True,
) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise PresetConfigError("Preset update payload must be an object.")

    presets = _load_config_for_update(config_path)
    for index, preset in enumerate(presets):
        if preset["id"] == preset_id:
            break
    else:
        raise PresetConfigError(f"Unknown preset '{preset_id}'.")

    incoming = dict(patch)
    if replace:
        if not incoming:
            raise PresetConfigError(f"Preset '{preset_id}' update payload is empty.")
        updated = incoming
    else:
        updated = dict(preset)
        updated.update(incoming)

    if "id" not in updated:
        updated["id"] = preset["id"]

    if updated.get("id") != preset["id"]:
        raise PresetConfigError("Preset id cannot be changed.")

    if not replace and "label" not in updated:
        updated["label"] = preset["label"]
    if not replace and "description" not in updated:
        updated["description"] = preset["description"]
    if not replace and "zones" not in updated:
        updated["zones"] = preset["zones"]

    _validate_preset(updated, preset_id=preset["id"])
    _require_unique_preset_id(presets, updated["id"], current_index=index)

    presets[index] = updated
    _write_raw_config({"presets": presets}, config_path)
    return updated


def delete_preset(preset_id: str, config_path: Path = PRESETS_CONFIG_PATH) -> dict[str, Any]:
    presets = _load_config_for_update(config_path)
    if len(presets) <= 1:
        raise PresetConfigError("Cannot delete the last preset.")

    for index, preset in enumerate(presets):
        if preset["id"] == preset_id:
            removed = presets.pop(index)
            _write_raw_config({"presets": presets}, config_path)
            return removed
    raise PresetConfigError(f"Unknown preset '{preset_id}'.")


def list_presets(config_path: Path = PRESETS_CONFIG_PATH) -> list[dict[str, str]]:
    return [
        {
            "id": preset["id"],
            "label": preset["label"],
            "description": preset["description"],
        }
        for preset in load_preset_catalog(config_path)
    ]


def _get_preset_zones(preset_id: str, config_path: Path) -> list[dict[str, Any]]:
    for preset in load_preset_catalog(config_path):
        if preset["id"] == preset_id:
            return [dict(zone) for zone in preset["zones"]]
    raise PresetConfigError(f"Unknown preset '{preset_id}'.")


def build_preset_zones(
    preset_id: str,
    text: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[dict[str, Any]]:
    zones = _get_preset_zones(preset_id, config_path)
    for zone in zones:
        if zone.get("type") == "text" and zone.get("text_source") == "custom":
            zone["custom_text"] = text
    return zones


def build_batch_quote_zones(
    preset_id: str,
    quote: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[dict[str, Any]]:
    zones = _get_preset_zones(preset_id, config_path)
    custom_text_zones = [
        zone for zone in zones if zone.get("type") == "text" and zone.get("text_source") == "custom"
    ]
    if len(custom_text_zones) != 1:
        raise PresetConfigError("Batch mode requires a preset with exactly one custom text zone.")

    custom_text_zones[0]["custom_text"] = quote
    return zones


def resolve_batch_preset_mode(
    preset_id: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> str:
    zones = _get_preset_zones(preset_id, config_path)
    structured_text_zones = [
        zone
        for zone in zones
        if zone.get("type") == "text" and zone.get("text_source") in STRUCTURED_BATCH_TEXT_SOURCES
    ]
    if structured_text_zones:
        return "structured"

    custom_text_zones = [
        zone for zone in zones if zone.get("type") == "text" and zone.get("text_source") == "custom"
    ]
    if len(custom_text_zones) == 1:
        return "quote"

    raise PresetConfigError(
        "Batch mode requires either exactly one custom text zone or at least one text zone using number, name, caption, title, or subtitle."
    )


def build_batch_structured_zones(
    preset_id: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[dict[str, Any]]:
    zones = _get_preset_zones(preset_id, config_path)
    if not any(
        zone.get("type") == "text" and zone.get("text_source") in STRUCTURED_BATCH_TEXT_SOURCES
        for zone in zones
    ):
        raise PresetConfigError(
            "Structured batch mode requires a preset with at least one text zone using number, name, caption, title, or subtitle."
        )
    return zones


def structured_fields_for_preset(
    preset_id: str,
    config_path: Path = PRESETS_CONFIG_PATH,
) -> list[str]:
    zones = _get_preset_zones(preset_id, config_path)
    fields: list[str] = []
    seen: set[str] = set()
    for zone in zones:
        if zone.get("type") != "text":
            continue
        field = zone.get("text_source")
        if not isinstance(field, str):
            continue
        normalized_field = field.strip().lower()
        if normalized_field in STRUCTURED_BATCH_TEXT_SOURCES and normalized_field not in seen:
            fields.append(normalized_field)
            seen.add(normalized_field)

    if not fields:
        raise PresetConfigError(
            "Structured batch mode requires a preset with at least one text zone using number, name, caption, title, or subtitle."
        )

    return fields
