"""Backfill contract search tokens for existing data.

Contracts are stored encrypted at rest. Keyword search uses a separate token
index table (`contract_search_tokens`) that must be populated.

Usage:
    cd backend
    python scripts/backfill_contract_search_tokens.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import and_, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dealguard.config import get_settings
from dealguard.infrastructure.database.models.contract import Contract
from dealguard.infrastructure.database.models.contract_search import ContractSearchToken
from dealguard.shared.search_tokens import token_hashes_from_text


async def _backfill(*, batch_size: int) -> int:
    settings = get_settings()
    engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    processed = 0
    async with session_factory() as session:
        while True:
            missing_ids_stmt = (
                select(Contract.id)
                .outerjoin(
                    ContractSearchToken,
                    and_(
                        ContractSearchToken.organization_id == Contract.organization_id,
                        ContractSearchToken.contract_id == Contract.id,
                    ),
                )
                .where(Contract.deleted_at.is_(None))
                .where(Contract._raw_text_encrypted.is_not(None))
                .where(ContractSearchToken.contract_id.is_(None))
                .order_by(Contract.created_at.asc())
                .limit(batch_size)
            )
            missing_ids_result = await session.execute(missing_ids_stmt)
            contract_ids = [row[0] for row in missing_ids_result.all()]
            if not contract_ids:
                break

            contracts_result = await session.execute(
                select(Contract).where(Contract.id.in_(contract_ids))
            )
            contracts = contracts_result.scalars().all()

            for contract in contracts:
                contract_text = contract.contract_text
                if not contract_text:
                    continue

                await session.execute(
                    delete(ContractSearchToken).where(
                        ContractSearchToken.organization_id == contract.organization_id,
                        ContractSearchToken.contract_id == contract.id,
                    )
                )

                hashes = token_hashes_from_text(contract_text)
                if hashes:
                    await session.execute(
                        insert(ContractSearchToken),
                        [
                            {
                                "organization_id": contract.organization_id,
                                "token_hash": token_hash,
                                "contract_id": contract.id,
                            }
                            for token_hash in hashes
                        ],
                    )

                processed += 1

            await session.commit()

    await engine.dispose()
    return processed


def main() -> None:
    batch_size = int(os.getenv("DEALGUARD_SEARCH_BACKFILL_BATCH_SIZE", "50"))
    processed = asyncio.run(_backfill(batch_size=batch_size))
    print(f"Backfilled search tokens for {processed} contract(s).")


if __name__ == "__main__":
    main()
