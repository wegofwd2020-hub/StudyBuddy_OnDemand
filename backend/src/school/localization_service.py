"""
School localization service — currency, timezone, number formatting.

Maps country codes to standard prefixes (currency symbol, thousands separator,
decimal separator, timezone) fetched from CLDR or a local mapping. Stores on
school registration/update.
"""

from __future__ import annotations

from typing import TypedDict

import asyncpg

# Localization data: country_code → (currency_code, symbol, thousands_sep, decimal_sep, timezone)
# Source: CLDR. Manually maintained fallback for core markets.
_COUNTRY_LOCALIZATION: dict[str, tuple[str, str, str, str, str]] = {
    "US": ("USD", "$", ",", ".", "America/New_York"),
    "GB": ("GBP", "£", ",", ".", "Europe/London"),
    "IN": ("INR", "₹", ",", ".", "Asia/Kolkata"),
    "CA": ("CAD", "$", ",", ".", "America/Toronto"),
    "AU": ("AUD", "$", ",", ".", "Australia/Sydney"),
    "FR": ("EUR", "€", " ", ",", "Europe/Paris"),
    "DE": ("EUR", "€", ".", ",", "Europe/Berlin"),
    "JP": ("JPY", "¥", ",", ".", "Asia/Tokyo"),
    "CN": ("CNY", "¥", ",", ".", "Asia/Shanghai"),
    "BR": ("BRL", "R$", ".", ",", "America/Sao_Paulo"),
    "MX": ("MXN", "$", ",", ".", "America/Mexico_City"),
}

_DEFAULT_COUNTRY = "US"


class SchoolLocalization(TypedDict):
    """School localization configuration."""

    country_code: str
    currency_code: str
    currency_symbol: str
    thousands_separator: str
    decimal_separator: str
    timezone: str


def get_localization_for_country(country_code: str | None) -> SchoolLocalization:
    """
    Fetch localization prefixes for a country. Fallback to USA if not found.
    """
    country = country_code or _DEFAULT_COUNTRY
    country_upper = country.upper()

    if country_upper not in _COUNTRY_LOCALIZATION:
        country_upper = _DEFAULT_COUNTRY

    currency_code, symbol, thousands_sep, decimal_sep, timezone = _COUNTRY_LOCALIZATION[
        country_upper
    ]

    return SchoolLocalization(
        country_code=country_upper,
        currency_code=currency_code,
        currency_symbol=symbol,
        thousands_separator=thousands_sep,
        decimal_separator=decimal_sep,
        timezone=timezone,
    )


async def infer_country_from_ip(ip_addr: str | None) -> str:
    """
    Infer country from IP geolocation (stub for external integration).
    Returns country code or None if unable to determine.
    """
    # TODO: integrate GeoIP2 / MaxMind when IP is available
    return None


async def get_or_create_school_localization(
    conn: asyncpg.Connection,
    school_id: str,
    country_code: str | None,
    ip_addr: str | None = None,
) -> SchoolLocalization:
    """
    Get existing school localization, or create from country code.

    Fallback chain:
    1. User-provided country_code
    2. Inferred from IP geolocation
    3. Default to USA
    """
    # Check if already exists
    existing = await conn.fetchrow(
        "SELECT * FROM school_localization WHERE school_id = $1",
        school_id,
    )
    if existing:
        return SchoolLocalization(
            country_code=existing["country_code"],
            currency_code=existing["currency_code"],
            currency_symbol=existing["currency_symbol"],
            thousands_separator=existing["thousands_separator"],
            decimal_separator=existing["decimal_separator"],
            timezone=existing["timezone"],
        )

    # Determine country via fallback chain
    determined_country = country_code
    if not determined_country and ip_addr:
        determined_country = await infer_country_from_ip(ip_addr)
    if not determined_country:
        determined_country = _DEFAULT_COUNTRY

    # Fetch localization for country
    loc = get_localization_for_country(determined_country)

    # Insert into DB
    await conn.execute(
        """
        INSERT INTO school_localization
        (school_id, country_code, currency_code, currency_symbol, thousands_separator, decimal_separator, timezone)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (school_id) DO UPDATE SET
            country_code = $2, currency_code = $3, currency_symbol = $4,
            thousands_separator = $5, decimal_separator = $6, timezone = $7
        """,
        school_id,
        loc["country_code"],
        loc["currency_code"],
        loc["currency_symbol"],
        loc["thousands_separator"],
        loc["decimal_separator"],
        loc["timezone"],
    )

    return loc


async def get_school_localization(
    conn: asyncpg.Connection,
    school_id: str,
) -> SchoolLocalization | None:
    """Fetch school localization, or None if not found."""
    row = await conn.fetchrow(
        "SELECT * FROM school_localization WHERE school_id = $1",
        school_id,
    )
    if not row:
        return None

    return SchoolLocalization(
        country_code=row["country_code"],
        currency_code=row["currency_code"],
        currency_symbol=row["currency_symbol"],
        thousands_separator=row["thousands_separator"],
        decimal_separator=row["decimal_separator"],
        timezone=row["timezone"],
    )
