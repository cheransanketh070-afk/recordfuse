"""Field-specific normalisation with a pluggable registry."""

from __future__ import annotations

import contextlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize(
        "NFKD",
        _text(value),
    )

    text = "".join(
        ch
        for ch in text
        if not unicodedata.combining(ch)
    )

    text = re.sub(
        r"[^a-zA-Z0-9 ]+",
        " ",
        text.casefold(),
    )

    return " ".join(text.split())


def normalize_email(value: Any) -> str:
    """Normalise email conservatively without provider-specific alias rewriting."""
    text = _text(value).casefold()

    if "@" not in text:
        return text

    local, domain = text.rsplit("@", 1)

    with contextlib.suppress(UnicodeError):
        domain = domain.encode("idna").decode("ascii")

    return f"{local}@{domain}"


def normalize_phone(value: Any) -> str:
    text = re.sub(
        r"\D+",
        "",
        _text(value),
    )

    return (
        text[2:]
        if text.startswith("00")
        else text
    )


def normalize_address(value: Any) -> str:
    text = unicodedata.normalize(
        "NFKD",
        _text(value),
    )

    text = "".join(
        ch
        for ch in text
        if not unicodedata.combining(ch)
    )

    text = re.sub(
        r"[^\w\s]",
        " ",
        text.casefold(),
    )

    replacements = {
        "street": "st",
        "road": "rd",
        "avenue": "ave",
        "boulevard": "blvd",
    }

    tokens = [
        replacements.get(token, token)
        for token in text.split()
    ]

    return " ".join(tokens)


def normalize_generic(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        _text(value).casefold(),
    )


class NormalizerRegistry:
    """Map field names to normalisers; custom fields can be registered at runtime."""

    def __init__(self) -> None:
        self._normalizers: dict[str, Callable[[Any], str]] = {
            "name": normalize_name,
            "email": normalize_email,
            "phone": normalize_phone,
            "address": normalize_address,
        }

    def register(
        self,
        field: str,
        fn: Callable[[Any], str],
    ) -> None:
        if not field:
            raise ValueError(
                "field name cannot be empty"
            )

        self._normalizers[field] = fn

    def normalize(
        self,
        field: str,
        value: Any,
    ) -> str:
        return self._normalizers.get(
            field,
            normalize_generic,
        )(value)
