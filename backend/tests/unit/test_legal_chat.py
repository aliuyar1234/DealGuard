"""
Unit tests for Legal Chat (AI-Jurist) services.

Tests cover:
- KnowledgeRetriever: RAG-based contract search
- LegalChatService: Chat orchestration
- Citation validation
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dealguard.shared.context import TenantContext, clear_tenant_context, set_tenant_context


@pytest.fixture(autouse=True)
def tenant_context():
    """Provide tenant context for legal chat services."""
    ctx = TenantContext(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        user_email="test@example.com",
        user_role="admin",
    )
    set_tenant_context(ctx)
    yield ctx
    clear_tenant_context()


class TestKnowledgeRetriever:
    """Tests for KnowledgeRetriever (RAG component)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_db, tenant_context):
        """Create KnowledgeRetriever instance."""
        from dealguard.domain.legal.knowledge_retriever import KnowledgeRetriever

        return KnowledgeRetriever(mock_db, organization_id=tenant_context.organization_id)

    @pytest.mark.asyncio
    async def test_search_contracts_by_query(self, retriever, mock_db):
        """Test searching contracts by query."""
        contract = MagicMock(
            id=uuid.uuid4(),
            filename="Mietvertrag.pdf",
            contract_type=None,
            contract_text="Die Kündigungsfrist beträgt 3 Monate.",
        )
        mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(contract, 1)]))

        with patch(
            "dealguard.domain.legal.knowledge_retriever.token_hashes_from_query",
            return_value=[b"x" * 32],
        ):
            results = await retriever.search_contracts("Kündigungsfrist", limit=5)

        assert len(results) == 1
        assert results[0].filename == "Mietvertrag.pdf"

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, retriever, mock_db):
        """Test search with empty query returns recent contracts."""
        contracts = [
            MagicMock(
                id=uuid.uuid4(),
                filename="Contract1.pdf",
                created_at=MagicMock(),
            )
        ]
        mock_db.execute.return_value = MagicMock(
            fetchall=MagicMock(
                return_value=[
                    MagicMock(
                        id=contracts[0].id,
                        filename=contracts[0].filename,
                        contract_type=None,
                        raw_text="Some contract text.",
                        relevance=0.5,
                    )
                ]
            )
        )

        results = await retriever.get_all_contracts(limit=5)

        assert results is not None

    @pytest.mark.asyncio
    async def test_search_returns_relevant_snippets(self, retriever, mock_db):
        """Test that search returns relevant text snippets."""
        contract_text = """
        Seite 1: Einleitung zum Vertrag.
        Seite 2: Die Kündigungsfrist beträgt 3 Monate zum Quartalsende.
        Seite 3: Zahlungsbedingungen.
        """
        contract = MagicMock(
            id=uuid.uuid4(),
            filename="Mietvertrag.pdf",
            contract_type=None,
            contract_text=contract_text,
        )
        mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(contract, 1)]))

        with patch(
            "dealguard.domain.legal.knowledge_retriever.token_hashes_from_query",
            return_value=[b"x" * 32],
        ):
            results = await retriever.search_contracts("Kündigungsfrist", limit=5)
        clauses = retriever.extract_relevant_clauses(results, "Kündigungsfrist")

        assert clauses is not None
        assert len(clauses) == 1
        assert "Kündigungsfrist" in clauses[0].clause_text


class TestCitationValidation:
    """Tests for citation validation."""

    def test_valid_citation_format(self):
        """Test valid citation parsing from JSON responses."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
            LegalAdvisorPromptV1,
        )

        prompt = LegalAdvisorPromptV1()
        response = {
            "answer": "Antwort mit [1].",
            "citations": [
                {
                    "number": 1,
                    "contract_id": "contract-1",
                    "contract_filename": "Mietvertrag.pdf",
                    "clause_text": "Die Kuendigungsfrist betraegt drei Monate.",
                    "page": 5,
                    "paragraph": "Abs. 1",
                }
            ],
            "confidence": 0.9,
            "requires_lawyer": False,
            "follow_up_questions": [],
        }

        parsed = prompt.parse_response(json.dumps(response))
        assert len(parsed.citations) == 1

    def test_invalid_citation_format(self):
        """Test invalid citation parsing returns no citations."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
            LegalAdvisorPromptV1,
        )

        prompt = LegalAdvisorPromptV1()
        parsed = prompt.parse_response("Not JSON at all")
        assert parsed.citations == []


class TestLegalChatService:
    """Tests for LegalChatService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def clause_context(self):
        """Create a sample clause context."""
        from dealguard.domain.legal.knowledge_retriever import ClauseContext

        return ClauseContext(
            contract_id=uuid.uuid4(),
            contract_filename="Mietvertrag.pdf",
            clause_text="Die Kuendigungsfrist betraegt drei Monate.",
            relevance_score=0.9,
            page=5,
            paragraph="Abs. 1",
        )

    @pytest.fixture
    def mock_ai_client(self, clause_context):
        """Create mock AI client."""
        from dealguard.infrastructure.ai.client import AIResponse

        response_payload = {
            "answer": "Die Kuendigungsfrist betraegt drei Monate.",
            "citations": [
                {
                    "number": 1,
                    "contract_id": str(clause_context.contract_id),
                    "contract_filename": clause_context.contract_filename,
                    "clause_text": clause_context.clause_text,
                    "page": clause_context.page,
                    "paragraph": clause_context.paragraph,
                }
            ],
            "confidence": 0.92,
            "requires_lawyer": False,
            "follow_up_questions": [],
        }

        mock = MagicMock()
        mock.complete = AsyncMock(
            return_value=AIResponse(
                content=json.dumps(response_payload),
                model="test-model",
                input_tokens=120,
                output_tokens=45,
                total_tokens=165,
                cost_cents=0.5,
                latency_ms=12.0,
            )
        )
        return mock

    @pytest.fixture
    def chat_service(self, mock_db, mock_ai_client, clause_context, tenant_context):
        """Create LegalChatService instance."""
        from dealguard.domain.legal.chat_service import LegalChatService
        from dealguard.domain.legal.company_profile import CompanyProfile

        with patch("dealguard.domain.legal.chat_service.get_ai_client") as mock_client_factory:
            mock_client_factory.return_value = mock_ai_client
            service = LegalChatService(
                mock_db,
                organization_id=tenant_context.organization_id,
                user_id=tenant_context.user_id,
            )

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        service.profile_service.get_profile = AsyncMock(
            return_value=CompanyProfile(company_name="ACME GmbH", jurisdiction="AT")
        )
        service.knowledge_retriever.build_context_for_question = AsyncMock(
            return_value=([clause_context], "kuendigungsfrist")
        )
        service._get_conversation_history = AsyncMock(return_value=[])

        return service

    @pytest.mark.asyncio
    async def test_ask_question_returns_response(self, chat_service, mock_db):
        """Test asking a question returns a response."""
        _ = mock_db
        response = await chat_service.ask_question("Was ist die Kuendigungsfrist?")

        assert response is not None
        assert response.answer

    @pytest.mark.asyncio
    async def test_ask_includes_citations(self, chat_service, mock_db):
        """Test that response includes citations."""
        _ = mock_db
        response = await chat_service.ask_question("Was ist die Kuendigungsfrist?")

        # Response should reference the contract
        assert response is not None
        assert response.citations

    @pytest.mark.asyncio
    async def test_ask_returns_confidence_score(self, chat_service, mock_db):
        """Test that response includes confidence score."""
        _ = mock_db
        response = await chat_service.ask_question("Komplexe rechtliche Frage")

        assert response is not None
        # Confidence should be between 0 and 1
        assert 0 <= response.confidence <= 1


class TestConversationManagement:
    """Tests for conversation management."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_db, tenant_context):
        """Test creating a new conversation."""
        from dealguard.domain.legal.chat_service import LegalChatService

        with patch("dealguard.domain.legal.chat_service.get_ai_client"):
            service = LegalChatService(
                mock_db,
                organization_id=tenant_context.organization_id,
                user_id=tenant_context.user_id,
            )

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        conversation = await service.create_conversation(title="Test Conversation")

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once_with(conversation)

    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, mock_db, tenant_context):
        """Test getting conversation messages."""
        from dealguard.domain.legal.chat_service import LegalChatService
        from dealguard.infrastructure.database.models.legal_chat import MessageRole

        with patch("dealguard.domain.legal.chat_service.get_ai_client"):
            service = LegalChatService(
                mock_db,
                organization_id=tenant_context.organization_id,
                user_id=tenant_context.user_id,
            )

        messages = [
            MagicMock(role=MessageRole.USER, content="Question"),
            MagicMock(role=MessageRole.ASSISTANT, content="Answer"),
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=messages)))
        )

        conversation_id = uuid.uuid4()
        result = await service._get_conversation_history(conversation_id)

        assert len(result) == 2


class TestCompanyProfileService:
    """Tests for CompanyProfileService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_company_profile(self, mock_db, tenant_context):
        """Test getting company profile."""
        from dealguard.domain.legal.company_profile import CompanyProfileService

        service = CompanyProfileService(mock_db, organization_id=tenant_context.organization_id)

        # Mock organization with settings
        org = MagicMock()
        org.settings = {
            "legal_profile": {
                "company_name": "ACME GmbH",
                "industry": "Technology",
                "company_size": "11-50",
            }
        }
        org.name = "ACME GmbH"
        mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=org))

        profile = await service.get_profile()

        assert profile is not None
        assert profile.company_name == "ACME GmbH"

    @pytest.mark.asyncio
    async def test_update_company_profile(self, mock_db, tenant_context):
        """Test updating company profile."""
        from dealguard.domain.legal.company_profile import (
            CompanyProfile,
            CompanyProfileService,
        )

        service = CompanyProfileService(mock_db, organization_id=tenant_context.organization_id)

        org = MagicMock(settings={})
        mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=org))
        mock_db.flush = AsyncMock()

        profile = CompanyProfile(
            company_name="New Name",
            industry="Finance",
        )
        await service.update_profile(profile)

        mock_db.flush.assert_called_once()
        assert org.settings["legal_profile"]["company_name"] == "New Name"


class TestAntiHallucination:
    """Tests for anti-hallucination mechanisms."""

    def test_prompt_includes_citation_requirement(self):
        """Test that system prompt requires citations."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
            LegalAdvisorPromptV1,
        )

        system_prompt = LegalAdvisorPromptV1().render_system()
        assert "ZITIERPFLICHT" in system_prompt or "citation" in system_prompt.lower()

    def test_prompt_warns_about_uncertainty(self):
        """Test that prompt instructs to express uncertainty."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
            LegalAdvisorPromptV1,
        )

        system_prompt = LegalAdvisorPromptV1().render_system()
        prompt_lower = system_prompt.lower()
        assert (
            "unsicher" in prompt_lower
            or "uncertain" in prompt_lower
            or "nicht sicher" in prompt_lower
        )

    def test_prompt_recommends_lawyer_for_complex_cases(self):
        """Test that prompt recommends lawyers for complex cases."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import (
            LegalAdvisorPromptV1,
        )

        system_prompt = LegalAdvisorPromptV1().render_system()
        assert "Anwalt" in system_prompt or "lawyer" in system_prompt.lower()


class TestLegalMessageModel:
    """Tests for LegalMessage database model."""

    def test_message_creation(self):
        """Test creating a legal message."""
        from dealguard.infrastructure.database.models.legal_chat import LegalMessage

        message = LegalMessage(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            role="assistant",
            content="Die Kündigungsfrist beträgt 3 Monate [Mietvertrag.pdf, S. 5].",
            message_metadata={
                "citations": [{"file": "Mietvertrag.pdf", "page": 5, "snippet": "...3 Monate..."}],
                "confidence": 0.92,
            },
        )

        assert message.role == "assistant"
        assert len(message.citations) == 1
        assert message.confidence == 0.92

    def test_conversation_creation(self):
        """Test creating a legal conversation."""
        from dealguard.infrastructure.database.models.legal_chat import LegalConversation

        conversation = LegalConversation(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            title="Fragen zum Mietvertrag",
        )

        assert conversation.title == "Fragen zum Mietvertrag"
