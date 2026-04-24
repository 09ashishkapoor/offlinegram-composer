import json
import base64
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import app as app_module
from app import app
from processor import ProcessorError


client = TestClient(app)


def create_image(path: Path, color: tuple[int, int, int, int]) -> None:
    Image.new("RGBA", (1080, 1080), color).save(path)


def test_fonts_endpoint():
    response = client.get("/api/fonts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fonts"]


def test_presets_endpoint():
    response = client.get("/api/presets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["presets"]
    assert payload["helper_text"] == "Presets are editable in-app and saved to presets.json in this project folder."


def test_presets_crud_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "PRESETS_CONFIG_PATH", tmp_path / "presets.json")
    source = Path("presets.json").read_text(encoding="utf-8")
    app_module.PRESETS_CONFIG_PATH.write_text(source, encoding="utf-8")

    create_response = client.post(
        "/api/presets",
        json={
            "id": "api_preset",
            "label": "API Preset",
            "description": "Created by API",
            "zones": [
                {
                    "id": "api-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 30,
                    "text_color": "#FFFFFF",
                    "opacity": 1.0,
                    "x_percent": 50,
                    "y_percent": 50,
                    "alignment": "center",
                    "max_width_percent": 80,
                    "uppercase": False,
                    "bg_shape": "none",
                    "bg_color": "#000000",
                    "bg_opacity": 0.0,
                    "bg_padding": 0,
                    "shadow_enabled": False,
                    "shadow_dx": 0,
                    "shadow_dy": 0,
                    "shadow_blur": 0,
                    "shadow_color": "#000000",
                    "shadow_opacity": 0.0,
                    "outline_enabled": False,
                    "outline_thickness": 0,
                    "outline_color": "#000000",
                }
            ],
        },
    )
    assert create_response.status_code == 200
    assert create_response.json()["preset"]["id"] == "api_preset"

    update_response = client.put(
        "/api/presets/api_preset",
        json={
            "id": "api_preset",
            "label": "API Preset Updated",
            "description": "Updated by API",
            "zones": [
                {
                    "id": "api-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 30,
                    "text_color": "#FFFFFF",
                    "opacity": 1.0,
                    "x_percent": 50,
                    "y_percent": 50,
                    "alignment": "center",
                    "max_width_percent": 80,
                    "uppercase": True,
                    "bg_shape": "none",
                    "bg_color": "#000000",
                    "bg_opacity": 0.0,
                    "bg_padding": 0,
                    "shadow_enabled": False,
                    "shadow_dx": 0,
                    "shadow_dy": 0,
                    "shadow_blur": 0,
                    "shadow_color": "#000000",
                    "shadow_opacity": 0.0,
                    "outline_enabled": False,
                    "outline_thickness": 0,
                    "outline_color": "#000000",
                }
            ],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["preset"]["label"] == "API Preset Updated"

    delete_response = client.delete("/api/presets/api_preset")
    assert delete_response.status_code == 200
    assert delete_response.json()["preset"]["id"] == "api_preset"


def test_presets_endpoint_rejects_duplicate_id(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "PRESETS_CONFIG_PATH", tmp_path / "presets.json")
    app_module.PRESETS_CONFIG_PATH.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")

    response = client.post(
        "/api/presets",
        json={
            "id": "preset_1",
            "label": "Duplicate",
            "description": "Duplicate id",
            "zones": [
                {
                    "id": "api-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 30,
                    "text_color": "#FFFFFF",
                    "opacity": 1.0,
                    "x_percent": 50,
                    "y_percent": 50,
                    "alignment": "center",
                    "max_width_percent": 80,
                    "uppercase": False,
                    "bg_shape": "none",
                    "bg_color": "#000000",
                    "bg_opacity": 0.0,
                    "bg_padding": 0,
                    "shadow_enabled": False,
                    "shadow_dx": 0,
                    "shadow_dy": 0,
                    "shadow_blur": 0,
                    "shadow_color": "#000000",
                    "shadow_opacity": 0.0,
                    "outline_enabled": False,
                    "outline_thickness": 0,
                    "outline_color": "#000000",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_presets_update_rejects_empty_label(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "PRESETS_CONFIG_PATH", tmp_path / "presets.json")
    app_module.PRESETS_CONFIG_PATH.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")

    response = client.put(
        "/api/presets/preset_1",
        json={
            "id": "preset_1",
            "label": "   ",
            "description": "No label",
            "zones": [
                {
                    "id": "preset-1-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                    "font_name": "BebasNeue-Regular",
                    "font_size": 74,
                    "text_color": "#FFFFFF",
                    "opacity": 1.0,
                    "x_percent": 50,
                    "y_percent": 59,
                    "alignment": "center",
                    "max_width_percent": 72,
                    "uppercase": True,
                    "bg_shape": "none",
                    "bg_color": "#000000",
                    "bg_opacity": 0.0,
                    "bg_padding": 0,
                    "shadow_enabled": True,
                    "shadow_dx": 0,
                    "shadow_dy": 5,
                    "shadow_blur": 14,
                    "shadow_color": "#000000",
                    "shadow_opacity": 0.9,
                    "outline_enabled": True,
                    "outline_thickness": 14,
                    "outline_color": "#000000",
                }
            ],
        },
    )
    assert response.status_code == 400
    assert "non-empty 'label'" in response.json()["detail"]


def test_presets_create_without_id_auto_generates_stable_id(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "PRESETS_CONFIG_PATH", tmp_path / "presets.json")
    app_module.PRESETS_CONFIG_PATH.write_text(Path("presets.json").read_text(encoding="utf-8"), encoding="utf-8")

    response = client.post(
        "/api/presets",
        json={
            "label": "Generated preset",
            "description": "No explicit id",
            "zones": [
                {
                    "id": "generated-text",
                    "type": "text",
                    "text_source": "custom",
                    "custom_text": "",
                }
            ],
        },
    )

    assert response.status_code == 200
    preset_id = response.json()["preset"]["id"]
    assert preset_id.startswith("preset")
    assert preset_id != "None"


def test_preview_single_structured_rejects_incomplete_text(tmp_path: Path):
    image_path = tmp_path / "single-structured-invalid.png"
    create_image(image_path, (25, 25, 25, 255))
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single-structured-invalid.png", image_file, "image/png")},
            data={
                "preset_id": "preset_3",
                "text": "1. Missing caption",
            },
        )

    assert response.status_code == 400
    assert "Structured presets require either one line" in response.json()["detail"]


def test_preview_single_uses_preset_id(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={"preset_id": "preset_1", "text": "Kala Bhairava"},
        )
    assert response.status_code == 200
    assert "image_b64" in response.json()


def test_generate_single_uses_preset_id(tmp_path: Path):
    image_path = tmp_path / "single.png"
    output_dir = tmp_path / "out"
    create_image(image_path, (20, 20, 20, 255))
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_2",
                "text": "Kala Bhairava",
                "output_dir": str(output_dir),
            },
        )
    assert response.status_code == 200
    assert Path(response.json()["saved_to"]).exists()


def test_generate_single_rejects_invalid_export_format(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={"preset_id": "preset_2", "text": "Kala Bhairava", "output_dir": str(tmp_path / "out"), "format": "bmp"},
        )

    assert response.status_code == 400
    assert "Unsupported export format" in response.json()["detail"]


def test_generate_single_rejects_invalid_export_quality(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_2",
                "text": "Kala Bhairava",
                "output_dir": str(tmp_path / "out"),
                "format": "jpg",
                "quality": "0",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Quality must be between 1 and 100."


def test_generate_single_rejects_invalid_filename_template(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_2",
                "text": "Kala Bhairava",
                "output_dir": str(tmp_path / "out"),
                "filename_template": "{bad_token}",
            },
        )

    assert response.status_code == 400
    assert "Unsupported filename token" in response.json()["detail"]


def test_generate_single_respects_export_format_and_template(tmp_path: Path):
    image_path = tmp_path / "single.png"
    output_dir = tmp_path / "out"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_2",
                "text": "Kala Bhairava",
                "output_dir": str(output_dir),
                "format": "jpg",
                "quality": "85",
                "filename_template": "{source}-{index}",
            },
        )

    assert response.status_code == 200
    saved_to = Path(response.json()["saved_to"])
    assert saved_to.suffix == ".jpg"
    assert saved_to.exists()
    assert saved_to.name.startswith("single-1")


def test_generate_single_accepts_export_format_alias_and_named_tokens(tmp_path: Path):
    image_path = tmp_path / "single.png"
    output_dir = tmp_path / "out"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_2",
                "text": "Kala Bhairava",
                "output_dir": str(output_dir),
                "export_format": "jpg",
                "export_quality": "75",
                "filename_template": "{preset}_{index}_{source_name}_{base_name}",
            },
        )

    assert response.status_code == 200
    saved_to = Path(response.json()["saved_to"])
    assert saved_to.suffix == ".jpg"
    assert saved_to.exists()
    assert "preset_2" in saved_to.name
    assert "1" in saved_to.name


def test_batch_quotes_generate_accepts_export_format_alias(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")
    out = tmp_path / "out"

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(out),
                "export_format": "webp",
                "filename_template": "{preset}-{index}",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_count"] == 2
    assert payload["files"][0].endswith(".webp")
    assert payload["files"][1].endswith(".webp")
    assert Path(payload["files"][0]).name.startswith("preset_1-1")


def test_preview_single_supports_structured_preset(tmp_path: Path):
    image_path = tmp_path / "single-structured.png"
    create_image(image_path, (25, 25, 25, 255))
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single-structured.png", image_file, "image/png")},
            data={
                "preset_id": "preset_3",
                "text": "1\nShhmashhana kalika\nThe dark-bodied Goddess of the cremation ground.",
            },
        )
    assert response.status_code == 200
    assert "image_b64" in response.json()


def test_preview_single_rejects_unknown_preset(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={"preset_id": "does-not-exist", "text": "Test"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown preset 'does-not-exist'."


def test_batch_quotes_preview_rejects_unknown_preset(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("Only one quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir), "preset_id": "does-not-exist"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown preset 'does-not-exist'."


def test_preview_single_rejects_missing_image_path(tmp_path: Path):
    response = client.post(
        "/api/preview",
        data={"preset_id": "preset_1", "image_path": str(tmp_path / "missing.png"), "text": "Where am I?"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected image was not found."


def test_preview_single_rejects_unreadable_image_path(tmp_path: Path):
    unreadable_path = tmp_path / "unreadable-dir"
    unreadable_path.mkdir()

    response = client.post(
        "/api/preview",
        data={"preset_id": "preset_1", "image_path": str(unreadable_path), "text": "No decode"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to read image input."


def test_preview_single_rejects_non_image_path(tmp_path: Path):
    non_image_path = tmp_path / "not-an-image.txt"
    non_image_path.write_text("just text", encoding="utf-8")

    response = client.post(
        "/api/preview",
        data={"preset_id": "preset_1", "image_path": str(non_image_path), "text": "Bad input"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to read image input."


def test_preview_single_accepts_overlay_override(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))
    overlay = [
        {
            "id": "custom-text",
            "type": "text",
            "text_source": "custom",
            "custom_text": "Kala Bhairava",
            "font_name": "BebasNeue-Regular",
            "font_size": 64,
            "text_color": "#FFFFFF",
            "opacity": 1.0,
            "x_percent": 50,
            "y_percent": 40,
            "alignment": "center",
            "max_width_percent": 82,
            "uppercase": True,
            "bg_shape": "none",
            "bg_color": "#000000",
            "bg_opacity": 0.0,
            "bg_padding": 0,
            "shadow_enabled": True,
            "shadow_dx": 0,
            "shadow_dy": 5,
            "shadow_blur": 14,
            "shadow_color": "#000000",
            "shadow_opacity": 0.9,
            "outline_enabled": True,
            "outline_thickness": 8,
            "outline_color": "#000000",
        }
    ]
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_1",
                "text": "Kala Bhairava",
                "overlay_json": json.dumps(overlay),
            },
        )
    assert response.status_code == 200


def test_preview_single_overlay_richer_typography_changes_output(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    overlay = [
        {
            "id": "custom-text",
            "type": "text",
            "text_source": "custom",
            "custom_text": "Kala Bhairava",
            "font_name": "BebasNeue-Regular",
            "font_size": 60,
            "text_color": "#00FF00",
            "opacity": 0.65,
            "x_percent": 50,
            "y_percent": 40,
            "alignment": "center",
            "max_width_percent": 60,
            "uppercase": True,
            "bg_shape": "rectangle",
            "bg_color": "#001100",
            "bg_opacity": 0.4,
            "bg_padding": 18,
            "shadow_enabled": True,
            "shadow_dx": 0,
            "shadow_dy": 6,
            "shadow_blur": 11,
            "shadow_color": "#111111",
            "shadow_opacity": 0.75,
            "outline_enabled": True,
            "outline_thickness": 5,
            "outline_color": "#00AA00",
        }
    ]

    with image_path.open("rb") as image_file:
        base_response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={"preset_id": "preset_1", "text": "Kala Bhairava"},
        )

    with image_path.open("rb") as image_file:
        overlay_response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_1",
                "text": "Kala Bhairava",
                "overlay_json": json.dumps(overlay),
            },
        )

    assert base_response.status_code == 200
    assert overlay_response.status_code == 200

    base_image = base64.b64decode(base_response.json()["image_b64"])
    overlay_image = base64.b64decode(overlay_response.json()["image_b64"])
    assert base_image != overlay_image


def test_preview_single_rejects_invalid_overlay_json(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_1",
                "text": "Kala Bhairava",
                "overlay_json": "{this is not json}",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid overlay JSON."


def test_preview_single_rejects_non_list_overlay_json(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_1",
                "text": "Kala Bhairava",
                "overlay_json": '{"id": "custom-text"}',
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Overlay payload must be a list."


def test_preview_single_rejects_invalid_overlay_typography_value(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))
    overlay = [
        {
            "id": "custom-text",
            "type": "text",
            "text_source": "custom",
            "custom_text": "Kala Bhairava",
            "text_color": "#12",
        }
    ]

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={
                "preset_id": "preset_1",
                "text": "Kala Bhairava",
                "overlay_json": json.dumps(overlay),
            },
        )

    assert response.status_code == 400
    assert "text_color" in response.json()["detail"]


def test_browse_valid_path(tmp_path: Path):
    response = client.get("/api/browse", params={"path": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    assert "folders" in payload
    assert "text_files" in payload
    assert payload["current"] == str(tmp_path.resolve())


def test_browse_invalid_path():
    response = client.get("/api/browse", params={"path": "Z:\\this\\path\\should\\not\\exist"})
    assert response.status_code == 400


def test_browse_lists_text_files(tmp_path: Path):
    quote_file = tmp_path / "quotes.txt"
    quote_file.write_text("Stay steady\n", encoding="utf-8")
    markdown_file = tmp_path / "notes.md"
    markdown_file.write_text("Line\n", encoding="utf-8")
    csv_file = tmp_path / "entries.csv"
    csv_file.write_text("1,Name,Caption\n1,Alpha,Beta\n", encoding="utf-8")
    tsv_file = tmp_path / "entries.tsv"
    tsv_file.write_text("1\tName\tCaption\n1\tAlpha\tBeta\n", encoding="utf-8")
    create_image(tmp_path / "sample.png", (1, 2, 3, 255))

    response = client.get("/api/browse", params={"path": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    text_names = {item["name"] for item in payload["text_files"]}
    assert "quotes.txt" in text_names
    assert "notes.md" in text_names
    assert "entries.csv" in text_names
    assert "entries.tsv" in text_names


def test_pick_path_supports_batch_quotes_mode(monkeypatch, tmp_path: Path):
    selected = tmp_path / "chosen"
    selected.mkdir()
    captured: dict[str, str | None] = {}

    def fake_picker(mode: str, initial_path: str | None = None) -> str:
        captured["mode"] = mode
        captured["initial_path"] = initial_path
        return str(selected)

    monkeypatch.setattr("app.pick_native_path", fake_picker)
    response = client.post(
        "/api/pick",
        json={
            "mode": "batch-quotes",
            "initial_path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cancelled"] is False
    assert payload["path"] == str(selected.resolve())
    assert captured["mode"] == "batch-quotes"
    assert captured["initial_path"] == str(tmp_path)


def test_pick_path_success(monkeypatch, tmp_path: Path):
    selected = tmp_path / "chosen"
    selected.mkdir()
    captured: dict[str, str | None] = {}

    def fake_picker(mode: str, initial_path: str | None = None) -> str:
        captured["mode"] = mode
        captured["initial_path"] = initial_path
        return str(selected)

    monkeypatch.setattr("app.pick_native_path", fake_picker)
    response = client.post(
        "/api/pick",
        json={
            "mode": "batch-output",
            "initial_path": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cancelled"] is False
    assert payload["path"] == str(selected.resolve())
    assert captured["mode"] == "batch-output"
    assert captured["initial_path"] == str(tmp_path)


def test_pick_path_cancelled(monkeypatch):
    monkeypatch.setattr("app.pick_native_path", lambda mode, initial_path=None: None)
    response = client.post("/api/pick", json={"mode": "output"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["cancelled"] is True
    assert payload["path"] is None


def test_pick_path_rejects_invalid_mode():
    response = client.post("/api/pick", json={"mode": "not-a-real-mode"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid picker mode."


def test_pick_path_unavailable_runtime(monkeypatch):
    def raise_unavailable(mode: str, initial_path: str | None = None) -> str | None:
        raise ProcessorError("Native path picker is available only on Windows.")

    monkeypatch.setattr("app.pick_native_path", raise_unavailable)
    response = client.post("/api/pick", json={"mode": "output"})
    assert response.status_code == 501
    assert response.json()["detail"] == "Native path picker is available only on Windows."


def test_batch_preview_and_generate(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\nName 2: Meaning 2\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        preview_response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "sample_count": "2",
            },
        )
    assert preview_response.status_code == 200
    assert len(preview_response.json()["previews"]) == 2

    with text_file.open("rb") as file_handle:
        generate_response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "output_dir": str(output_dir),
            },
        )
    assert generate_response.status_code == 200
    payload = generate_response.json()
    assert payload["saved_count"] == 2
    for file_path in payload["files"]:
        assert Path(file_path).exists()


def test_batch_quotes_preview_success(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["previews"]) == 2
    assert [item["quote"] for item in payload["previews"]] == ["First quote", "Second quote"]


def test_batch_quotes_preview_rejects_invalid_utf8_text_file(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    text_file = tmp_path / "quotes.bin"
    text_file.write_bytes(b"\xff\xfe\x00bad bytes")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("quotes.bin", file_handle, "text/plain")},
            data={"image_dir": str(image_dir), "preset_id": "preset_1"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Text file must be UTF-8 encoded."


def test_batch_quotes_preview_rejects_text_path_to_directory(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_dir = tmp_path / "text-dir"
    text_dir.mkdir()

    response = client.post(
        "/api/batch/quotes/preview",
        data={
            "image_dir": str(image_dir),
            "preset_id": "preset_1",
            "text_path": str(text_dir),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected text path is not a file."


def test_batch_quotes_preview_rejects_nonexistent_text_path(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    response = client.post(
        "/api/batch/quotes/preview",
        data={
            "image_dir": str(image_dir),
            "preset_id": "preset_1",
            "text_path": str(tmp_path / "missing.txt"),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected text file was not found."


def test_batch_quotes_preview_supports_text_path(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")

    response = client.post(
        "/api/batch/quotes/preview",
        data={
            "text_path": str(text_file),
            "image_dir": str(image_dir),
            "preset_id": "preset_1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["previews"]) == 2


def test_batch_quotes_preview_count_mismatch(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("Only one quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Batch mode expects one quote per image, but counts differ: "
        "found 2 images and 1 quotes. "
        "Ensure every image has exactly one quote and retry."
    )


def test_batch_quotes_generate_success(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(output_dir),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_count"] == 2
    for file_path in payload["files"]:
        assert Path(file_path).exists()


def test_batch_quotes_generate_count_mismatch(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "quotes.txt"
    text_file.write_text("Only one quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(output_dir),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Batch mode expects one quote per image, but counts differ: "
        "found 2 images and 1 quotes. "
        "Ensure every image has exactly one quote and retry."
    )


def test_batch_structured_preview_success_with_preset_3(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "1. Name A: Caption about destiny\n2. Name B: Caption about courage\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir), "preset_id": "preset_3"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "structured"
    assert len(payload["previews"]) == 2
    assert payload["previews"][0]["number"] == "1"
    assert payload["previews"][0]["name"] == "Name A"
    assert payload["previews"][1]["caption"].startswith("Caption")


def test_batch_import_inspect_csv_returns_format_headers_required_fields_and_mapping(tmp_path: Path):
    text_file = tmp_path / "entries.csv"
    text_file.write_text("No,Name,Caption\n1,Name A,Caption A\n2,Name B,Caption B\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/import/inspect",
            files={"text_file": ("entries.csv", file_handle, "text/csv")},
            data={"preset_id": "preset_3", "import_format": "auto"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_format"] == "csv"
    assert payload["headers"] == ["No", "Name", "Caption"]
    assert payload["required_fields"] == ["number", "name", "caption"]
    assert payload["suggested_mapping"] == {"number": "No", "name": "Name", "caption": "Caption"}


def test_batch_structured_preview_with_csv_mapping_is_successful_for_preset_3(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.csv"
    text_file.write_text(
        "No,Name,Caption\n1,Name A,Caption A\n2,Name B,Caption B\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.csv", file_handle, "text/csv")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "import_format": "csv",
                "field_mapping_json": '{"No":"number","Name":"name","Caption":"caption"}',
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "structured"
    assert payload["previews"][0]["number"] == "1"
    assert payload["previews"][1]["caption"] == "Caption B"


def test_batch_structured_generate_with_tsv_field_mapping_json(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.tsv"
    text_file.write_text("No\tName\tCaption\n1\tName A\tCaption A\n2\tName B\tCaption B\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("entries.tsv", file_handle, "text/tab-separated-values")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "output_dir": str(output_dir),
                "import_format": "tsv",
                "field_mapping_json": '{"No":"number","Name":"name","Caption":"caption"}',
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "structured"
    assert payload["saved_count"] == 2
    for file_path in payload["files"]:
        assert Path(file_path).exists()


def test_batch_structured_preview_auto_detect_keeps_plain_text_mode(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("1. Name: Caption\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "import_format": "auto",
            },
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "structured"


def test_batch_import_inspect_uses_title_and_subtitle_required_fields(tmp_path: Path, monkeypatch):
    text_file = tmp_path / "entries.csv"
    text_file.write_text("title,subtitle\nOne,Two\n", encoding="utf-8")

    import app as app_module

    original = app_module.structured_fields_for_preset
    monkeypatch.setattr(app_module, "structured_fields_for_preset", lambda preset_id, config_path=None: ["title", "subtitle"])
    try:
        with text_file.open("rb") as file_handle:
            response = client.post(
                "/api/batch/import/inspect",
                files={"text_file": ("entries.csv", file_handle, "text/csv")},
                data={
                    "preset_id": "preset_3",
                    "import_format": "csv",
                },
            )
    finally:
        monkeypatch.setattr(app_module, "structured_fields_for_preset", original)

    assert response.status_code == 200
    payload = response.json()
    assert payload["required_fields"] == ["title", "subtitle"]


def test_batch_quotes_preview_preserves_structured_mode_with_clamped_count(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for name in ["001.png", "002.png", "003.png", "004.png", "005.png", "006.png"]:
        create_image(image_dir / name, (10, 10, 10, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "1. Name 1: Caption 1\n2. Name 2: Caption 2\n3. Name 3: Caption 3\n4. Name 4: Caption 4\n5. Name 5: Caption 5\n6. Name 6: Caption 6\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "sample_count": "0",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "structured"
    assert len(payload["previews"]) == 1


def test_batch_quotes_preview_rejects_malformed_structured_lines(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "Bad structured line without number and caption\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir), "preset_id": "preset_3"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Line 1 must contain a '.' separating the number and name fields."


def test_batch_quotes_generate_rejects_malformed_structured_lines(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "1. Missing name-only\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "output_dir": str(output_dir),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Line 1 must contain a ':' separating the name and caption fields."


def test_batch_structured_preview_count_mismatch_with_preset_3(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text("1. Only name: Single caption\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir), "preset_id": "preset_3"},
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == (
            "Batch mode expects one structured entry per image, but counts differ: "
            "found 2 images and 1 structured entries. "
            "Ensure every image has exactly one structured entry and retry."
        )
    )


def test_batch_structured_generate_success_with_preset_3(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "1. Skyline: Caption about peace\n2. Harbor: Caption about calm\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "output_dir": str(output_dir),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "structured"
    assert payload["saved_count"] == 2
    for file_path in payload["files"]:
        assert Path(file_path).exists()


def test_batch_quotes_generate_rejects_invalid_export_format(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(tmp_path / "out"),
                "format": "gif",
            },
        )

    assert response.status_code == 400
    assert "Unsupported export format" in response.json()["detail"]


def test_batch_quotes_generate_rejects_invalid_export_quality(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(tmp_path / "out"),
                "format": "webp",
                "quality": "0",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Quality must be between 1 and 100."


def test_batch_quotes_generate_rejects_invalid_filename_template(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(tmp_path / "out"),
                "format": "webp",
                "filename_template": "{bad_token}",
            },
        )

    assert response.status_code == 400
    assert "Unsupported filename token" in response.json()["detail"]


def test_batch_quotes_generate_respects_export_format_and_template(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("First quote\nSecond quote\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_1",
                "output_dir": str(output_dir),
                "format": "webp",
                "filename_template": "quote-{index}",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_count"] == 2
    assert payload["files"][0].endswith(".webp")
    assert payload["files"][1].endswith(".webp")
    assert Path(payload["files"][0]).name.startswith("quote-1")


def test_batch_generate_rejects_invalid_export_format(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\nName 2: Meaning 2\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "output_dir": str(tmp_path / "out"),
                "format": "gif",
            },
        )

    assert response.status_code == 400
    assert "Unsupported export format" in response.json()["detail"]


def test_batch_generate_rejects_invalid_export_quality(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\nName 2: Meaning 2\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "output_dir": str(tmp_path / "out"),
                "format": "webp",
                "quality": "0",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Quality must be between 1 and 100."


def test_batch_generate_rejects_invalid_filename_template(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "output_dir": str(tmp_path / "out"),
                "format": "jpg",
                "filename_template": "{bad_token}",
            },
        )

    assert response.status_code == 400
    assert "Unsupported filename token" in response.json()["detail"]


def test_batch_generate_respects_export_format_and_template(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\nName 2: Meaning 2\n", encoding="utf-8")
    out = tmp_path / "out"

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "output_dir": str(out),
                "format": "jpg",
                "quality": "88",
                "filename_template": "{source}-{index}",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_count"] == 2
    assert payload["files"][0].endswith(".jpg")
    assert payload["files"][1].endswith(".jpg")
    assert Path(payload["files"][0]).exists()
    assert Path(payload["files"][1]).exists()
    assert Path(payload["files"][0]).name.startswith("001-1")



def test_batch_preview_rejects_invalid_zones_json(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": "[invalid]",
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid zones JSON."


def test_batch_preview_rejects_non_list_zones_json(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": '{"zones": []}',
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Zones payload must be a list."


def test_batch_preview_rejects_text_path_to_non_file(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_dir = tmp_path / "a-directory"
    text_dir.mkdir()

    response = client.post(
        "/api/batch/preview",
        data={
            "image_dir": str(image_dir),
            "zones_json": json.dumps([]),
            "text_path": str(text_dir),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected text path is not a file."


def test_batch_preview_rejects_missing_text_file_or_path(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    response = client.post(
        "/api/batch/preview",
        data={
            "image_dir": str(image_dir),
            "zones_json": json.dumps([]),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload a text file or choose one from disk."


def test_batch_preview_rejects_nonexistent_text_path(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))

    response = client.post(
        "/api/batch/preview",
        data={
            "image_dir": str(image_dir),
            "zones_json": json.dumps([]),
            "text_path": str(tmp_path / "missing.txt"),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Selected text file was not found."


def test_batch_preview_rejects_invalid_utf8_text_file(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.bin"
    text_file.write_bytes(b"\xff\xfe\x00name: meaning\n")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.bin", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Text file must be UTF-8 encoded."


def test_batch_preview_accepts_sample_count_bounds(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for name in ["001.png", "002.png", "003.png", "004.png", "005.png", "006.png"]:
        create_image(image_dir / name, (10, 10, 10, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "Name 1: Meaning 1\nName 2: Meaning 2\nName 3: Meaning 3\nName 4: Meaning 4\nName 5: Meaning 5\nName 6: Meaning 6\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "sample_count": "-3",
            },
        )

    assert response.status_code == 200
    assert len(response.json()["previews"]) == 1

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "sample_count": "10",
            },
        )

    assert response.status_code == 200
    assert len(response.json()["previews"]) == 5


def test_batch_preview_count_is_clamped(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    for name in ["001.png", "002.png", "003.png", "004.png", "005.png", "006.png"]:
        create_image(image_dir / name, (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text(
        "Name 1: Meaning 1\nName 2: Meaning 2\nName 3: Meaning 3\nName 4: Meaning 4\nName 5: Meaning 5\nName 6: Meaning 6\n",
        encoding="utf-8",
    )

    with text_file.open("rb") as file_handle:
        preview_response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "sample_count": "0",
            },
        )
    assert preview_response.status_code == 200
    assert len(preview_response.json()["previews"]) == 1

    with text_file.open("rb") as file_handle:
        preview_response = client.post(
            "/api/batch/preview",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
                "sample_count": "9",
            },
        )
    assert preview_response.status_code == 200
    assert len(preview_response.json()["previews"]) == 5


def test_batch_structured_generate_count_mismatch_with_preset_3(tmp_path: Path):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "generated"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    create_image(image_dir / "002.png", (30, 30, 30, 255))

    text_file = tmp_path / "entries.txt"
    text_file.write_text("1. Only one: Missing mate\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "preset_id": "preset_3",
                "output_dir": str(output_dir),
            },
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == (
            "Batch mode expects one structured entry per image, but counts differ: "
            "found 2 images and 1 structured entries. "
            "Ensure every image has exactly one structured entry and retry."
        )
    )


def test_preview_single_requires_preset_when_no_overlay(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/preview",
            files={"image": ("single.png", image_file, "image/png")},
            data={"text": "Kala Bhairava"},
        )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Choose a preset when using single-image generation without an overlay override."
    )


def test_batch_quotes_endpoints_require_preset(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "quotes.txt"
    text_file.write_text("Only one quote\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        preview_response = client.post(
            "/api/batch/quotes/preview",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir)},
        )
    assert preview_response.status_code == 400
    assert (
        preview_response.json()["detail"]
        == "Choose a preset for preset-driven batch generation so the app knows how to map each text entry."
    )

    with text_file.open("rb") as file_handle:
        generate_response = client.post(
            "/api/batch/quotes/generate",
            files={"text_file": ("quotes.txt", file_handle, "text/plain")},
            data={"image_dir": str(image_dir)},
        )
    assert generate_response.status_code == 400
    assert (
        generate_response.json()["detail"]
        == "Choose a preset for preset-driven batch generation so the app knows how to map each text entry."
    )


def test_legacy_generic_batch_routes_are_deprecated():
    preview_route = next(route for route in app.routes if getattr(route, "path", None) == "/api/batch/preview")
    generate_route = next(
        route for route in app.routes if getattr(route, "path", None) == "/api/batch/generate"
    )

    assert preview_route.deprecated is True
    assert generate_route.deprecated is True
    assert (preview_route.summary or "").startswith("Legacy generic batch")
    assert (generate_route.summary or "").startswith("Legacy generic batch")


def test_preview_single_requires_image_input(tmp_path: Path):
    response = client.post(
        "/api/preview",
        data={"preset_id": "preset_1", "text": "Kala Bhairava"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide an uploaded image or an image path."


def test_generate_single_requires_image_input(tmp_path: Path):
    response = client.post(
        "/api/generate",
        data={"preset_id": "preset_1", "text": "Kala Bhairava", "output_dir": str(tmp_path)},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide an uploaded image or an image path."


def test_generate_single_rejects_missing_output_dir(tmp_path: Path):
    image_path = tmp_path / "single.png"
    create_image(image_path, (20, 20, 20, 255))

    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/generate",
            files={"image": ("single.png", image_file, "image/png")},
            data={"preset_id": "preset_1", "text": "Kala Bhairava"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Select an output folder."


def test_batch_generate_rejects_missing_output_dir(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    create_image(image_dir / "001.png", (10, 10, 10, 255))
    text_file = tmp_path / "entries.txt"
    text_file.write_text("Name 1: Meaning 1\n", encoding="utf-8")

    with text_file.open("rb") as file_handle:
        response = client.post(
            "/api/batch/generate",
            files={"text_file": ("entries.txt", file_handle, "text/plain")},
            data={
                "image_dir": str(image_dir),
                "zones_json": json.dumps([]),
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Select an output folder."
