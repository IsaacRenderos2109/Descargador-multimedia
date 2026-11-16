"""Refresh one DuckDNS A record without logging its credential."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DUCKDNS_ENDPOINT = "https://www.duckdns.org/update"
DOMAIN_PATTERN = re.compile(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\Z")
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9-]{16,128}\Z")


class DuckDnsUpdateError(ValueError):
    """A DuckDNS update was rejected or its credentials were invalid."""


def make_update_request(domain: str, token: str) -> Request:
    """Build the HTTPS request after validating non-secret input fields."""
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise DuckDnsUpdateError("DuckDNS domain must be a single subdomain label.")
    if not TOKEN_PATTERN.fullmatch(token):
        raise DuckDnsUpdateError("DuckDNS token has an invalid format.")
    query = urlencode({"domains": domain, "token": token, "ip": ""})
    return Request(
        f"{DUCKDNS_ENDPOINT}?{query}",
        headers={"User-Agent": "video-downloader-duckdns-updater/1.0"},
    )


def update_duckdns(
    domain: str,
    token: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> None:
    """Send an update and fail closed unless DuckDNS replies with ``OK``."""
    request = make_update_request(domain, token)
    open_request = urlopen if opener is None else opener
    with open_request(request, timeout=15) as response:
        result = response.read(16).decode("ascii", errors="replace").strip()
    if result != "OK":
        raise DuckDnsUpdateError("DuckDNS rejected the record update.")


def main() -> int:
    domain = os.environ.get("DUCKDNS_DOMAIN", "")
    token = os.environ.get("DUCKDNS_TOKEN", "")
    try:
        update_duckdns(domain, token)
    except Exception:
        # Do not print an exception or URL; urllib errors can include the token.
        print(
            "DuckDNS update failed; check service logs, connectivity, domain, and token.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
