import pytest

from video_downloader.validation import ValidationError, parse_urls, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "https://youtu.be/abcdefghijk?t=4",
        "https://www.youtube.com/watch?v=abcdefghijk&list=PL1234567890",
        "https://youtube.com/shorts/abcdefghijk",
        "https://m.youtube.com/live/abcdefghijk",
        "https://www.youtube.com/embed/abcdefghijk",
        "http://music.youtube.com/watch?v=abcdefghijk",
    ],
)
def test_canonical_video_url(url):
    assert validate_url(url) == "https://www.youtube.com/watch?v=abcdefghijk"


def test_playlist_and_deduplication():
    assert validate_url("https://youtube.com/playlist?list=PL1234567890&si=tracking") == (
        "https://www.youtube.com/playlist?list=PL1234567890"
    )
    assert (
        len(parse_urls("https://youtu.be/abcdefghijk\nhttps://youtube.com/watch?v=abcdefghijk"))
        == 1
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///etc/passwd",
        "https://youtube.com.evil.test/watch?v=abcdefghijk",
        "https://youtube.com@evil.test/watch?v=abcdefghijk",
        "https://evil.test/abcdefghijk",
        "https://youtube.com/watch?v=short",
        "https://youtu.be/../../file",
        "javascript:alert(1)",
        "https://youtube.com:bad/watch?v=abcdefghijk",
        "https://youtube.com:123/watch?v=abcdefghijk",
        "https://user:pass@youtube.com/watch?v=abcdefghijk",
        "https://youtube.com/channel/abcdefghijk",
        "https://youtube.com/playlist?list=bad",
        "https://youtu.be/abcdefghijk/extra",
    ],
)
def test_reject_invalid_urls(url):
    with pytest.raises(ValidationError):
        validate_url(url)


def test_empty_and_oversized_batch():
    for text in ("  \n", "https://youtu.be/abcdefghijk " * 101):
        with pytest.raises(ValidationError):
            parse_urls(text)
