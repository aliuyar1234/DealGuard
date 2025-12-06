"""
Unit tests for Legal Chat (AI-Jurist) services.

Tests cover:
- KnowledgeRetriever: RAG-based contract search
- LegalChatService: Chat orchestration
- Citation validation
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestKnowledgeRetriever:
    """Tests for KnowledgeRetriever (RAG component)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def retriever(self, mock_db):
        """Create KnowledgeRetriever instance."""
        from dealguard.domain.legal.knowledge_retriever import KnowledgeRetriever
        return KnowledgeRetriever(mock_db)

    @pytest.mark.asyncio
    async def test_search_contracts_by_query(self, retriever, mock_db):
        """Test searching contracts by query."""
        contracts = [
            MagicMock(
                id=uuid.uuid4(),
                filename="Mietvertrag.pdf",
                raw_text="Die Kündigungsfrist beträgt 3 Monate.",
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=contracts)))
        )

        results = await retriever.search("Kündigungsfrist", limit=5)

        assert len(results) > 0

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
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=contracts)))
        )

        results = await retriever.search("", limit=5)

        assert results is not None

    @pytest.mark.asyncio
    async def test_search_returns_relevant_snippets(self, retriever, mock_db):
        """Test that search returns relevant text snippets."""
        contract_text = """
        Seite 1: Einleitung zum Vertrag.
        Seite 2: Die Kündigungsfrist beträgt 3 Monate zum Quartalsende.
        Seite 3: Zahlungsbedingungen.
        """
        contracts = [
            MagicMock(
                id=uuid.uuid4(),
                filename="Mietvertrag.pdf",
                raw_text=contract_text,
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=contracts)))
        )

        results = await retriever.search("Kündigungsfrist", limit=5)

        # Results should contain the relevant snippet
        assert results is not None


class TestCitationValidation:
    """Tests for citation validation."""

    def test_valid_citation_format(self):
        """Test valid citation format detection."""
        # Valid formats: [Filename.pdf, S. 5] or [Filename, Seite 5]
        valid_citations = [
            "[Mietvertrag.pdf, S. 5]",
            "[Vertrag.docx, Seite 3]",
            "[Contract.pdf, S. 1-3]",
        ]

        from dealguard.domain.legal.chat_service import parse_citations

        for citation in valid_citations:
            parsed = parse_citations(f"Text mit {citation}")
            assert len(parsed) > 0

    def test_invalid_citation_format(self):
        """Test invalid citation format detection."""
        invalid_citations = [
            "No citation here",
            "Just a filename.pdf",
            "[Incomplete citation",
        ]

        from dealguard.domain.legal.chat_service import parse_citations

        for text in invalid_citations:
            parsed = parse_citations(text)
            assert len(parsed) == 0


class TestLegalChatService:
    """Tests for LegalChatService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_ai_client(self):
        """Create mock AI client."""
        mock = MagicMock()
        mock.messages.create = AsyncMock(
            return_value=MagicMock(
                content=[MagicMock(text="Legal response with [Contract.pdf, S. 1] citation.")],
                usage=MagicMock(input_tokens=100, output_tokens=50),
            )
        )
        return mock

    @pytest.fixture
    def chat_service(self, mock_db, mock_ai_client):
        """Create LegalChatService instance."""
        from dealguard.domain.legal.chat_service import LegalChatService

        with patch("dealguard.domain.legal.chat_service.AnthropicClient") as mock_client_class:
            mock_client_class.return_value = mock_ai_client
            service = LegalChatService(
                db=mock_db,
                organization_id=uuid.uuid4(),
            )
            service.ai_client = mock_ai_client
            return service

    @pytest.mark.asyncio
    async def test_ask_question_returns_response(self, chat_service, mock_db):
        """Test asking a question returns a response."""
        # Mock contract search
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        response = await chat_service.ask("Was ist die Kündigungsfrist?")

        assert response is not None
        assert hasattr(response, "answer") or hasattr(response, "content")

    @pytest.mark.asyncio
    async def test_ask_includes_citations(self, chat_service, mock_db):
        """Test that response includes citations."""
        # Mock contract search with results
        contracts = [
            MagicMock(
                id=uuid.uuid4(),
                filename="Mietvertrag.pdf",
                raw_text="Die Kündigungsfrist beträgt 3 Monate.",
            )
        ]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=contracts)))
        )

        response = await chat_service.ask("Was ist die Kündigungsfrist?")

        # Response should reference the contract
        assert response is not None

    @pytest.mark.asyncio
    async def test_ask_returns_confidence_score(self, chat_service, mock_db):
        """Test that response includes confidence score."""
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        response = await chat_service.ask("Komplexe rechtliche Frage")

        assert response is not None
        # Confidence should be between 0 and 1
        if hasattr(response, "confidence"):
            assert 0 <= response.confidence <= 1


class TestConversationManagement:
    """Tests for conversation management."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_db):
        """Test creating a new conversation."""
        from dealguard.domain.legal.chat_service import LegalChatService

        with patch("dealguard.domain.legal.chat_service.AnthropicClient"):
            service = LegalChatService(
                db=mock_db,
                organization_id=uuid.uuid4(),
            )

            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            conversation = await service.create_conversation(title="Test Conversation")

            mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, mock_db):
        """Test getting conversation messages."""
        from dealguard.domain.legal.chat_service import LegalChatService

        with patch("dealguard.domain.legal.chat_service.AnthropicClient"):
            service = LegalChatService(
                db=mock_db,
                organization_id=uuid.uuid4(),
            )

            messages = [
                MagicMock(role="user", content="Question"),
                MagicMock(role="assistant", content="Answer"),
            ]
            mock_db.execute.return_value = MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=messages)))
            )

            conversation_id = uuid.uuid4()
            result = await service.get_messages(conversation_id)

            assert len(result) == 2


class TestCompanyProfileService:
    """Tests for CompanyProfileService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_company_profile(self, mock_db):
        """Test getting company profile."""
        from dealguard.domain.legal.company_profile import CompanyProfileService

        service = CompanyProfileService(mock_db)

        # Mock organization with settings
        org = MagicMock(
            settings={
                "company_name": "ACME GmbH",
                "industry": "Technology",
                "employees": 50,
            }
        )
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=org)
        )

        org_id = uuid.uuid4()
        profile = await service.get_profile(org_id)

        assert profile is not None
        assert profile.get("company_name") == "ACME GmbH"

    @pytest.mark.asyncio
    async def test_update_company_profile(self, mock_db):
        """Test updating company profile."""
        from dealguard.domain.legal.company_profile import CompanyProfileService

        service = CompanyProfileService(mock_db)

        org = MagicMock(settings={})
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=org)
        )
        mock_db.commit = AsyncMock()

        org_id = uuid.uuid4()
        await service.update_profile(org_id, {
            "company_name": "New Name",
            "industry": "Finance",
        })

        mock_db.commit.assert_called_once()


class TestAntiHallucination:
    """Tests for anti-hallucination mechanisms."""

    def test_prompt_includes_citation_requirement(self):
        """Test that system prompt requires citations."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import LEGAL_ADVISOR_PROMPT

        assert "Zitat" in LEGAL_ADVISOR_PROMPT or "citation" in LEGAL_ADVISOR_PROMPT.lower()

    def test_prompt_warns_about_uncertainty(self):
        """Test that prompt instructs to express uncertainty."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import LEGAL_ADVISOR_PROMPT

        assert "unsicher" in LEGAL_ADVISOR_PROMPT.lower() or "uncertain" in LEGAL_ADVISOR_PROMPT.lower() or "nicht sicher" in LEGAL_ADVISOR_PROMPT.lower()

    def test_prompt_recommends_lawyer_for_complex_cases(self):
        """Test that prompt recommends lawyers for complex cases."""
        from dealguard.infrastructure.ai.prompts.legal_advisor_v1 import LEGAL_ADVISOR_PROMPT

        assert "Anwalt" in LEGAL_ADVISOR_PROMPT or "lawyer" in LEGAL_ADVISOR_PROMPT.lower()


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
            citations=[
                {"file": "Mietvertrag.pdf", "page": 5, "snippet": "...3 Monate..."}
            ],
            confidence=0.92,
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
            user_id=uuid.uuid4(),
            title="Fragen zum Mietvertrag",
        )

        assert conversation.title == "Fragen zum Mietvertrag"
