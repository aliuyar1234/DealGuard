"""Integration test for queue -> worker -> status flow."""

import json
import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dealguard.config import get_settings
from dealguard.domain.contracts.services import ContractAnalysisService
from dealguard.infrastructure.database.models.contract import (
    AnalysisStatus,
    Contract,
    ContractType,
)
from dealguard.infrastructure.database.models.organization import Organization, PlanTier
from dealguard.infrastructure.database.models.user import User, UserRole
from dealguard.infrastructure.database.repositories.contract import (
    ContractAnalysisRepository,
    ContractRepository,
)
from dealguard.infrastructure.queue.client import enqueue_contract_analysis
from dealguard.infrastructure.queue.worker import JobState, analyze_contract_job
from dealguard.shared.context import TenantContext, set_tenant_context

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-encryption-32chars")
get_settings.cache_clear()


@dataclass
class FakeAIResponse:
    content: str
    model: str = "claude-test"
    input_tokens: int = 120
    output_tokens: int = 45
    cost_cents: float = 0.5


class FakeAIClient:
    async def analyze_contract(self, contract_text, contract_type, resource_id=None):
        response = {
            "contract_type_detected": "service",
            "risk_score": 15,
            "risk_level": "low",
            "summary": "Test analysis summary.",
            "findings": [
                {
                    "category": "liability",
                    "severity": "low",
                    "title": "Begrenzte Haftung",
                    "description": "Haftung ist begrenzt.",
                    "original_clause_text": "Haftung ist begrenzt.",
                    "clause_location": {"page": 1, "paragraph": "1"},
                    "suggested_change": "Keine Aenderung notwendig.",
                    "market_comparison": "Marktueblich.",
                }
            ],
            "recommendations": [
                "Empfehlung 1",
                "Empfehlung 2",
                "Empfehlung 3",
            ],
        }
        return FakeAIResponse(content=json.dumps(response))


@pytest.mark.asyncio
async def test_enqueue_to_worker_updates_status(async_session):
    org = Organization(
        id=uuid4(),
        name="Queue Test Org",
        slug=f"queue-test-{uuid4().hex[:8]}",
        plan_tier=PlanTier.BUSINESS,
        settings={},
    )
    user = User(
        id=uuid4(),
        organization_id=org.id,
        supabase_user_id=f"supabase-{uuid4().hex}",
        email="queue-test@example.com",
        full_name="Queue Test",
        role=UserRole.ADMIN,
    )

    async_session.add_all([org, user])
    await async_session.commit()

    set_tenant_context(
        TenantContext(
            organization_id=org.id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
        )
    )

    contract_repo = ContractRepository(async_session)
    analysis_repo = ContractAnalysisRepository(async_session)

    contract = Contract(
        created_by=user.id,
        filename="test.pdf",
        file_path="contracts/test.pdf",
        file_hash="hash123",
        file_size_bytes=1234,
        mime_type="application/pdf",
        page_count=1,
        contract_type=ContractType.SERVICE,
        status=AnalysisStatus.PENDING,
    )
    contract._raw_text_encrypted = "Test contract content."

    await contract_repo.create(contract)
    await async_session.commit()

    with patch(
        "dealguard.infrastructure.queue.client.enqueue_job",
        new_callable=AsyncMock,
    ) as mock_enqueue:
        mock_enqueue.return_value = "job-123"
        job_id = await enqueue_contract_analysis(
            contract_id=contract.id,
            organization_id=org.id,
            user_id=user.id,
        )
        assert job_id == "job-123"

    service = ContractAnalysisService(
        contract_repo=contract_repo,
        analysis_repo=analysis_repo,
        ai_client=FakeAIClient(),
        storage=MagicMock(),
        extractor=MagicMock(),
    )

    ctx = {"job_state": JobState(session=async_session, contract_service=service)}
    result = await analyze_contract_job(
        ctx,
        contract_id=str(contract.id),
        organization_id=str(org.id),
        user_id=str(user.id),
    )

    await async_session.commit()

    assert result["status"] == "completed"

    set_tenant_context(
        TenantContext(
            organization_id=org.id,
            user_id=user.id,
            user_email=user.email,
            user_role=user.role,
        )
    )

    updated = await contract_repo.get_by_id(contract.id)
    assert updated is not None
    assert updated.status == AnalysisStatus.COMPLETED

    analysis = await analysis_repo.get_by_contract_id(contract.id)
    assert analysis is not None
