"""Pruebas aisladas del contrato actual de la CLI, sin descargas de red."""
from pathlib import Path

from app import ALLOWED_FORMATS, build_output_template, normalize_urls


def test_formats_include_audio_and_video():
    assert {"mp3", "m4a", "wav", "flac", "opus", "mp4", "webm", "mkv"} <= ALLOWED_FORMATS


def test_normalize_urls_discards_blank_lines_and_trims_space():
    assert normalize_urls(["  https://example.org/a  ", "", "  ", "https://example.org/b"]) == [
        "https://example.org/a", "https://example.org/b"
    ]


def test_default_output_uses_media_title(tmp_path: Path):
    template = build_output_template(tmp_path / "media", None)
    assert template == str(tmp_path / "media" / "%(title)s.%(ext)s")
    assert (tmp_path / "media").is_dir()


def test_custom_output_for_batch_prevents_same_name(tmp_path: Path):
    template = build_output_template(tmp_path, "mi_archivo", url_count=3)
    assert template == str(tmp_path / "mi_archivo_%(autonumber)s.%(ext)s")


def test_custom_output_for_single_url(tmp_path: Path):
    template = build_output_template(tmp_path, "mi_archivo", url_count=1)
    assert template == str(tmp_path / "mi_archivo.%(ext)s")
