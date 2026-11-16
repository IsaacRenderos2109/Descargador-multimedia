import json
import shutil
import subprocess

import pytest
import yt_dlp
from yt_dlp.postprocessor.ffmpeg import FFmpegExtractAudioPP, FFmpegVideoConvertorPP

pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg/FFprobe no disponibles",
)


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"]


def test_real_audio_postprocessor(tmp_path):
    source = tmp_path / "synthetic.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=0.3", str(source)], check=True
    )
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        processor = FFmpegExtractAudioPP(ydl, preferredcodec="mp3", preferredquality="192")
        _, result = processor.run({"filepath": str(source), "ext": "wav", "vcodec": "none"})
    streams = probe(result["filepath"])
    assert streams[0]["codec_name"] == "mp3"


def test_real_video_postprocessor(tmp_path):
    source = tmp_path / "synthetic.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=640x360:d=0.3",
            "-c:v",
            "libx264",
            str(source),
        ],
        check=True,
    )
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        processor = FFmpegVideoConvertorPP(ydl, preferedformat="mp4")
        _, result = processor.run({"filepath": str(source), "ext": "mkv", "vcodec": "h264"})
    assert result["filepath"].endswith(".mp4")
    assert probe(result["filepath"])[0]["height"] == 360
