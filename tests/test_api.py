import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app import app


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
    assert payload["helper_text"] == "Presets are defined in the local app config file."


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


def test_browse_valid_path(tmp_path: Path):
    response = client.get("/api/browse", params={"path": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    assert "folders" in payload
    assert payload["current"] == str(tmp_path.resolve())


def test_browse_invalid_path():
    response = client.get("/api/browse", params={"path": "Z:\\this\\path\\should\\not\\exist"})
    assert response.status_code == 400


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
