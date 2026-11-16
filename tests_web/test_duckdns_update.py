from __future__ import annotations

from urllib.request import Request

import pytest

from deploy.oracle.duckdns_update import (
    DuckDnsUpdateError,
    make_update_request,
    update_duckdns,
)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _size: int) -> bytes:
        return self.body


def test_duckdns_request_contains_expected_fields() -> None:
    request = make_update_request("my-video-app", "12345678-1234-1234-1234-123456789abc")

    assert isinstance(request, Request)
    assert request.full_url.startswith("https://www.duckdns.org/update?")
    assert "domains=my-video-app" in request.full_url
    assert "ip=" in request.full_url


def test_duckdns_update_accepts_ok_from_mock() -> None:
    captured: dict[str, object] = {}

    def open_mock(request: Request, *, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(b"OK\n")

    update_duckdns("my-video-app", "12345678-1234-1234-1234-123456789abc", opener=open_mock)

    assert captured["timeout"] == 15
    assert isinstance(captured["request"], Request)


@pytest.mark.parametrize(
    ("domain", "token"),
    [
        ("full.domain.example", "12345678-1234-1234-1234-123456789abc"),
        ("valid-domain", "short"),
        ("-invalid", "12345678-1234-1234-1234-123456789abc"),
    ],
)
def test_invalid_duckdns_input_is_rejected_before_network(domain: str, token: str) -> None:
    def should_not_open(*_: object, **__: object) -> FakeResponse:
        pytest.fail("Invalid input must not reach the network.")

    with pytest.raises(DuckDnsUpdateError):
        update_duckdns(domain, token, opener=should_not_open)


def test_duckdns_rejection_does_not_echo_token() -> None:
    secret = "12345678-1234-1234-1234-123456789abc"

    with pytest.raises(DuckDnsUpdateError) as error:
        update_duckdns(
            "my-video-app",
            secret,
            opener=lambda *_args, **_kwargs: FakeResponse(b"KO\n"),
        )

    assert secret not in str(error.value)
