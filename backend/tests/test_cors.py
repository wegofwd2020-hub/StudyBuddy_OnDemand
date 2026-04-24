"""
backend/tests/test_cors.py

Parity with Thittam's pkg/corsutil tests — same inputs, same expected
outputs. FastAPI's CORSMiddleware consumes the regex directly, so these
tests exercise the regex via re.fullmatch() rather than a callable wrapper.
"""

from __future__ import annotations

import re

import pytest

from src.core.cors import build_lan_origin_regex, parse_extra_origins


@pytest.fixture(scope="module")
def lan_regex() -> re.Pattern[str]:
    return re.compile(build_lan_origin_regex())


def _allows(regex: re.Pattern[str], origin: str) -> bool:
    return regex.fullmatch(origin) is not None


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        # Accepted — loopback + RFC-1918 on allowed web ports.
        ("http://localhost:3000", True),
        ("http://localhost:3010", True),
        ("http://127.0.0.1:3000", True),
        ("http://192.168.68.55:3000", True),
        ("http://10.0.0.5:3010", True),
        ("http://172.16.4.2:3000", True),
        ("http://172.31.255.1:3000", True),
        ("http://[::1]:3000", True),
        # Wrong port.
        ("http://localhost:3200", False),
        ("http://192.168.1.1:8080", False),
        # Wrong scheme — https intentionally out of scope for LAN.
        ("https://localhost:3000", False),
        # Public IPs and just-outside-RFC-1918 ranges.
        ("http://8.8.8.8:3000", False),
        ("http://172.32.0.1:3000", False),
        ("http://example.com:3000", False),
        # Garbage.
        ("", False),
        ("not-a-url", False),
        ("http://:3000", False),
    ],
)
def test_lan_origin_regex(lan_regex: re.Pattern[str], origin: str, expected: bool) -> None:
    assert _allows(lan_regex, origin) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, []),
        ("", []),
        ("https://a.example.com", ["https://a.example.com"]),
        (
            "https://a.example.com,https://b.example.com",
            ["https://a.example.com", "https://b.example.com"],
        ),
        (
            " https://a.example.com , ,https://b.example.com  ",
            ["https://a.example.com", "https://b.example.com"],
        ),
    ],
)
def test_parse_extra_origins(value: str | None, expected: list[str]) -> None:
    assert parse_extra_origins(value) == expected
