import re
from urllib.parse import parse_qs, urlsplit

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]{10,150}$")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
MAX_INPUT_URLS = 100


class ValidationError(ValueError):
    pass


def validate_url(value: str) -> str:
    """Accept only explicit public YouTube URL shapes, never arbitrary hosts."""
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 80, 443}
        ):
            raise ValueError
        query = parse_qs(parsed.query)
        video = None
        playlist = None
        if parsed.hostname == "youtu.be":
            video = parsed.path.strip("/")
        elif parsed.hostname in HOSTS:
            if parsed.path == "/watch":
                video = query.get("v", [""])[0]
            elif parsed.path.startswith(("/shorts/", "/live/", "/embed/")):
                video = parsed.path.strip("/").split("/")[1]
            elif parsed.path == "/playlist":
                playlist = query.get("list", [""])[0]
        if video is not None and VIDEO_ID.fullmatch(video):
            # A watch URL with list= is a single video; explicit /playlist means a batch.
            return f"https://www.youtube.com/watch?v={video}"
        if playlist is not None and PLAYLIST_ID.fullmatch(playlist):
            return f"https://www.youtube.com/playlist?list={playlist}"
    except (ValueError, IndexError):
        pass
    raise ValidationError(f"URL de YouTube no válida: {value[:180]}")


def parse_urls(text: str) -> list[str]:
    values = text.split()
    if not values:
        raise ValidationError("Pega al menos un enlace de YouTube.")
    if len(values) > MAX_INPUT_URLS:
        raise ValidationError(f"Introduce como máximo {MAX_INPUT_URLS} enlaces por análisis.")
    return list(dict.fromkeys(validate_url(value) for value in values))
