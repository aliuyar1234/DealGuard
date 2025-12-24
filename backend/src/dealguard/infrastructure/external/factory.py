"""Factories for external service providers.

These providers can hold network clients (e.g., httpx.AsyncClient). Creating them
per-request is expensive and can leak resources if not closed.
"""

from __future__ import annotations

import inspect
from typing import Any

from dealguard.config import Settings
from dealguard.infrastructure.external.mock_provider import (
    MockCompanyProvider,
    MockCreditProvider,
    MockInsolvencyProvider,
    MockSanctionProvider,
)
from dealguard.infrastructure.external.openfirmenbuch import OpenFirmenbuchProvider
from dealguard.infrastructure.external.opensanctions import OpenSanctionsProvider


def build_partner_providers(settings: Settings) -> dict[str, object]:
    if settings.is_development:
        return {
            "company_provider": MockCompanyProvider(),
            "credit_provider": MockCreditProvider(),
            "sanction_provider": MockSanctionProvider(),
            "insolvency_provider": MockInsolvencyProvider(),
        }

    return {
        "company_provider": OpenFirmenbuchProvider(),
        "credit_provider": MockCreditProvider(),
        "sanction_provider": OpenSanctionsProvider(),
        "insolvency_provider": MockInsolvencyProvider(),
    }


async def close_providers(providers: dict[str, object] | None) -> None:
    if not providers:
        return

    for provider in providers.values():
        close = getattr(provider, "close", None)
        if close is None:
            continue
        if inspect.iscoroutinefunction(close):
            await close()
        else:
            close()


def get_provider(providers: dict[str, object], key: str) -> Any:
    try:
        return providers[key]
    except KeyError as exc:
        raise KeyError(f"Missing provider: {key}") from exc
